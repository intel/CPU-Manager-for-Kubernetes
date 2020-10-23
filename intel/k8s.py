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

import logging

from intel import util
from kubernetes import client as k8sclient, config as k8sconfig
from kubernetes.client import V1Namespace, V1DeleteOptions

VERSION_NAME = "v1.9.0"


# Only set up the Volume Mounts necessary for the container
CONTAINER_VOLUME_MOUNTS = {
    "init": {
        "volumeMounts": [
            {
                "mountPath": "/host/proc",
                "name": "host-proc",
                "readOnly": True
            }
        ],
        "securityContext": {
            "readOnlyRootFilesystem": True,
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 3000,
            "fsGroup": 2000
        }
    },
    "install": {
        "volumeMounts": [
            {
                "mountPath": "/opt/bin",
                "name": "cmk-install-dir",
            }
        ],
        "securityContext": {
            "privileged": True
        }
    },
    "discover": {
        "volumeMounts": [
        ],
        "securityContext": {
            "readOnlyRootFilesystem": True,
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 3000,
            "fsGroup": 2000
        }
    },
    "reconcile": {
        "volumeMounts": [
            {
                "mountPath": "/host/proc",
                "name": "host-proc",
                "readOnly": True
            },
            {
                "mountPath": "/opt/bin",
                "name": "cmk-install-dir",
                "readOnly": True
            }
        ],
        "securityContext": {
            "readOnlyRootFilesystem": True,
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 3000,
            "fsGroup": 2000
        }
    },
    "nodereport": {
        "volumeMounts": [
            {
                "mountPath": "/host/proc",
                "name": "host-proc",
                "readOnly": True
            },
            {
                "mountPath": "/opt/bin",
                "name": "cmk-install-dir",
                "readOnly": True
            }
        ],
        "securityContext": {
            "readOnlyRootFilesystem": True,
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 3000,
            "fsGroup": 2000
        }
    },
    "webhook": {
        "volumeMounts": [
            {
                "mountPath": "/host/proc",
                "name": "host-proc",
                "readOnly": True
            },
            {
                "mountPath": "/opt/bin",
                "name": "cmk-install-dir",
                "readOnly": True
            }
        ],
        "securityContext": {
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 3000,
            "fsGroup": 2000
        }
    },
    "reconfigure": {
        "volumeMounts": [
            {
                "mountPath": "/host/proc",
                "name": "host-proc",
                "readOnly": True
            }
        ],
        "securityContext": {
            "readOnlyRootFilesystem": True,
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "runAsGroup": 3000,
            "fsGroup": 2000
        }
    }
}


def get_pod_template(saname="cmk-serviceaccount"):
    pod_template = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "PODNAME",
            "annotations": {
            }
        },
        "spec": {
            "serviceAccount": saname,
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
                        "path": "/opt/bin"
                    },
                    "name": "cmk-install-dir"
                }
            ]
        }
    }
    return pod_template


def ds_from(pod, version):
    ds_template = {}
    if version >= util.parse_version(VERSION_NAME):
        ds_template = {
            "apiVersion": "apps/v1",
            "kind": "DaemonSet",
            "metadata": {
                "name": pod["metadata"]["name"].replace("pod", "ds")
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app": pod["metadata"]["name"].replace("pod", "ds")
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app":
                                pod["metadata"]["name"].replace("pod", "ds")
                        }
                    },
                    "spec": pod["spec"]
                }
            }
        }
    # for k8s versions older than 1.9.0 use extensions/v1beta1 API
    else:
        ds_template = {
            "apiVersion": "extensions/v1beta1",
            "kind": "DaemonSet",
            "metadata": {
                "name": pod["metadata"]["name"].replace("pod", "ds")
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {
                            "app":
                                pod["metadata"]["name"].replace("pod", "ds")
                        }
                    },
                    "spec": pod["spec"]
                }
            }
        }
    return ds_template


def deployment_from(pod):
    deployment_template = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "labels": pod["metadata"]["labels"],
            "name": pod["metadata"]["name"].replace("pod", "deployment")
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": pod["metadata"]["labels"]
            },
            "template": {
                "metadata": {
                    "labels": pod["metadata"]["labels"]
                },
                "spec": pod["spec"]
            }
        }
    }
    return deployment_template


def client_from_config(config):
    if config is None:
        k8sconfig.load_incluster_config()
        return k8sclient.CoreV1Api()
    else:
        client = k8sclient.ApiClient(configuration=config)
        return k8sclient.CoreV1Api(api_client=client)


def apps_api_client_from_config(config):
    if config is None:
        k8sconfig.load_incluster_config()
        return k8sclient.AppsV1Api()
    else:
        client = k8sclient.ApiClient(configuration=config)
        return k8sclient.AppsV1Api(api_client=client)


def extensions_client_from_config(config):
    if config is None:
        k8sconfig.load_incluster_config()
        return k8sclient.ExtensionsV1beta1Api()
    else:
        client = k8sclient.ApiClient(configuration=config)
        return k8sclient.ExtensionsV1beta1Api(api_client=client)


def version_api_client_from_config(config):
    if config is None:
        k8sconfig.load_incluster_config()
        return k8sclient.VersionApi()
    else:
        client = k8sclient.ApiClient(configuration=config)
        return k8sclient.VersionApi(api_client=client)


def admissionregistartion_api_client_from_config(config):
    if config is None:
        k8sconfig.load_incluster_config()
        return k8sclient.AdmissionregistrationV1beta1Api()
    else:
        client = k8sclient.ApiClient(configuration=config)
        return k8sclient.AdmissionregistrationV1beta1Api(api_client=client)


