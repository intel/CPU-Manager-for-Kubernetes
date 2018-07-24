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
import ssl
import logging
import json
import base64
import yaml

CMK_ER_NAME = 'cmk.intel.com/dp-cores'
ENV_PROC_FS = 'CMK_PROC_FS'
ENV_NUM_CORES = 'CMK_NUM_CORES'


class WebhookServerConfig(object):
    def __init__(self, config_file_path):
        default_config = {
            'server': {
                'binding-address': '127.0.0.1',
                'port': 443,
                'cert': '/etc/certs/cert.pem',
                'key': '/etc/certs/key.pem'
            }
        }

        try:
            config_file = open(config_file_path, 'r')
            config = yaml.load(config_file)
        except IOError:
            logging.warning('Error opening config file. Loading defaults')
            config = default_config

        self.hostname = config.get('server', {}).get('binding-address')
        self.port = config.get('server', {}).get('port')
        self.cert = config.get('server', {}).get('cert')
        self.key = config.get('server', {}).get('key')


class WebhookServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        HTTPServer.__init__(self, *args, **kwargs)
        self.host_proc_fs = None
        self.config_dir = None
        self.install_dir = None
        self.sa_name = None


class WebhookRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        if self.path.startswith("/mutate"):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')

            admission_review = json.loads(post_data)

            admission_review = mutate(admission_review,
                                      self.server.host_proc_fs,
                                      self.server.config_dir,
                                      self.server.install_dir,
                                      self.server.sa_name)

            response = json.dumps(admission_review)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(400)
        return


def mutate(admission_review, host_proc_fs, config_dir, install_dir, sa_name):
    try:
        if admission_review['request']['kind']['kind'] == 'Pod':
            pod = admission_review['request']['object']
        else:
            raise KeyError
    except KeyError:
        logging.error('not a pod')
        return

    if is_mutation_required(pod):
        # list of patches to apply on the pod
        patches = []

        # annotate pod as modified
        inject_annotation(patches, pod, 'cmk.intel.com/resources-injected',
                          'true')

        # inject volumes
        inject_volume(patches, pod, 'cmk-host-proc', host_proc_fs)
        inject_volume(patches, pod, 'cmk-config-dir', config_dir)
        inject_volume(patches, pod, 'cmk-install-dir', install_dir)

        # inject toleration
        inject_toleration(patches, pod, 'operator', 'Exists')

        # inject service account
        inject_sa_name(patches, pod, sa_name)

        for i in range(len(pod['spec']['containers'])):
            container = pod['spec']['containers'][i]

            if not is_container_mutation_required(container):
                continue

            # inject ENNV_PROC_FS variable
            inject_env(container, ENV_PROC_FS, '/host/proc')

            # inject ENV_NUM_CORES variable
            # NOTE: priotize requests over limits
            if 'requests' in container['resources']:
                num_cores = container['resources']['requests'][CMK_ER_NAME]
            else:
                num_cores = container['resources']['limits'][CMK_ER_NAME]
            inject_env(container, ENV_NUM_CORES, num_cores)

            # inject volume mounts
            inject_volume_mount(container, 'cmk-host-proc',
                                '/host/proc', True)
            inject_volume_mount(container, 'cmk-config-dir',
                                '/etc/cmk', False)
            inject_volume_mount(container, 'cmk-install-dir',
                                '/opt/bin', False)

            # replace original container with patched one
            pod['spec']['containers'][i] = container

        # generate patch based on patched containers spec
        patch_containers(patches, pod)

        resp = {
            'allowed': True,
            'uid': admission_review['request']['uid'],
            'patch': encode_patch(patches)
        }

    else:
        logging.info("Mutation is not required. Skipping...")
        resp = {
            'allowed': True,
            'uid': admission_review['request']['uid']
        }

    admission_review.pop('request')
    admission_review['response'] = resp
    return admission_review


def inject_annotation(patches, pod, key, value):
    if 'annotations' not in pod['metadata']:
        pod['annotations'] = []
    elif key in pod['annotations']:
        logging.debug('Annotation %s exists. Skipping', key)
        return patches

    patch = {
        'op': 'add',
        'path': '/metadata/annotations',
        'value': {key: value}
    }
    patches.append(patch)
    return patches


def inject_sa_name(patches, pod, name):
    if 'serviceAccountName' in pod['spec']:
        logging.debug('serviceAccountName %s exists. Skipping', name)
        return patches

    patch = {
        'op': 'add',
        'path': '/spec/serviceAccountName',
        'value': name
    }
    patches.append(patch)
    return patches


def patch_containers(patches, pod):
    patch = {
        'op': 'replace',
        'path': '/spec/containers',
        'value': pod['spec']['containers']
    }
    patches.append(patch)
    return patches


def inject_volume(patches, pod, name, host_path):
    path = '/spec/volumes'
    if 'volumes' not in pod:
        path += '/-'
    elif name in pod['spec']['volumes']:
        logging.debug('Volume %s exists. Skipping...', name)
        return patches

    volume = {
        'name': name,
        'hostPath': {
            'path': host_path
        }
    }
    patch = {
        'op': 'add',
        'path': path,
        'value': volume
    }
    patches.append(patch)
    return patches


def inject_toleration(patches, pod, key, value):
    path = '/spec/tolerations'
    if 'tolerations' not in pod:
        path += '/-'
    elif key in pod['spec']['tolerations']:
        logging.debug('Toleration %s exists. Skipping...', key)
        return patches

    patch = {
        'op': 'add',
        'path': path,
        'value': {key: value}
    }
    patches.append(patch)
    return patches


def inject_env(container, name, value):
    if 'env' not in container:
        container['env'] = []
    elif name in container['env']:
        logging.debug('Environmental variable %s exists. Skipping...', name)
        return container

    container['env'].append({
        'name': name,
        'value': value
    })
    return container


def inject_volume_mount(container, name, path, read_only):
    if 'volumeMounts' not in container:
        container['volumeMounts'] = []
    elif name in container['volumeMounts']:
        logging.debug('Volume mount %s exists. Skipping...', name)
        return container

    container['volumeMounts'].append({
        'name': name,
        'mountPath': path,
        'readOnly': read_only
    })
    return container


def encode_patch(patch):
    return base64.b64encode(json.dumps(patch).encode('utf-8')).decode('utf-8')


def is_container_mutation_required(container):
    try:
        if container['resources']['requests'][CMK_ER_NAME] is not None:
            return True
    except KeyError:
        pass
    try:
        if container['resources']['limits'][CMK_ER_NAME] is not None:
            return True
    except KeyError:
        pass
    return False


def is_mutation_required(pod):
    for container in pod['spec']['containers']:
        if is_container_mutation_required(container):
            return True
    return False


def webhook(config_file, host_proc_fs, config_dir, install_dir, sa_name):
    config = WebhookServerConfig(config_file)

    webhook_server = WebhookServer((config.hostname, config.port),
                                   WebhookRequestHandler)
    webhook_server.host_proc_fs = host_proc_fs
    webhook_server.config_dir = config_dir
    webhook_server.install_dir = install_dir
    webhook_server.sa_name = sa_name

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(config.cert, config.key)
    webhook_server.socket = ssl_context.wrap_socket(webhook_server.socket,
                                                    server_side=True)

    try:
        webhook_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        webhook_server.server_close()
