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
from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import V1Namespace, V1DeleteOptions


def get_pod_template():
    pod_template = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "PODNAME",
            "annotations": {
            }
        },
        "spec": {
            "nodeName": "NODENAME",
            "containers": [
            ],
            "restartPolicy": "Never",
            "volumes": [
                {
                    "hostPath": {
                        "path": "/proc"
                    },
                    "name": "host-proc"
                },
                {
                    "hostPath": {
                        "path": "/etc/kcm"
                    },
                    "name": "kcm-conf-dir"
                },
                {
                    "hostPath": {
                        "path": "/opt/bin"
                    },
                    "name": "kcm-install-dir"
                }
            ]
        }
    }
    return pod_template


def client_from_config(config):
    if config is None:
        k8sconfig.load_incluster_config()
        return k8sclient.CoreV1Api()
    else:
        client = k8sclient.ApiClient(config=config)
        return k8sclient.CoreV1Api(api_client=client)


def get_container_template():
    container_template = {
        "args": [
            "ARGS"
        ],
        "command": ["/bin/bash", "-c"],
        "env": [
            {
                "name": "KCM_PROC_FS",
                "value": "/host/proc"
            },
            {
                "name": "NODE_NAME",
                "valueFrom": {
                    "fieldRef": {
                        "fieldPath": "spec.nodeName"
                    }
                }
            }
        ],
        "image": "IMAGENAME",
        "name": "NAME",
        "volumeMounts": [
            {
                "mountPath": "/host/proc",
                "name": "host-proc",
                "readOnly": True
            },
            {
                "mountPath": "/etc/kcm",
                "name": "kcm-conf-dir"
            },
            {
                "mountPath": "/opt/bin",
                "name": "kcm-install-dir"
            }
        ],
        "imagePullPolicy": "Never"
    }
    return container_template


# get_node_list() returns the node list in the current Kubernetes cluster.
def get_node_list(config, label_selector=None):
    k8s_api = client_from_config(config)
    if label_selector:
        nodes = k8s_api.list_node(label_selector=label_selector).to_dict()
    else:
        nodes = k8s_api.list_node().to_dict()
    return nodes["items"]


# get_pod_list() returns the pod list in the current Kubernetes cluster.
def get_pod_list(config):
    k8s_api = client_from_config(config)
    return k8s_api.list_pod_for_all_namespaces().to_dict()


# create_pod() sends a request to the Kubernetes API server to create a
# pod based on podspec.
def create_pod(config, podspec, ns_name="default"):
    k8s_api = client_from_config(config)
    return k8s_api.create_namespaced_pod(ns_name, podspec)


# Create list of schedulable nodes.
def get_compute_nodes(config, label_selector=None):
    compute_nodes = []
    for node in get_node_list(config, label_selector):
        if "unschedulable" in node["spec"] and \
                node["spec"]["unschedulable"]:
            continue
        compute_nodes.append(node)
    return compute_nodes


# Set label to selected node.
def set_node_label(config, node, label, label_value):
    patch_body = [{
        "op": "add",
        "path": "/metadata/labels/%s" % label,
        "value": label_value,
    }]
    k8s_api = client_from_config(config)
    k8s_api.patch_node(node, patch_body)


# Unset label from node.
def unset_node_label(config, node, label):
    patch_body = [{
        "op": "remove",
        "path": "/metadata/labels/%s" % label,
    }]
    k8s_api = client_from_config(config)
    k8s_api.patch_node(node, patch_body)


# Create namespace with generated namespace name.
def create_namespace(config, ns_name):
    metadata = {'name': ns_name}
    namespace = V1Namespace(metadata=metadata)
    k8s_api = client_from_config(config)
    k8s_api.create_namespace(namespace)


# Get available namespaces.
def get_namespaces(config):
    k8s_api = client_from_config(config)
    return k8s_api.list_namespace().to_dict()


# Delete namespace by name.
def delete_namespace(config, ns_name, delete_options=V1DeleteOptions()):
    k8s_api = client_from_config(config)
    k8s_api.delete_namespace(ns_name, delete_options)


# Delete pod from namespace.
def delete_pod(config, name, ns_name="default", body=V1DeleteOptions()):
    k8s_api = client_from_config(config)
    k8s_api.delete_namespaced_pod(name, ns_name, body)
