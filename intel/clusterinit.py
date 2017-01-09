import logging
import sys
from kubernetes import config as k8sconfig, client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException


def cluster_init(host_list, all_hosts, cmd_list, kcm_img, kcm_cmd_list,
                 conf_dir, install_dir, num_dp_cores, num_cp_cores):
    k8sconfig.load_incluster_config()

    kcm_node_list = get_kcm_node_list(host_list, all_hosts)
    logging.debug("KCM node list: {}".format(kcm_node_list))

    kcm_cmd_list = [cmd.strip() for cmd in cmd_list.split(',')]
    logging.debug("KCM command list: {}".format(kcm_cmd_list))

    # The order in which the pods are run is important.
    # The init pods should be run first to setup KCM config dir.
    if "init" in kcm_cmd_list and kcm_cmd_list[0] != "init":
        raise RuntimeError("init command should be listed first.")

    for cmd in kcm_cmd_list:
        run_pods(cmd, kcm_img, conf_dir, install_dir, kcm_node_list,
                 num_dp_cores, num_cp_cores)


def run_pods(kcm_cmd_name, kcm_img, conf_dir, install_dir, kcm_node_list):
    logging.info("Creating kcm {} pods ...".format(kcm_cmd_name))

    pod_run_func_name = "run_{}_pods".format(kcm_cmd_name)
    pod_name_prefix = "kcm-{}-pod-".format(kcm_cmd_name)
    pod_phase_name = ""
    if kcm_cmd_name in ["init", "discover", "install"]:
        pod_phase_name = "Succeeded"
    elif kcm_cmd_name == "reconcile":
        pod_phase_name = "Running"

    current_module = sys.modules[__name__]
    getattr(current_module, pod_run_func_name)(kcm_img, conf_dir,
                                               install_dir, kcm_node_list)

    logging.info("Waiting for kcm {} pods to enter {} state."
                 .format(kcm_cmd_name, pod_phase_name))
    for node in kcm_node_list:
        pod_name = pod_name_prefix + node
        try:
            wait_for_pod_phase(pod_name, pod_phase_name)
        except RuntimeError as err:
            logging.error("{}".format(pod_name, err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


def get_k8s_node_list():
    k8s_api = k8sclient.CoreV1Api()
    return k8s_api.list_node()


def get_k8s_pod_list():
    k8s_api = k8sclient.CoreV1Api()
    return k8s_api.list_pod_for_all_namespaces()


def create_k8s_pod(podspec):
    k8s_api = k8sclient.CoreV1Api()
    return k8s_api.create_namespaced_pod("default", podspec)


def get_kcm_node_list(host_list, all_hosts):
    kcm_node_list = []
    if host_list:
        kcm_node_list = [host.strip() for host in host_list.split(',')]
    if all_hosts:
        try:
            node_list_resp = get_k8s_node_list().to_dict()
            for node in node_list_resp["items"]:
                kcm_node_list.append(node["metadata"]["name"])
        except K8sApiException as err:
            logging.error("Exception when getting the node list: {}"
                          .format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)
    return kcm_node_list


def wait_for_pod_phase(pod_name, phase_name):
    wait = True
    while wait:
        try:
            pod_list_resp = get_k8s_pod_list().to_dict()
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


def run_init_pods(kcm_img, conf_dir, install_dir, kcm_node_list,
                  num_dp_cores, num_cp_cores):
    init_pod_template = get_init_pod_template()
    for node in kcm_node_list:
        init_pod_template["metadata"]["name"] = "kcm-init-pod-{}".format(node)
        init_pod_template["spec"]["nodeName"] = node
        init_pod_template["spec"]["containers"][0]["image"] = kcm_img
        init_pod_template["spec"]["containers"][0]["args"][2] = \
            "--num-dp-cores={}".format(num_dp_cores)
        init_pod_template["spec"]["containers"][0]["args"][3] = \
            "--num-cp-cores={}".format(num_cp_cores)
        init_pod_template["spec"]["volumes"][0]["hostPath"]["path"] = conf_dir

        try:
            create_pod_resp = create_k8s_pod(init_pod_template)
            logging.debug("Response while creating init pods: {}"
                          .format(create_pod_resp))
        except K8sApiException as err:
            logging.error("Exception when creating init pod: {}"
                          .format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


def run_discover_pods(kcm_img, conf_dir, install_dir, kcm_node_list):
    discover_pod_template = get_discover_pod_template()
    for node in kcm_node_list:
        discover_pod_template["metadata"]["name"] = \
                "kcm-discover-pod-{}".format(node)
        discover_pod_template["spec"]["nodeName"] = node
        discover_pod_template["spec"]["containers"][0]["image"] = kcm_img
        discover_pod_template["spec"]["volumes"][0]["hostPath"]["path"] = \
            conf_dir

        try:
            create_pod_resp = create_k8s_pod(discover_pod_template)
            logging.debug("Response while creating discover pods: {}"
                          .format(create_pod_resp))
        except K8sApiException as err:
            logging.error("Exception when creating discover pod: {}"
                          .format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


def run_reconcile_pods(kcm_img, conf_dir, install_dir, kcm_node_list):
    reconcile_pod_template = get_reconcile_pod_template()
    for node in kcm_node_list:
        reconcile_pod_template["metadata"]["name"] = \
                "kcm-reconcile-pod-{}".format(node)
        reconcile_pod_template["spec"]["nodeName"] = node
        reconcile_pod_template["spec"]["containers"][0]["image"] = kcm_img
        reconcile_pod_template["spec"]["volumes"][0]["hostPath"]["path"] = \
            conf_dir

        try:
            create_pod_resp = create_k8s_pod(reconcile_pod_template)
            logging.debug("Response while creating reconcile pods: {}"
                          .format(create_pod_resp))
        except K8sApiException as err:
            logging.error("Exception when creating reconcile pod: {}"
                          .format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


def run_install_pods(kcm_img, conf_dir, install_dir, kcm_node_list):
    install_pod_template = get_install_pod_template()
    for node in kcm_node_list:
        install_pod_template["metadata"]["name"] = \
                "kcm-install-pod-{}".format(node)
        install_pod_template["spec"]["nodeName"] = node
        install_pod_template["spec"]["containers"][0]["image"] = kcm_img
        install_pod_template["spec"]["volumes"][0]["hostPath"]["path"] = \
            install_dir

        try:
            create_pod_resp = create_k8s_pod(install_pod_template)
            logging.debug("Response while creating install pods: {}"
                          .format(create_pod_resp))
        except K8sApiException as err:
            logging.error("Exception when creating install pod: {}"
                          .format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


def get_init_pod_template():
    init_pod_template = {
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
                                "/kcm/kcm.py init", "--conf-dir=/etc/kcm",
                                "--num-dp-cores=4", "--num-cp-cores=1"
                            ],
                            "command": [
                                "/bin/bash",
                                "-c"
                            ],
                            "image": "IMAGENAME",
                            "name": "kcm-init-container",
                            "volumeMounts": [
                                {
                                    "mountPath": "/etc/kcm",
                                    "name": "kcm-conf-dir"
                                }
                            ],
                            "imagePullPolicy": "Never"
                        }
                    ],
                    "restartPolicy": "Never",
                    "volumes": [
                        {
                            "hostPath": {
                                "path": "HOSTPATH"
                            },
                            "name": "kcm-conf-dir"
                        }
                    ]
                }
            }
    return init_pod_template


def get_discover_pod_template():
    discover_pod_template = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "PODNAME"
            },
            "spec": {
                "nodeName": "NODE_NAME",
                "containers": [
                    {
                        "args": ["/kcm/kcm.py discover --conf-dir=/etc/kcm"],
                        "command": ["/bin/bash", "-c"],
                        "env": [
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
                        "name": "kcm-discover-container",
                        "volumeMounts": [
                            {
                                "mountPath": "/etc/kcm",
                                "name": "kcm-conf-dir"
                            }
                        ],
                        "imagePullPolicy": "Never"
                    }
                ],
                "restartPolicy": "Never",
                "volumes": [
                    {
                        "hostPath": {
                            "path": "HOSTPATH"
                        },
                        "name": "kcm-conf-dir"
                    }

                ]
            }
        }
    return discover_pod_template


def get_reconcile_pod_template():
    reconcile_pod_template = {
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
                            "sleep 60;",
                            "/kcm/kcm.py reconcile",
                            "--conf-dir=/etc/kcm"
                        ],
                        "command": ["/bin/bash", "-c"],
                        "env": [
                            {
                                "name": "KCM_PROC_FS",
                                "value": "/host/proc"
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
                            }
                        ],
                        "imagePullPolicy": "Never"
                    }
                ],
                "volumes": [
                    {
                        "hostPath": {
                            "path": "/proc"
                        },
                        "name": "host-proc"
                    },
                    {
                        "hostPath": {
                            "path": "HOSTPATH"
                        },
                        "name": "kcm-conf-dir"
                    }
                ]
            }
        }
    return reconcile_pod_template


def get_install_pod_template():
    install_pod_template = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "PODNAME"
            },
            "spec": {
                "nodeName": "NODENAME",
                "containers": [
                    {
                        "args": ["/kcm/kcm.py install --install-dir=/opt/bin"],
                        "command": ["/bin/bash", "-c"],
                        "image": "IMAGENAME",
                        "name": "kcm-install-container",
                        "volumeMounts": [
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
                                "path": "HOSTPATH"
                            },
                            "name": "kcm-install-dir"
                        }
                ]
            }
        }
    return install_pod_template
