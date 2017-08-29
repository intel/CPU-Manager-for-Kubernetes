# Copyright (c) 2017 Intel Corporation
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

import json
import logging
import time

from kubernetes.client.rest import ApiException as K8sApiException
from .util import ldh_convert_check

# Example usage:
#
# from kubernetes import config as k8sconfig, client as k8sclient
#
# k8sconfig.load_kube_config()
#
# v1beta = k8sclient.ExtensionsV1beta1Api()
#
# apple_type = CustomResourceDefinitionType(
#               v1beta, "intel.com", "apple", ["ap"])
#
# apple1 = apple_type.create("apple1")
# apple1.body["spec"]["count"] = 5
# apple1.save()
#
# apple2 = apple_type.create("apple2")
# apple2.body["spec"]["count"] = 10
# apple2.save()


class CustomResourceDefinitionType:
    def __init__(self, api, group, name, short_names,
                 version="v1", scope="Namespaced"):
        assert api is not None
        assert group is not None
        assert name is not None
        assert short_names is not None
        assert version is not None
        assert scope is not None

        self.api = api
        self.group = group
        self.kind_name = str(name).capitalize()
        self.singular_name = name
        self.plural_name = "{}s".format(name)
        self.short_names = short_names
        self.type_version = version
        self.type_scope = scope

        self.header_params = {
            'Content-Type': "application/json",
            'Accept': "application/json"
        }

        self.auth_settings = ['BearerToken']

        self.spec = {
            "group": self.group,
            "version": self.type_version,
            "scope": self.type_scope,
            "names": {
                "kind": self.kind_name,
                "singular": self.singular_name,
                "plural": self.plural_name,
                "shortNames": self.short_names
            }
        }

        self.body = {
            "metadata": {"name": ".".join([self.plural_name, self.group])},
            "spec": self.spec
        }

    def save(self):
        """Create custom resource definition spec"""
        try:
            resource_path = \
                '/apis/apiextensions.k8s.io/v1beta1/customresourcedefinitions'
            self.api.api_client.call_api(
                resource_path,
                'POST',
                self.header_params,
                body=self.body,
                auth_settings=self.auth_settings)

        except K8sApiException as e:
            if json.loads(e.body)["reason"] != "AlreadyExists":
                raise e

        # Wait until resource type is ready.
        while not self.exists():
            logging.info(
                "waiting 1 second until custom resource definition is ready")
            time.sleep(1)

    def exists(self, namespace="default"):
        """Check if custom resource definition exists"""
        resource_path = "/".join([
            "/apis",
            self.group,
            "v1",
            "namespaces", namespace,
            self.plural_name
        ])

        try:
            self.api.api_client.call_api(
                resource_path,
                'GET',
                self.header_params,
                auth_settings=self.auth_settings)

        except K8sApiException as e:
            if json.loads(e.body)["reason"] == "NotFound":
                return False
            raise e

        return True

    def create(self, name, namespace="default"):
        """Create custom resource definition"""
        self.save()
        return CustomResourceDefinition(self.api, self, namespace, name)

    def remove(self):
        """Remove custom resource definitions"""
        if self.exists():
            resource_path = "/apis/apiextensions.k8s.io/" \
                            + "v1beta1/customresourcedefinitions/" \
                            + self.plural_name + "." + self.group

            self.api.api_client.call_api(
                resource_path,
                'DELETE',
                self.header_params,
                auth_settings=self.auth_settings)


class CustomResourceDefinition:
    def __init__(self, api, resource_type, namespace, name):
        assert (api is not None)
        assert (resource_type is not None)
        assert (name is not None)
        assert (namespace is not None)

        self.api = api
        self.resource_type = resource_type
        self.name = ldh_convert_check(name)
        self.namespace = namespace

        self.body = {
            "apiVersion": "/".join([
                self.resource_type.group,
                self.resource_type.type_version
            ]),
            "kind": self.resource_type.kind_name,
            "metadata": {"name": self.name},
            "spec": {}
        }

        self.resource_path = "/".join([
            "/apis",
            self.resource_type.group,
            "v1",
            "namespaces",
            self.namespace,
            self.resource_type.plural_name
        ])

    def remove(self):
        """Remove custom object"""
        resource_path = "/".join([
            self.resource_path,
            self.name
        ])

        self.api.api_client.call_api(
            resource_path,
            'DELETE',
            self.resource_type.header_params,
            auth_settings=self.resource_type.auth_settings)

    def create(self):
        """Create custom object"""
        self.api.api_client.call_api(
            self.resource_path,
            'POST',
            self.resource_type.header_params,
            body=self.body,
            auth_settings=self.resource_type.auth_settings)

    def save(self):
        """Save custom object if not exists"""
        try:
            self.create()

        except K8sApiException as e:
            if json.loads(e.body)["reason"] != "AlreadyExists":
                raise e

            try:
                self.remove()
            except K8sApiException as e:
                if json.loads(e.body)["reason"] != "NotFound":
                    raise e

            self.create()

    def remove_all(self):
        """Remove all object custom resource"""
        resource_path = self.resource_path

        self.api.api_client.call_api(
            resource_path,
            'DELETE',
            self.resource_type.header_params,
            auth_settings=self.resource_type.auth_settings)
