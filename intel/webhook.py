# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from http.server import BaseHTTPRequestHandler, HTTPServer
from yamlreader import yaml_load, data_merge as merge, YamlReaderError
import ssl
import logging
import json
import base64
import sys

CMK_ER_NAME = ['cmk.intel.com/exclusive-cores',
               'cmk.intel.com/exclusive-non-isolcpus-cores']
CMK_MUTATE_ANNOTATION = 'cmk.intel.com/mutate'
ENV_NUM_CORES = 'CMK_NUM_CORES'
CIPHERS = "ECDHE-RSA-AES256-GCM-SHA384:\
ECDHE-ECDSA-AES256-GCM-SHA384"


class MutationError(Exception):
    pass


class WebhookServerConfig(object):
    def __init__(self):
        self.server = {}

    def load(self, filepath):
        try:
            config = yaml_load(filepath)
        except IOError:
            logging.error("Error opening config file {}."
                          .format(filepath))
            sys.exit(1)

        try:
            self.address = config["server"]["binding-address"]
            self.port = config["server"]["port"]
            self.cert = config["server"]["cert"]
            self.key = config["server"]["key"]
            self.mutations = config["server"]["mutations"]
        except KeyError as err:
            logging.error("Error loading configuration: {}".format(str(err)))
            sys.exit(1)


class WebhookServer(HTTPServer):
    def __init__(self, config, handler_class, cafile, insecure):
        self.config = config
        self.cafile = cafile
        self.insecure = insecure
        try:
            HTTPServer.__init__(self, (self.config.address, self.config.port),
                                handler_class)
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(self.config.cert, self.config.key)
            if self.insecure == "False":
                logging.info("Setting up webhook server to authenticate using"
                             " mutual TLS...")
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                ssl_context.load_verify_locations(cafile=self.cafile)

            ssl_context.options |= ssl.PROTOCOL_TLS
            ssl_context.options |= ssl.OP_NO_SSLv2
            ssl_context.options |= ssl.OP_NO_SSLv3
            ssl_context.options |= ssl.OP_NO_TLSv1
            ssl_context.options |= ssl.OP_NO_TLSv1_1
            ssl_context.set_ciphers(CIPHERS)
        except KeyError as err:
            logging.error("Error applying server config {}.".format(str(err)))
            sys.exit(1)
        self.socket = ssl_context.wrap_socket(self.socket, server_side=True)


class WebhookRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path.startswith("/mutate"):
            if self.headers['Content-Type'] != "application/json":
                logging.error("Incorrect content type")
                self.send_response(500)
            content_length = int(self.headers['Content-Length'])
            if content_length > 10000:
                logging.error("HTTP body too large")
                self.send_response(500)

            post_data = self.rfile.read(content_length).decode('utf-8')

            try:
                admission_review = json.loads(post_data)
                if admission_review["kind"] != "AdmissionReview":
                    logging.error("Request must be an admission review")
                    raise MutationError
                mutate(admission_review, self.server.config.mutations)
                response = json.dumps(admission_review)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))
            except ValueError as err:
                logging.error("Error while loading request {}".format(
                              err))
                self.send_response(500)
            except MutationError:
                logging.error("Error mutating resource")
                self.send_response(500)
        else:
            self.send_response(400)


def load_mutations(filepath):
    # load mutations from config file
    try:
        config = yaml_load(filepath)
        mutations = config.get('mutations', {})
    except YamlReaderError:
        logging.error("Error loading mutations from file {}."
                      .format(filepath))
        sys.exit(1)
    return mutations


