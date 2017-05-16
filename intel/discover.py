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

from intel import config
import json
from kubernetes import config as k8sconfig, client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException
import logging
import os
import sys


# discover reads the CMK configuration file, patches kubernetes nodes with
# appropriate number of CMK Opaque Integer Resource (OIR) slots and applies
# the appropriate CMK node labels and taints.
def discover(conf_dir):
    # Patch the node with the appropriate CMK OIR.
    logging.debug("Patching the node with the appropriate CMK OIR.")
    add_node_oir(conf_dir)
    # Add appropriate CMK label to the node.
    logging.debug("Adding appropriate CMK label to the node.")
    add_node_label()
    # Add appropriate CMK taint to the node.
    logging.debug("Adding appropriate CMK taint to the node.")
    add_node_taint()


# add_node_oir patches the node with the appropriate CMK OIR.
def add_node_oir(conf_dir):
    c = config.Config(conf_dir)
    with c.lock():
        if "dataplane" not in c.pools():
            raise KeyError("Dataplane pool does not exist")
        if len(c.pool("dataplane").cpu_lists()) == 0:
            raise KeyError("No CPU list in dataplane pool")
        num_slots = len(c.pool("dataplane").cpu_lists())

    patch_path = ("/status/capacity/pod.alpha.kubernetes.io~1opaque-int-"
                  "resource-cmk")
    patch_body = [{
        "op": "add",
        "path": patch_path,
        "value": num_slots
    }]

    try:
        patch_k8s_node_status(patch_body)
    except K8sApiException as err:
        logging.error("Exception when patching node with OIR: {}"
                      .format(err))
        logging.error("Aborting discover ...")
        sys.exit(1)


def add_node_label():
    patch_path = "/metadata/labels/cmk.intel.com~1cmk-node"
    patch_body = [{
        "op": "add",
        "path": patch_path,
        "value": "true"
    }]

    try:
        patch_k8s_node(patch_body)
    except K8sApiException as err:
        logging.error("Exception when labeling the node: {}".format(err))
        logging.error("Aborting discover ...")
        sys.exit(1)


def add_node_taint():
    node_name = os.getenv("NODE_NAME")
    try:
        node_resp = get_k8s_node(node_name)
    except K8sApiException as err:
        logging.error("Exception when getting the node obj: {}".format(err))
        logging.error("Aborting discover ...")
        sys.exit(1)

    node_taints_list = []
    node_taint_key = "scheduler.alpha.kubernetes.io/taints"
    if node_taint_key in node_resp["metadata"]["annotations"]:
        node_taints = node_resp["metadata"]["annotations"][node_taint_key]
        # Do not try to parse the empty string as JSON.
        if node_taints:
            node_taints_list = json.loads(node_taints)

    # Filter existing "cmk" taint, if it exists.
    node_taints_list = [t for t in node_taints_list if t["key"] != "cmk"]

    node_taints_list.append({
        "key": "cmk",
        "value": "true",
        "effect": "NoSchedule"
    })

    patch_path = "/metadata/annotations/scheduler.alpha.kubernetes.io~1taints"

    # See: https://tools.ietf.org/html/rfc6902#section-4.1
    patch_body = [
        {
            "op": "add",
            "path": patch_path,
            "value": json.dumps(node_taints_list)
        }
    ]

    try:
        patch_k8s_node(patch_body)
    except K8sApiException as err:
        logging.error("Exception when tainting the node: {}".format(err))
        logging.error("Aborting discover ...")
        sys.exit(1)


# patch_k8s_node_status patches the kubernetes node with CMK OIR with
# value num_slots.
def patch_k8s_node_status(patch_body):
    k8sconfig.load_incluster_config()
    k8sapi = k8sclient.CoreV1Api()
    node_name = os.getenv("NODE_NAME")

    logging.info("Patching node status {}:\n{}".format(
        node_name,
        json.dumps(patch_body, indent=2, sort_keys=True)))

    # Patch the node with the specified number of opaque integer resources.
    k8sapi.patch_node_status(node_name, patch_body)


def patch_k8s_node(patch_body):
    k8sconfig.load_incluster_config()
    k8sapi = k8sclient.CoreV1Api()
    node_name = os.getenv("NODE_NAME")

    logging.info("Patching node {}:\n{}".format(
        node_name,
        json.dumps(patch_body, indent=2, sort_keys=True)))

    # Patch the node with the specified number of opaque integer resources.
    k8sapi.patch_node(node_name, patch_body)


# get_k8s_node() retuns the node spec associated with node_name.
def get_k8s_node(node_name):
    node_list_resp = get_k8s_node_list()
    for node in node_list_resp["items"]:
        if node["metadata"]["name"] == node_name:
            return node


# get_k8s_node_list() returns the node list in the current Kubernetes cluster.
def get_k8s_node_list():
    k8sconfig.load_incluster_config()
    k8s_api = k8sclient.CoreV1Api()
    return k8s_api.list_node().to_dict()
