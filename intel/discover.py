import ast
from intel import config
import json
from kubernetes import config as k8sconfig, client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException
import logging
import os


# discover reads the KCM configuration file, patches kubernetes nodes with
# appropriate number of KCM Opaque Integer Resource (OIR) slots and applies
# the appropriate KCM node labels and taints.
def discover(conf_dir):
    # Patch the node with the appropriate KCM OIR.
    add_node_oir(conf_dir)
    # Add appropriate KCM label to the node.
    add_node_label()
    # Add appropriate KCM taint to the node.
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

    patch_path = ('/status/capacity/pod.alpha.kubernetes.io~1opaque-int-'
                  'resource-kcm')
    patch_body = [{
        "op": "add",
        "path": patch_path,
        "value": num_slots
    }]

    try:
        patch_k8s_node_status(patch_body)
    except K8sApiException as err:
        logging.warning("Exception when patching the node with OIR: {}"
                        .format(err))


def add_node_label():
    patch_path = '/metadata/labels/kcm.intel.com~1kcm-node'
    patch_body = [{
        "op": "add",
        "path": patch_path,
        "value": "true"
    }]

    try:
        patch_k8s_node(patch_body)
    except K8sApiException as err:
        logging.warning("Exception when labeling the node: {}".format(err))


def add_node_taint():
    node_name = os.getenv("NODE_NAME")
    try:
        node_resp = get_k8s_node(node_name)
    except K8sApiException as err:
        logging.warning("Exception when getting the node obj: {}".format(err))

    node_taints_list = []
    node_taint_key = "scheduler.alpha.kubernetes.io/taints"
    if node_resp["metadata"]["annotations"][node_taint_key]:
        node_taints = node_resp["metadata"]["annotations"][node_taint_key]
        node_taints_list = ast.literal_eval(node_taints)

    kcm_taint = {
            "key": "kcm",
            "value": "true",
            "effect": "NoSchedule"
    }
    node_taints_list.append(kcm_taint)

    patch_path = '/metadata/annotations/scheduler.alpha.kubernetes.io~1taints'
    patch_body = [{
        "op": "replace",
        "path": patch_path,
        "value": json.dumps(node_taints_list)
    }]

    try:
        patch_k8s_node(patch_body)
    except K8sApiException as err:
        logging.warning("Exception when tainiting the node: {}".format(err))


# patch_k8s_node_status patches the kubernetes node with KCM OIR with
# value num_slots.
def patch_k8s_node_status(patch_body):
    k8sconfig.load_incluster_config()
    k8sapi = k8sclient.CoreV1Api()
    node_name = os.getenv("NODE_NAME")

    # Patch the node with the specified number of opaque integer resources.
    k8sapi.patch_node_status(node_name, patch_body)


def patch_k8s_node(patch_body):
    k8sconfig.load_incluster_config()
    k8sapi = k8sclient.CoreV1Api()
    node_name = os.getenv("NODE_NAME")

    # Patch the node with the specified number of opaque integer resources.
    k8sapi.patch_node(node_name, patch_body)


# get_k8s_node() retuns the node spec associated with node_name.
def get_k8s_node(node_name):
    try:
        node_list_resp = get_k8s_node_list()
    except K8sApiException as err:
        logging.warning("Exception when patching the node: {}".format(err))

    for node in node_list_resp["items"]:
        if node["metadata"]["name"] == node_name:
            return node


# get_k8s_node_list() returns the node list in the current Kubernetes cluster.
def get_k8s_node_list():
    k8sconfig.load_incluster_config()
    k8s_api = k8sclient.CoreV1Api()
    return k8s_api.list_node().to_dict()