def mutate(admission_review, mutations_file):
    try:
        if admission_review['request']['kind']['kind'] == 'Pod':
            pod = admission_review['request']['object']
        else:
            raise KeyError
    except KeyError:
        logging.error("Resource is not a pod")
        raise MutationError

    if is_mutation_required(pod):
        mutations = load_mutations(mutations_file)

        # apply pod mutations
        try:
            merge(pod, mutations.get("perPod", {}))
        except YamlReaderError as err:
            logging.error("Error when applying pod mutations: "
                          "{}".format(str(err)))
            raise MutationError

        # apply mutation to containers
        for i in range(len(pod['spec']['containers'])):
            # Need to reload mutations as they were geting changed
            mutations = load_mutations(mutations_file)
            container = pod['spec']['containers'][i]

            pod['spec']['containers'][i] = apply_mutation(container, mutations)

        # apply mutation to initContainers which may not exist
        try:
            for i in range(len(pod['spec']['initContainers'])):
                mutations = load_mutations(mutations_file)
                container = pod['spec']['initContainers'][i]

                pod['spec']['initContainers'][i] = \
                    apply_mutation(container, mutations)
        except KeyError:
            pass

        # generate patch based on modified pod spec
        patch = generate_patch(pod)

        resp = {
            'allowed': True,
            'uid': admission_review['request']['uid'],
            'patch': encode_patch(patch)
        }

    else:
        logging.info("Mutation is not required. Skipping...")
        resp = {
            'allowed': True,
            'uid': admission_review['request']['uid']
        }

    admission_review.pop('request')
    admission_review['response'] = resp


def apply_mutation(container, mutations):
    try:
        merge(container, mutations.get("perContainer", {}))
    except YamlReaderError as err:
        logging.error("Error when applying container mutations: "
                      "{}".format(str(err)))
        raise MutationError

    # NOTE: inject ENV_NUM_CORES variable only into containers with
    # ERs request/limit, priotizing requests over limits
    n_cores = None
    for er in CMK_ER_NAME:
        try:
            n_cores = container['resources']['requests'][er]
        except KeyError:
            logging.info("Container {} does not request CMK ER {}"
                         .format(container['name'], er))
            try:
                n_cores = container['resources']['limits'][er]
            except KeyError:
                logging.info("Container {} doesn't have CMK ER {} limit"
                             .format(container['name'], er))

        if n_cores is not None:
            # Break out if request found for any one ER
            # No support for multiple
            inject_env(container, ENV_NUM_CORES, n_cores)
            break

    return container


def generate_patch(pod):
    # NOTE: workaround for K8s API server not accepting '/' as a patch path
    patch = [
        {
            'op': 'replace',
            'path': '/metadata',
            'value': pod['metadata']
        },
        {
            'op': 'replace',
            'path': '/spec',
            'value': pod['spec']
        }
    ]
    return patch


def inject_env(container, name, value):
    if 'env' not in container:
        container['env'] = []
    elif name in [env["name"] for env in container["env"]]:
        logging.info("Environmental variable {} exists. Skipping..."
                     .format(name))
        return

    container['env'].append({
        'name': name,
        'value': value
    })


def encode_patch(patch):
    return base64.b64encode(json.dumps(patch).encode('utf-8')).decode('utf-8')


def is_container_mutation_required(container):
    for er in CMK_ER_NAME:
        try:
            if container['resources']['requests'][er] is not None:
                return True
        except KeyError:
            pass
        try:
            if container['resources']['limits'][er] is not None:
                return True
        except KeyError:
            pass
    return False


def is_mutation_required(pod):
    for container in pod['spec']['containers']:
        if is_container_mutation_required(container):
            return True
    try:
        if (pod['metadata']['annotations'][CMK_MUTATE_ANNOTATION]
                in ["true", "True", "1"]):
            return True
    except KeyError:
        logging.info("Annotation `{}` not present."
                     .format(CMK_MUTATE_ANNOTATION))
    return False


def webhook(config_file, cafile, insecure):
    config = WebhookServerConfig()
    config.load(config_file)

    webhook_server = WebhookServer(config, WebhookRequestHandler,
                                   cafile, insecure)

    try:
        webhook_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        webhook_server.server_close()
