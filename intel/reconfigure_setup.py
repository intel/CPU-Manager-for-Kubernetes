from . import k8s, clusterinit
from kubernetes.client.rest import ApiException as K8sApiException
import logging
import sys


def reconfigure_setup(num_exclusive_cores, num_shared_cores,
                      excl_non_isolcpus, exclusive_mode,
                      shared_mode, cmk_img, cmk_img_pol, install_dir,
                      saname, namespace):

    # Get all nodes that have the CMK taint
    cmk_nodes = get_cmk_nodes()
    logging.info("Reconfiguring nodes {}".format(", ".join(cmk_nodes)))

    execute_reconfigure(num_exclusive_cores, num_shared_cores,
                        excl_non_isolcpus, exclusive_mode,
                        shared_mode, cmk_img, cmk_img_pol, install_dir,
                        cmk_nodes, saname, namespace)


def get_cmk_nodes():
    node_list = k8s.get_compute_nodes(None)
    cmk_nodes = []
    for node in node_list:
        try:
            if node["metadata"]["labels"]["cmk.intel.com/cmk-node"] == "true":
                cmk_nodes.append(node["metadata"]["name"])
        except KeyError:
            continue

    if len(cmk_nodes) < 1:
        logging.error("No CMK nodes detected, aborting...")
        sys.exit(1)

    return cmk_nodes


def execute_reconfigure(num_exclusive_cores, num_shared_cores,
                        excl_non_isolcpus, exclusive_mode,
                        shared_mode, cmk_img, cmk_img_pol, install_dir,
                        cmk_nodes, saname, namespace):
    for node_name in cmk_nodes:
        pod = k8s.get_pod_template()
        clusterinit.update_pod(pod, "Never", install_dir, saname)
        args = "/cmk/cmk.py reconfigure --node-name={}"\
               " --num-exclusive-cores={} --num-shared-cores={}"\
               " --excl-non-isolcpus={} --exclusive-mode={}"\
               " --shared-mode={} --install-dir={}"\
               " --namespace={}"\
               .format(node_name, num_exclusive_cores,
                       num_shared_cores, excl_non_isolcpus,
                       exclusive_mode, shared_mode,
                       install_dir, namespace)

        clusterinit.update_pod_with_container(pod, "reconfigure", cmk_img,
                                              cmk_img_pol, args)

        clusterinit.update_pod_with_node_details(pod, node_name,
                                                 ["reconfigure"])

        try:
            cr_pod_resp = k8s.create_pod(None, pod, namespace)
            logging.debug("Response while creating pod for"
                          " reconfigure command: {}".format(cr_pod_resp))
        except K8sApiException as err:
            logging.error("Exception when creating pod for"
                          " reconfigure command: {}".format(err.reason))
            logging.error("Aborting reconfigure ...")
            sys.exit(1)

        pod_name = "cmk-reconfigure-pod-{}".format(node_name)
        pod_phase_name = "Succeeded"
        try:
            clusterinit.wait_for_pod_phase(pod_name, pod_phase_name)
        except RuntimeError as err:
            logging.error("Exception while waiting for pod to succeed: {}"
                          .format(err))
            logging.error("Aborting reconfigure ...")
            sys.exit(1)
