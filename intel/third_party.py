import json
from kubernetes.client.rest import ApiException as K8sApiException
import datetime

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
    def __init__(self, api, url, type_name, version="v1"):
        self.api = api
        self.type_url = url
        self.type_name = type_name
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

    def create(self, name, namespace="default"):
        self.save()
        return ThirdPartyResource(self.api, self, namespace, name)


class ThirdPartyResource:
    def __init__(self, api, resource_type, namespace, name):
        self.api = api
        self.resource_type = resource_type
        self.name = name
        self.namespace = namespace
        self.body = {
            "apiVersion": "/".join([
                self.resource_type.type_url,
                self.resource_type.type_version
            ]),
            "kind": self.resource_type.type_name.title().replace("-", ""),
            "metadata": {"name": name}
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

        print("resource_path: '%s'" % resource_path)
        print("body: '%s'" % body)

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