def get_container_template(cmd):
    container_template = {
        "args": [
            "ARGS"
        ],
        "command": ["/bin/bash", "-c"],
        "env": [
            {
                "name": "CMK_PROC_FS",
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
        "securityContext": CONTAINER_VOLUME_MOUNTS[cmd]["securityContext"],
        "volumeMounts": CONTAINER_VOLUME_MOUNTS[cmd]["volumeMounts"],
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


# get_node_from_pod returns the node that a given pod is running on
def get_node_from_pod(config, pod_name):
    pods = get_pod_list(config)
    for p in pods["items"]:
        if p["metadata"]["name"] == pod_name:
            return p["spec"]["node_name"]


# get_pod_list() returns the pod list in the current Kubernetes cluster.
def get_pod_list(config):
    k8s_api = client_from_config(config)
    return k8s_api.list_pod_for_all_namespaces().to_dict()


# create_pod() sends a request to the Kubernetes API server to create a
# pod based on podspec.
def create_pod(config, podspec, ns_name):
    k8s_api = client_from_config(config)
    return k8s_api.create_namespaced_pod(ns_name, podspec)


# create_legacy_ds() sends a request to the Kubernetes API server to create a
# ds based on deamonset spec.
def create_ds(config, spec, ns_name, version):
    if version >= util.parse_version(VERSION_NAME):
        k8s_api = apps_api_client_from_config(config)
        return k8s_api.create_namespaced_daemon_set(ns_name, spec)
    else:
        k8s_api = extensions_client_from_config(config)
        return k8s_api.create_namespaced_daemon_set(ns_name, spec)


def create_service(config, spec, ns_name):
    k8s_api = client_from_config(config)
    return k8s_api.create_namespaced_service(ns_name, spec)


def create_config_map(config, spec, ns_name):
    k8s_api = client_from_config(config)
    return k8s_api.create_namespaced_config_map(ns_name, spec)


def patch_config_map(config, cm_name, spec, ns_name):
    k8s_api = client_from_config(config)
    return k8s_api.patch_namespaced_config_map(cm_name, ns_name, spec)


def create_secret(config, spec, ns_name):
    k8s_api = client_from_config(config)
    return k8s_api.create_namespaced_secret(ns_name, spec)


def create_mutating_webhook_configuration(config, spec):
    k8s_api = admissionregistartion_api_client_from_config(config)
    return k8s_api.create_mutating_webhook_configuration(spec)


def create_deployment(config, spec, ns_name):
    k8s_api = apps_api_client_from_config(config)
    return k8s_api.create_namespaced_deployment(ns_name, spec)


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


# Get k8s version
def get_kube_version(config):
    k8s_api = version_api_client_from_config(config)
    version_info = k8s_api.get_code()
    return version_info.git_version


# Get named configmap
def get_config_map(config, name, ns_name):
    k8s_api = client_from_config(config)
    configmaps = k8s_api.list_namespaced_config_map(ns_name)
    for cm in configmaps.items:
        if cm.metadata.name == name:
            return cm


# Delete namespace by name.
def delete_namespace(config, ns_name, delete_options=V1DeleteOptions()):
    k8s_api = client_from_config(config)
    k8s_api.delete_namespace(ns_name)


# Delete pod from namespace.
def delete_pod(config, name, ns_name="default", body=V1DeleteOptions()):
    k8s_api = client_from_config(config)
    k8s_api.delete_namespaced_pod(name, ns_name)


# Delete ds from namespace.
# Due to problem with orphan_dependents flag and changes
# in cascade deletion in k8s, first delete the ds, then the pod
# https://github.com/kubernetes-incubator/client-python/issues/162
# https://github.com/kubernetes/kubernetes/issues/44046
def delete_ds(config, version, ds_name, ns_name="default",
              body=V1DeleteOptions()):
    k8s_api_core = client_from_config(config)

    if version >= util.parse_version(VERSION_NAME):
        k8s_api_apps = apps_api_client_from_config(config)
        k8s_api_apps.delete_namespaced_daemon_set(ds_name,
                                                  ns_name,
                                                  grace_period_seconds=0,
                                                  orphan_dependents=False)
    else:
        k8s_api_ext = extensions_client_from_config(config)
        k8s_api_ext.delete_namespaced_daemon_set(ds_name,
                                                 ns_name,
                                                 grace_period_seconds=0,
                                                 orphan_dependents=False)

    # Pod in ds has fixed label so we use label selector
    data = k8s_api_core.list_namespaced_pod(
        ns_name, label_selector="app={}".format(ds_name)).to_dict()
    # There should be only one pod
    for pod in data["items"]:
        logging.debug("Removing pod \"{}\"".format(pod["metadata"]["name"]))
        delete_pod(None, pod["metadata"]["name"], ns_name)


def delete_service(config, name, ns_name="default", body=V1DeleteOptions()):
    k8s_api = client_from_config(config)
    return k8s_api.delete_namespaced_service(name, ns_name)


def delete_config_map(config, name, ns_name="default", body=V1DeleteOptions()):
    k8s_api = client_from_config(config)
    return k8s_api.delete_namespaced_config_map(name, ns_name)


def delete_secret(config, name, ns_name="default", body=V1DeleteOptions()):
    k8s_api = client_from_config(config)
    return k8s_api.delete_namespaced_secret(name, ns_name)


def delete_mutating_webhook_configuration(config, name,
                                          body=V1DeleteOptions()):
    k8s_api = admissionregistartion_api_client_from_config(config)
    return k8s_api.delete_mutating_webhook_configuration(name)


def delete_deployment(config, name, ns_name="default", body=V1DeleteOptions()):
    k8s_api = apps_api_client_from_config(config)
    return k8s_api.delete_namespaced_deployment(name, ns_name)
