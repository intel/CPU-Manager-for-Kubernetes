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

from intel import config, util
import json
import logging
import os
import sys


from kubernetes import config as k8sconfig, client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException
from . import k8s


# discover reads the CMK configuration file, patches kubernetes nodes with
# appropriate number of CMK Opaque Integer Resource (OIR) slots and applies
# the appropriate CMK node labels and taints.
def discover(conf_dir):

    version = util.parse_version(k8s.get_kube_version(None))
    if version == util.parse_version("v1.8.0"):
        logging.fatal("K8s 1.8.0 is not supported. Update K8s to "
                      "version >=1.8.1 or rollback to previous versions")
        sys.exit(1)

    if version >= util.parse_version("v1.8.1"):
        # Patch the node with the appropriate CMK ER.
        logging.debug("Patching the node with the appropriate CMK ER.")
        add_node_er(conf_dir)
    else:
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
    num_excl_non_isolcpus = None
    with c.lock():
        if "exclusive" not in c.pools():
            raise KeyError("Exclusive pool does not exist")
        num_slots = len(c.pool("exclusive").cpu_lists())
        if "exclusive-non-isolcpus" in c.pools():
            num_excl_non_isolcpus = len(c.pool("exclusive-non-isolcpus")
                                        .cpu_lists())

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

    if num_excl_non_isolcpus:
        patch_path = ("/status/capacity/pod.alpha.kubernetes.io~1opaque-int-"
                      "resource-cmk-excl-non-isolcpus")
        patch_body = [{
            "op": "add",
            "path": patch_path,
            "value": num_excl_non_isolcpus
        }]

        try:
            patch_k8s_node_status(patch_body)
        except K8sApiException as err:
            logging.error("Exception when patching node with OIR: {}"
                          .format(err))
            logging.error("Aborting discover ...")
            sys.exit(1)


# add_node_er patches the node with the appropriate CMK extended resources.
def add_node_er(conf_dir):
    c = config.Config(conf_dir)
    num_excl_non_isolcpus = None
    with c.lock():
        if "exclusive" not in c.pools():
            raise KeyError("Exclusive pool does not exist")
        num_slots = len(c.pool("exclusive").cpu_lists())
        if "exclusive-non-isolcpus" in c.pools():
            num_excl_non_isolcpus = len(c.pool("exclusive-non-isolcpus")
                                        .cpu_lists())

    patch_path = ("/status/capacity/cmk.intel.com~1exclusive-cores")
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

    if num_excl_non_isolcpus:
        patch_path = ("/status/capacity/cmk.intel.com~1"
                      "exclusive-non-isolcpus-cores")
        patch_body = [{
            "op": "add",
            "path": patch_path,
            "value": num_excl_non_isolcpus
        }]

        try:
            patch_k8s_node_status(patch_body)
        except K8sApiException as err:
            logging.error("Exception when patching node with "
                          "exclusive-non-isolcpus ER: {}"
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


def get_node_label(key):
    node_name = os.getenv("NODE_NAME")

    try:
        node = get_k8s_node(node_name)
    except K8sApiException as err:
        logging.error("Exception when getting the node obj: {}".format(err))
        logging.error("Aborting ...")
        sys.exit(1)

    return node["metadata"]["labels"][key]


def add_node_taint():
    node_name = os.getenv("NODE_NAME")
    try:
        node_resp = get_k8s_node(node_name)
    except K8sApiException as err:
        logging.error("Exception when getting the node obj: {}".format(err))
        logging.error("Aborting discover ...")
        sys.exit(1)

    version = util.parse_version(k8s.get_kube_version(None))
    node_taints_list = []
    node_taints = []

    if version >= util.parse_version("v1.7.0"):
        node_taints = node_resp["spec"]["taints"]
        if node_taints:
            node_taints_list = node_taints
        patch_path = "/spec/taints"
    else:
        node_taint_key = "scheduler.alpha.kubernetes.io/taints"
        if node_taint_key in node_resp["metadata"]["annotations"]:
            node_taints = node_resp["metadata"]["annotations"][node_taint_key]
        patch_path = "/metadata/annotations/scheduler.alpha.kubernetes.io~1taints"  # noqa: E501
        if node_taints:
            node_taints_list = json.loads(node_taints)

    # Filter existing "cmk" taint, if it exists.
    node_taints_list = [t for t in node_taints_list if t["key"] != "cmk"]

    node_taints_list.append({
        "key": "cmk",
        "value": "true",
        "effect": "NoSchedule"
    })

    if version >= util.parse_version("v1.7.0"):
        value = node_taints_list
    else:
        value = json.dumps(node_taints_list)

    # See: https://tools.ietf.org/html/rfc6902#section-4.1
    patch_body = [
        {
            "op": "add",
            "path": patch_path,
            "value": value
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
