# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the "Software"), without modification,
# provided the following conditions are met:
#
# * Neither the name of Intel nor the names of its suppliers may be used to
#   endorse or promote products derived from this Software without specific
#   prior written permission.
# * No reverse engineering, decompilation, or disassembly of this Software
#   is permitted.
#
# Limited patent license.  Intel grants you a world-wide, royalty-free,
# non-exclusive license under patents it now or hereafter owns or controls to
# make, have made, use, import, offer to sell and sell ("Utilize") this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  "Third Party Programs" are the files
# listed in the "third-party-programs.txt" text file that is included with the
# Software and may include Intel programs under separate license terms. Third
# Party Programs, even if included with the distribution of the Materials, are
# governed by separate license terms and those license terms solely govern your
# use of those programs.
#
# DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
# DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS
# OR APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR
# DEATH.
#
# LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO
# INDEMNIFIY AND HOLD INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING
# FROM YOUR USE OR UNAUTHORIZED USE OF THE SOFTWARE.
#
# No support.  Intel may make changes to the Software, at any time without
# notice, and is not obligated to support, update or provide training for the
# Software.
#
# Termination. Intel may terminate your right to use the Software in the event
# of your breach of this Agreement and you fail to cure the breach within a
# reasonable period of time.
#
# Feedback.  Should you provide Intel with comments, modifications,
# corrections, enhancements or other input ("Feedback") related to the Software
# Intel will be free to use, disclose, reproduce, license or otherwise
# distribute or exploit the Feedback in its sole discretion without any
# obligations or restrictions of any kind, including without limitation,
# intellectual property rights or licensing obligations.
#
# Compliance with laws.  You agree to comply with all relevant laws and
# regulations governing your use, transfer, import or export (or prohibition
# thereof) of the Software.
#
# Governing law.  All disputes will be governed by the laws of the United
# States of America and the State of Delaware without reference to conflict of
# law principles and subject to the exclusive jurisdiction of the state or
# federal courts sitting in the State of Delaware, and each party agrees that
# it submits to the personal jurisdiction and venue of those courts and waives
# any objections. The United Nations Convention on Contracts for the
# International Sale of Goods (1980) is specifically excluded and will not
# apply to the Software.
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
