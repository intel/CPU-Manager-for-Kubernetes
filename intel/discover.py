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

from intel import config
import json
from kubernetes import config as k8sconfig, client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException
import logging
import os
import sys


# discover reads the KCM configuration file, patches kubernetes nodes with
# appropriate number of KCM Opaque Integer Resource (OIR) slots and applies
# the appropriate KCM node labels and taints.
def discover(conf_dir):
    # Patch the node with the appropriate KCM OIR.
    logging.debug("Patching the node with the appropriate KCM OIR.")
    add_node_oir(conf_dir)
    # Add appropriate KCM label to the node.
    logging.debug("Adding appropriate KCM label to the node.")
    add_node_label()
    # Add appropriate KCM taint to the node.
    logging.debug("Adding appropriate KCM taint to the node.")
    add_node_taint()


# add_node_oir patches the node with the appropriate KCM OIR.
def add_node_oir(conf_dir):
    c = config.Config(conf_dir)
    with c.lock():
        if "dataplane" not in c.pools():
            raise KeyError("Dataplane pool does not exist")
        if len(c.pool("dataplane").cpu_lists()) == 0:
            raise KeyError("No CPU list in dataplane pool")
        num_slots = len(c.pool("dataplane").cpu_lists())

    patch_path = ("/status/capacity/pod.alpha.kubernetes.io~1opaque-int-"
                  "resource-kcm")
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
    patch_path = "/metadata/labels/kcm.intel.com~1kcm-node"
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

    # Filter existing "kcm" taint, if it exists.
    node_taints_list = [t for t in node_taints_list if t["key"] != "kcm"]

    node_taints_list.append({
        "key": "kcm",
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


# patch_k8s_node_status patches the kubernetes node with KCM OIR with
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
