import os
import logging
from intel import config
from kubernetes import config as k8sconfig, client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException


# discover reads the KCM configuration file and patches kubernetes nodes with
# appropriate number of KCM Opaque Integer Resource (OIR) slots.
def discover(conf_dir):
    c = config.Config(conf_dir)
    with c.lock():
        if "dataplane" not in c.pools():
            raise KeyError("Dataplane pool does not exist")
        if len(c.pools()["dataplane"].cpu_lists()) == 0:
            raise KeyError("No CPU list in dataplane pool")
        num_slots = len(c.pools()["dataplane"].cpu_lists())

    try:
        patch_k8s_node(num_slots)
    except K8sApiException as err:
        logging.warning("Exception when patching the node: {}".format(err))


# patch_k8s_node patches the kubernetes node with KCM OIR with value num_slots.
def patch_k8s_node(num_slots):
    k8sconfig.load_incluster_config()
    k8sapi = k8sclient.CoreV1Api()

    node_name = os.getenv("NODE_NAME")
    patch_path = ('/status/capacity/pod.alpha.kubernetes.io~1opaque-int-'
                  'resource-kcm')
    body = [{
        "op": "add",
        "path": patch_path,
        "value": num_slots
    }]

    # Patch the node with the specified number of opaque integer resources.
    k8sapi.patch_node_status(node_name, body)
