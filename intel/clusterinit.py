import logging
import sys
from kubernetes import config as k8sconfig, client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException


def cluster_init(host_list, all_hosts, cmd_list, kcm_img, kcm_img_pol,
                 conf_dir, install_dir, num_dp_cores, num_cp_cores):
    kcm_node_list = get_kcm_node_list(host_list, all_hosts)
    logging.debug("KCM node list: {}".format(kcm_node_list))

    kcm_cmd_list = [cmd.strip() for cmd in cmd_list.split(',')]
    logging.debug("KCM command list: {}".format(kcm_cmd_list))

    # Check if all the flag values passed are valid.
    # Check if kcm_cmd_list is valid.
    valid_cmd_list = ["init", "discover", "install", "reconcile"]
    for kcm_cmd in kcm_cmd_list:
        if kcm_cmd not in valid_cmd_list:
            raise RuntimeError("KCM command should be one of {}"
                               .format(valid_cmd_list))
    if "init" in kcm_cmd_list and kcm_cmd_list[0] != "init":
        raise RuntimeError("init command should be run and listed first.")

    # Check if kcm_img_pol is valid.
    valid_img_pol_list = ["Never", "IfNotPresent", "Always"]
    if kcm_img_pol not in valid_img_pol_list:
        raise RuntimeError("Image pull policy should be one of {}"
                           .format(valid_img_pol_list))

    # Check if num_dp_cores and num_cp_cores are positive integers.
    if not num_dp_cores.isdigit():
        raise RuntimeError("num_dp_cores cores should be a positive integer.")
    if not num_cp_cores.isdigit():
        raise RuntimeError("num_cp_cores cores should be a positive integer.")

    # Run the pods based on the kcm_cmd_list and the provided options.
    for cmd in kcm_cmd_list:
        run_pods(cmd, kcm_img, kcm_img_pol, conf_dir, install_dir,
                 num_dp_cores, num_cp_cores, kcm_node_list)


# run_pods() runs the pods based on the kcm_cmd_name using run_cmd_pods.
# It waits for the pods to go into a pod phase based on pod_phase_name.
def run_pods(kcm_cmd_name, kcm_img, kcm_img_pol, conf_dir, install_dir,
             num_dp_cores, num_cp_cores, kcm_node_list):
    logging.info("Creating kcm {} pods ...".format(kcm_cmd_name))
    run_cmd_pods(kcm_cmd_name, kcm_img, kcm_img_pol, conf_dir, install_dir,
                 kcm_node_list, num_dp_cores, num_cp_cores)

    pod_name_prefix = "kcm-{}-pod-".format(kcm_cmd_name)
    pod_phase_name = ""
    if kcm_cmd_name in ["init", "discover", "install"]:
        pod_phase_name = "Succeeded"
    elif kcm_cmd_name == "reconcile":
        pod_phase_name = "Running"

    logging.info("Waiting for kcm {} pods to enter {} state."
                 .format(kcm_cmd_name, pod_phase_name))
    for node in kcm_node_list:
        pod_name = "{}{}".format(pod_name_prefix, node)
        try:
            wait_for_pod_phase(pod_name, pod_phase_name)
        except RuntimeError as err:
            logging.error("{}".format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


# run_cmd_pods() makes the appropriate changes to pod templates and runs the
# pod on each node provided by kcm_node_list.
def run_cmd_pods(kcm_cmd_name, kcm_img, kcm_img_pol, conf_dir, install_dir,
                 kcm_node_list, num_dp_cores, num_cp_cores):
    pod_template = get_pod_template()
    for node in kcm_node_list:
        pod_name = "kcm-{}-pod-{}".format(kcm_cmd_name, node)
        pod_template["metadata"]["name"] = pod_name
        pod_template["spec"]["nodeName"] = node
        pod_template["spec"]["containers"][0]["image"] = kcm_img
        pod_template["spec"]["containers"][0]["imagePullPolicy"] = kcm_img_pol

        if kcm_cmd_name == "install":
            pod_template["spec"]["volumes"][2]["hostPath"]["path"] = \
                    install_dir
        else:
            pod_template["spec"]["volumes"][1]["hostPath"]["path"] = \
                    conf_dir

        if kcm_cmd_name == "init":
            pod_template["spec"]["containers"][0]["args"][0] = \
                    "/kcm/kcm.py init --num-dp-cores={} --num-cp-cores={}"\
                    .format(num_dp_cores, num_cp_cores)
        elif kcm_cmd_name == "discover":
            pod_template["spec"]["containers"][0]["args"][0] = \
                    "/kcm/kcm.py discover"
        elif kcm_cmd_name == "install":
            pod_template["spec"]["containers"][0]["args"][0] = \
                    "/kcm/kcm.py install"
        elif kcm_cmd_name == "reconcile":
            pod_template["spec"]["containers"][0]["args"][0] = \
                    "/kcm/kcm.py reconcile --interval=60"

        try:
            create_pod_resp = create_k8s_pod(pod_template)
            logging.debug("Response while creating {} pods: {}"
                          .format(kcm_cmd_name, create_pod_resp))
        except K8sApiException as err:
            logging.error("Exception when creating {} pod: {}"
                          .format(kcm_cmd_name, err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


# get_kcm_node_list() returns a list of nodes based on either host_list or
# all_hosts.
def get_kcm_node_list(host_list, all_hosts):
    kcm_node_list = []
    if host_list:
        kcm_node_list = [host.strip() for host in host_list.split(',')]
    if all_hosts:
        try:
            node_list_resp = get_k8s_node_list()
            for node in node_list_resp["items"]:
                kcm_node_list.append(node["metadata"]["name"])
        except K8sApiException as err:
            logging.error("Exception when getting the node list: {}"
                          .format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)
    return kcm_node_list


# wait_for_pod_phase() waits for a pod to go into a pod phase specified by
# phase_name. It raises an error if the pod goes into a failed state.
def wait_for_pod_phase(pod_name, phase_name):
    wait = True
    while wait:
        try:
            pod_list_resp = get_k8s_pod_list()
        except K8sApiException as err:
            logging.error("Exception while waiting for Pod [{}] status: {}"
                          .format(pod_name, err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)

        for pod in pod_list_resp["items"]:
            if pod["metadata"]["name"] == pod_name:
                if pod["status"]["phase"] == phase_name:
                    wait = False
                    break
                elif pod["status"]["phase"] == "Failed":
                    raise RuntimeError("The Pod {} went into Failed state"
                                       .format(pod_name))


# get_k8s_node_list() returns the node list in the current Kubernetes cluster.
def get_k8s_node_list():
    k8sconfig.load_incluster_config()
    k8s_api = k8sclient.CoreV1Api()
    return k8s_api.list_node().to_dict()


# get_k8s_pod_list() returns the pod list in the current Kubernetes cluster.
def get_k8s_pod_list():
    k8sconfig.load_incluster_config()
    k8s_api = k8sclient.CoreV1Api()
    return k8s_api.list_pod_for_all_namespaces().to_dict()


# create_k8s_pod() sends a request to the Kubernetes API server to create a
# pod based on podspec.
def create_k8s_pod(podspec):
    k8sconfig.load_incluster_config()
    k8s_api = k8sclient.CoreV1Api()
    return k8s_api.create_namespaced_pod("default", podspec)


def get_pod_template():
    pod_template = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "PODNAME"
            },
            "spec": {
                "nodeName": "NODENAME",
                "containers": [
                    {
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
                        "name": "kcm-reconcile-container",
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
