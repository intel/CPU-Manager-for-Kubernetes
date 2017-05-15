# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from kubernetes.client.rest import ApiException as K8sApiException
import datetime
import logging
import re
import time

# Example usage:
#
# from kubernetes import config as k8sconfig, client as k8sclient
#
# k8sconfig.load_kube_config()
#
# v1beta = k8sclient.ExtensionsV1beta1Api()
#
# apple_type = ThirdPartyResourceType(v1beta, "intel.com", "apple")
#
# apple1 = apple_type.create("apple1")
# apple1.body["count"] = 5
# apple1.save()
#
# apple2 = apple_type.create("apple2")
# apple2.body["count"] = 10
# apple2.save()


class ThirdPartyResourceType():
    def __init__(self, api, url, kind_name, version="v1"):
        assert(api is not None)
        assert(url is not None)
        assert(kind_name is not None)
        assert(version is not None)

        self.api = api
        self.type_url = url
        self.type_name = kind_name.lower()
        self.kind_name = kind_name
        self.type_version = version

    def save(self):
        body = {
            "metadata": {"name": ".".join([self.type_name, self.type_url])},
            "versions": [{"name": self.type_version}]
        }

        try:
            self.api.create_third_party_resource(body)
        except K8sApiException as e:
            if json.loads(e.body)["reason"] != "AlreadyExists":
                raise e

        # Wait until resource type is ready.
        while not self.exists():
            logging.info(
                "waiting 1 second until third party resource is ready")
            time.sleep(1)

    def exists(self, namespace="default"):
        header_params = {
            'Content-Type': "application/json",
            'Accept': "application/json"
        }

        auth_settings = ['BearerToken']

        resource_path = "/".join([
            "/apis",
            self.type_url,
            self.type_version,
            "namespaces", namespace,
            self.type_name + "s"
        ])

        try:
            self.api.api_client.call_api(
                resource_path,
                'GET',
                header_params,
                auth_settings=auth_settings)

        except K8sApiException as e:
            if json.loads(e.body)["reason"] == "NotFound":
                return False
            raise e

        return True

    def create(self, name, namespace="default"):
        self.save()
        return ThirdPartyResource(self.api, self, namespace, name)


class ThirdPartyResource:
    def __init__(self, api, resource_type, namespace, name):
        assert(api is not None)
        assert(resource_type is not None)
        assert(name is not None)
        assert(namespace is not None)

        self.api = api
        self.resource_type = resource_type
        self.name = ldh_convert_check(name)
        self.namespace = namespace

        self.body = {
            "apiVersion": "/".join([
                self.resource_type.type_url,
                self.resource_type.type_version
            ]),
            "kind": self.resource_type.kind_name,
            "metadata": {"name": self.name}
        }

        self.header_params = {
            'Content-Type': "application/json",
            'Accept': "application/json"
        }

        self.auth_settings = ['BearerToken']

    def remove(self):
        resource_path = "/".join([
            "/apis",
            self.resource_type.type_url,
            self.resource_type.type_version,
            "namespaces", self.namespace,
            self.resource_type.type_name + "s",
            self.name
        ])

        self.api.api_client.call_api(
            resource_path,
            'DELETE',
            self.header_params,
            auth_settings=self.auth_settings)

    def create(self):
        resource_path = "/".join([
            "/apis",
            self.resource_type.type_url,
            self.resource_type.type_version,
            "namespaces", self.namespace,
            self.resource_type.type_name + "s"
        ])

        self.body["last_updated"] = datetime.datetime.now().isoformat()

        self.api.api_client.call_api(
            resource_path,
            'POST',
            self.header_params,
            body=self.body,
            auth_settings=self.auth_settings)

    def save(self):
        try:
            self.create()

        except K8sApiException as e:
            if json.loads(e.body)["reason"] != "AlreadyExists":
                raise e

            self.remove()
            self.create()


def ldh_convert_check(name):
    name_con = re.sub(r'[^-a-z0-9]', '-', name.lower())
    logging.info("Converted \"{}\" to \"{}\" for"
                 " TPR name".format(name, name_con))
    if not re.fullmatch('[a-z0-9]([-a-z0-9]*[a-z0-9])?', name_con):
        logging.error("Cant create valid TPR name using "
                      "\"{}\" - must match regex "
                      "[a-z0-9]([-a-z0-9]*[a-z0-9])?".format(name_con))
        exit(1)
    return name_con
