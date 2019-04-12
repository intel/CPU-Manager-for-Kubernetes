# Copyright (c) 2018 Intel Corporation
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

import json
import logging
import sys
import yaml

from kubernetes import client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException

from intel import k8s, util


def cluster_init(host_list, all_hosts, cmd_list, cmk_img, cmk_img_pol,
                 conf_dir, install_dir, num_exclusive_cores, num_shared_cores,
                 pull_secret, serviceaccount, exclusive_mode, shared_mode,
                 namespace):
    logging.info("Used ServiceAccount: {}".format(serviceaccount))
    cmk_node_list = get_cmk_node_list(host_list, all_hosts)
    logging.debug("CMK node list: {}".format(cmk_node_list))

    cmk_cmd_list = [cmd.strip() for cmd in cmd_list.split(',')]
    logging.debug("CMK command list: {}".format(cmk_cmd_list))

    # Check if all the flag values passed are valid.
    # Check if cmk_cmd_list is valid.
    valid_cmd_list = ["init", "discover", "install", "reconcile", "nodereport"]
    for cmk_cmd in cmk_cmd_list:
        if cmk_cmd not in valid_cmd_list:
            raise RuntimeError("CMK command should be one of {}"
                               .format(valid_cmd_list))
    if "init" in cmk_cmd_list and cmk_cmd_list[0] != "init":
        raise RuntimeError("init command should be run and listed first.")

    # Check if cmk_img_pol is valid.
    valid_img_pol_list = ["Never", "IfNotPresent", "Always"]
    if cmk_img_pol not in valid_img_pol_list:
        raise RuntimeError("Image pull policy should be one of {}"
                           .format(valid_img_pol_list))

    # Check if num_exclusive_cores and num_shared_cores are positive integers.
    if not num_exclusive_cores.isdigit():
        raise RuntimeError("num_exclusive_cores cores should be a positive "
                           "integer.")
    if not num_shared_cores.isdigit():
        raise RuntimeError("num_shared_cores cores should be a positive "
                           "integer.")

    # Split the cmk_cmd_list based on whether the cmd should be run as
    # one-shot job or long-running daemons.
    cmd_init_list = ["init", "discover", "install"]
    cmk_cmd_init_list = [cmd for cmd in cmk_cmd_list if cmd in cmd_init_list]
    cmk_cmd_list = [cmd for cmd in cmk_cmd_list if cmd not in cmd_init_list]

    # Run the pods based on the cmk_cmd_init_list and cmk_cmd_list with
    # provided options.
    if cmk_cmd_init_list:
        run_pods(None, cmk_cmd_init_list, cmk_img, cmk_img_pol, conf_dir,
                 install_dir, num_exclusive_cores, num_shared_cores,
                 cmk_node_list, pull_secret, serviceaccount, shared_mode,
                 exclusive_mode, namespace)
    if cmk_cmd_list:
        run_pods(cmk_cmd_list, None, cmk_img, cmk_img_pol, conf_dir,
                 install_dir, num_exclusive_cores, num_shared_cores,
                 cmk_node_list, pull_secret, serviceaccount, shared_mode,
                 exclusive_mode, namespace)

    # Run mutating webhook admission controller on supported cluster
    version = util.parse_version(k8s.get_kubelet_version(None))
    if version >= util.parse_version("v1.9.0"):
        deploy_webhook(namespace, conf_dir, install_dir, serviceaccount,
                       cmk_img)


# run_pods() runs the pods based on the cmd_list and cmd_init_list
# using run_cmd_pods. It waits for the pods to go into a pod phase based
# on pod_phase_name.
# Note: Only one of cmd_list or cmd_init_list should be specified.
def run_pods(cmd_list, cmd_init_list, cmk_img, cmk_img_pol, conf_dir,
             install_dir, num_exclusive_cores, num_shared_cores, cmk_node_list,
             pull_secret, serviceaccount, shared_mode, exclusive_mode,
             namespace):
    if cmd_list:
        logging.info("Creating cmk pod for {} commands ...".format(cmd_list))
    elif cmd_init_list:
        logging.info("Creating cmk pod for {} commands ..."
                     .format(cmd_init_list))

    run_cmd_pods(cmd_list, cmd_init_list, cmk_img, cmk_img_pol, conf_dir,
                 install_dir, num_exclusive_cores, num_shared_cores,
                 cmk_node_list, pull_secret, serviceaccount, shared_mode,
                 exclusive_mode, namespace)

    pod_name_prefix = ""
    pod_phase_name = ""
    if cmd_init_list:
        pod_name_prefix = "cmk-{}-pod-".format("-".join(cmd_init_list))
        pod_phase_name = "Succeeded"
        logging.info("Waiting for cmk pod running {} cmds to enter {} state."
                     .format(cmd_init_list, pod_phase_name))
    elif cmd_list:
        pod_name_prefix = "cmk-{}-ds-".format("-".join(cmd_list))
        pod_phase_name = "Running"
        logging.info("Waiting for cmk pod running {} cmds to enter {} state."
                     .format(cmd_list, pod_phase_name))

    for node in cmk_node_list:
        pod_name = "{}{}".format(pod_name_prefix, node)
        try:
            wait_for_pod_phase(pod_name, pod_phase_name)
        except RuntimeError as err:
            logging.error("{}".format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


# run_cmd_pods() makes the appropriate changes to pod templates and runs the
# pod on each node provided by cmk_node_list.
def run_cmd_pods(cmd_list, cmd_init_list, cmk_img, cmk_img_pol, conf_dir,
                 install_dir, num_exclusive_cores, num_shared_cores,
                 cmk_node_list, pull_secret, serviceaccount, shared_mode,
                 exclusive_mode, namespace):
    pod = k8s.get_pod_template()
    if pull_secret:
        update_pod_with_pull_secret(pod, pull_secret)
    if cmd_list:
        update_pod(pod, "Always", conf_dir, install_dir, serviceaccount)
        version = util.parse_version(k8s.get_kubelet_version(None))
        if version >= util.parse_version("v1.7.0"):
            pod["spec"]["tolerations"] = [{
                "operator": "Exists"}]
        for cmd in cmd_list:
            args = ""
            if cmd == "reconcile":
                args = "/cmk/cmk.py isolate --pool=infra /cmk/cmk.py -- reconcile --interval=5 --publish"  # noqa: E501
            elif cmd == "nodereport":
                args = "/cmk/cmk.py isolate --pool=infra /cmk/cmk.py -- node-report --interval=5 --publish"  # noqa: E501

            update_pod_with_container(pod, cmd, cmk_img, cmk_img_pol, args)
    elif cmd_init_list:
        update_pod(pod, "Never", conf_dir, install_dir, serviceaccount)
        for cmd in cmd_init_list:
            args = ""
            if cmd == "init":
                args = ("/cmk/cmk.py init --num-exclusive-cores={} "
                        "--num-shared-cores={} --shared-mode={} "
                        "--exclusive-mode={}")\
                    .format(num_exclusive_cores, num_shared_cores, shared_mode,
                            exclusive_mode)
                # If init is the only cmd in cmd_init_list, it should be run
                # as regular container as spec.containers is a required field.
                # Otherwise, it should be run as init-container.
                if len(cmd_init_list) == 1:
                    update_pod_with_container(pod, cmd, cmk_img,
                                              cmk_img_pol, args)
                else:
                    update_pod_with_init_container(pod, cmd, cmk_img,
                                                   cmk_img_pol, args)
            else:
                if cmd == "discover":
                    args = "/cmk/cmk.py discover"
                elif cmd == "install":
                    args = "/cmk/cmk.py install"
                update_pod_with_container(pod, cmd, cmk_img, cmk_img_pol,
                                          args)

    for node_name in cmk_node_list:
        if cmd_list:
            update_pod_with_node_details(pod, node_name, cmd_list)
            daemon_set = k8s.ds_from(pod=pod)
        elif cmd_init_list:
            update_pod_with_node_details(pod, node_name, cmd_init_list)

        try:
            if cmd_list:
                cr_pod_resp = k8s.create_ds(None, daemon_set, namespace)
                logging.debug("Response while creating ds for {} command(s): "
                              "{}".format(cmd_list, cr_pod_resp))
            elif cmd_init_list:
                cr_pod_resp = k8s.create_pod(None, pod, namespace)
                logging.debug("Response while creating pod for {} command(s): "
                              "{}".format(cmd_init_list, cr_pod_resp))
        except K8sApiException as err:
            if cmd_list:
                logging.error("Exception when creating pod for {} command(s): "
                              "{}".format(cmd_list, err))
            elif cmd_init_list:
                logging.error("Exception when creating pod for {} command(s): "
                              "{}".format(cmd_init_list, err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)


# deploy_webhook() creates mutating webhook admission controller configuration,
# pod and all required resources.
def deploy_webhook(namespace, conf_dir, install_dir, saname, cmk_img):
    prefix = "cmk-webhook"

    service_name = '-'.join([prefix, "service"])
    cert, key = util.generate_secrets(service_name, namespace)

    app_name = '-'.join([prefix, "app"])

    secret_data = {"cert.pem": cert, "key.pem": key}
    secret_name = '-'.join([prefix, "certs"])
    secret = k8sclient.V1Secret()
    update_secret(secret, secret_name, secret_data, "Opaque")
    try:
        k8s.create_secret(None, secret, namespace)
    except K8sApiException as err:
        if err.status == 409:
            logging.debug("Secret {} already exists".format(secret_name))
        else:
            logging.error("Exception when creating secret: {}".format(err))
            logging.error("Aborting webhook deployment ...")
            sys.exit(1)

    configmap = k8sclient.V1ConfigMap()
    configmap_name = '-'.join([prefix, "configmap"])
    configmap_data = {
        "server.yaml": yaml.dump(get_default_webhook_server_config()),
        "mutations.yaml": yaml.dump(get_default_webhook_mutations_config()),
    }
    update_configmap(configmap, configmap_name, configmap_data)
    try:
        k8s.create_config_map(None, configmap, namespace)
    except K8sApiException as err:
        if err.status == 409:
            logging.debug("configmap {} already exists".format(configmap_name))
        else:
            logging.error("Exception when creating config map: {}".format(err))
            logging.error("Aborting webhook deployment ...")
            sys.exit(1)

    service = k8sclient.V1Service()
    update_service(service, service_name, app_name, 443)
    try:
        k8s.create_service(None, service, namespace)
    except K8sApiException as err:
        if err.status == 409:
            logging.debug("service {} already exists".format(service_name))
        else:
            logging.error("Exception when creating service: {}".format(err))
            logging.error("Aborting webhook deployment ...")
            sys.exit(1)

    pod = k8s.get_pod_template()
    pod_name = '-'.join([prefix, "pod"])
    update_pod_with_metadata(pod, pod_name, app_name)
    update_pod_with_webhook_container(pod, cmk_img, configmap_name,
                                      secret_name)
    update_pod_with_restart_policy(pod, "Always")
    deployment = k8s.deployment_from(pod)
    try:
        k8s.create_deployment(None, deployment, namespace)
    except K8sApiException as err:
        if err.status == 409:
            logging.debug("deployment {} already exists".format(deployment))
        else:
            logging.error("Exception when creating webhook deployment: {}"
                          .format(err))
            logging.error("Aborting webhook deployment ...")
            sys.exit(1)

    config = k8sclient.V1beta1MutatingWebhookConfiguration()
    config_name = '-'.join([prefix, "config"])
    update_mutatingwebhookconfiguration(config,
                                        config_name,
                                        app_name,
                                        "cmk.intel.com",
                                        cert,
                                        service_name,
                                        "/mutate",
                                        namespace,
                                        "Ignore")
    try:
        k8s.create_mutating_webhook_configuration(None, config)
    except K8sApiException as err:
        if err.status == 409:
            logging.debug("mutating_webhook {} already exists"
                          .format(config_name))
        else:
            logging.error("Exception when creating webhook configuration: {}"
                          .format(err))
            logging.error("Aborting webhook deployment ...")
            sys.exit(1)


# get_cmk_node_list() returns a list of nodes based on either host_list or
# all_hosts.
def get_cmk_node_list(host_list, all_hosts):
    cmk_node_list = []
    if host_list:
        cmk_node_list = [host.strip() for host in host_list.split(',')]
    if all_hosts:
        try:
            node_list_resp = k8s.get_compute_nodes(None)
            for node in node_list_resp:
                cmk_node_list.append(node["metadata"]["name"])
        except K8sApiException as err:
            logging.error("Exception when getting the node list: {}"
                          .format(err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)
    return cmk_node_list


# wait_for_pod_phase() waits for a pod to go into a pod phase specified by
# phase_name. It raises an error if the pod goes into a failed state.
def wait_for_pod_phase(pod_name, phase_name):
    wait = True
    while wait:
        try:
            pod_list_resp = k8s.get_pod_list(None)
        except K8sApiException as err:
            logging.error("Exception while waiting for Pod [{}] status: {}"
                          .format(pod_name, err))
            logging.error("Aborting cluster-init ...")
            sys.exit(1)

        for pod in pod_list_resp["items"]:
            if ("metadata" in pod) and ("name" in pod["metadata"]) \
                    and pod_name in pod["metadata"]["name"]:
                if pod["status"]["phase"] == phase_name:
                    wait = False
                    break
                elif pod["status"]["phase"] == "Failed":
                    raise RuntimeError("The Pod {} went into Failed state"
                                       .format(pod_name))


# update_pod() updates the pod template with the provided options.
def update_pod(pod, restart_pol, conf_dir, install_dir, serviceaccount):
    pod["spec"]["serviceAccountName"] = serviceaccount
    pod["spec"]["restartPolicy"] = restart_pol
    pod["spec"]["volumes"][1]["hostPath"]["path"] = conf_dir
    pod["spec"]["volumes"][2]["hostPath"]["path"] = install_dir


def update_pod_with_node_details(pod, node_name, cmd_list):
    pod["spec"]["nodeName"] = node_name
    pod_name = "cmk-{}-pod-{}".format("-".join(cmd_list), node_name)
    pod["metadata"]["name"] = pod_name


def update_pod_with_pull_secret(pod, pull_secret):
    pod["spec"]["imagePullSecrets"] = [{"name": pull_secret}]


def update_pod_with_metadata(pod, name, app):
    pod["metadata"]["name"] = name
    pod["metadata"]["labels"] = {"app": app}


def update_pod_with_restart_policy(pod, restart_pol):
    pod["spec"]["restartPolicy"] = restart_pol


# update_pod_with_container() updates the pod template with a container using
# the provided options.
def update_pod_with_container(pod, cmd, cmk_img, cmk_img_pol, args):
    container_template = k8s.get_container_template()
    container_template["image"] = cmk_img
    container_template["imagePullPolicy"] = cmk_img_pol
    container_template["args"][0] = args
    # Each container name should be distinct within a Pod.
    container_template["name"] = cmd
    pod["spec"]["containers"].append(container_template)


# update_pod_with_init_container() updates the pod template with a init
# container using the provided options.
def update_pod_with_init_container(pod, cmd, cmk_img, cmk_img_pol, args):
    container_template = k8s.get_container_template()
    container_template["image"] = cmk_img
    container_template["imagePullPolicy"] = cmk_img_pol
    container_template["args"][0] = args
    # Each container name should be distinct within a Pod.
    container_template["name"] = cmd
    # Note(balajismaniam): Downward API for spec.nodeName doesn't seem to
    # work with init-containers. Removing it as a work-around. Needs further
    # investigation.
    container_template["env"].pop()
    pod_init_containers_list = []

    version = util.parse_version(k8s.get_kubelet_version(None))

    if version >= util.parse_version("v1.7.0"):
        pod["spec"]["initContainers"] = [container_template]
    else:

        init_containers_key = "pod.beta.kubernetes.io/init-containers"

        if init_containers_key in pod["metadata"]["annotations"]:
            init_containers = \
                pod["metadata"]["annotations"][init_containers_key]
            pod_init_containers_list = json.loads(init_containers)

        pod_init_containers_list.append(container_template)
        pod["metadata"]["annotations"][init_containers_key] = \
            json.dumps(pod_init_containers_list)


def update_pod_with_webhook_container(pod, cmk_img, configmap_name,
                                      secret_name):
    container = k8s.get_container_template()
    args = ("/cmk/cmk.py webhook --conf-file /etc/webhook/server.yaml")
    container["args"] = [args]
    container["image"] = cmk_img
    container["name"] = "cmk-webhook"
    container["volumeMounts"].append({
        'mountPath': '/etc/webhook',
        'name': 'configmap'
    })
    container["volumeMounts"].append({
        'mountPath': '/etc/ssl',
        'name': 'certs',
        'readOnly': True
    })
    pod["spec"]["volumes"].append({
        'name': 'configmap',
        'configMap': {
            'name': configmap_name
        }
    })
    pod["spec"]["volumes"].append({
        'name': 'certs',
        'secret': {
            'secretName': secret_name
         }
    })
    pod["spec"]["tolerations"] = [{"operator": "Exists"}]
    pod["spec"]["containers"].append(container)
    pod["spec"].pop("nodeName")


def update_secret(secret, name, data, secret_type):
    secret.metadata = k8sclient.V1ObjectMeta()
    secret.metadata.name = name
    secret.data = data
    secret.type = secret_type


def update_configmap(configmap, name, data):
    configmap.metadata = k8sclient.V1ObjectMeta()
    configmap.metadata.name = name
    configmap.data = data


def update_service(service, name, app, port):
    service.metadata = k8sclient.V1ObjectMeta()
    service.metadata.name = name
    service.metadata.labels = {"app": app}
    service.spec = k8sclient.V1ServiceSpec()
    service.spec.selector = {"app": app}
    service_port = k8sclient.V1ServicePort(port=port, target_port=port)
    service.spec.ports = [service_port]


def update_mutatingwebhookconfiguration(config, name, app, webhook_name, cert,
                                        service, path, namespace,
                                        failure_policy):
    config.metadata = k8sclient.V1ObjectMeta()
    config.metadata.name = name
    config.metadata.labels = {"app": app}
    client_config = k8sclient.V1beta1WebhookClientConfig(
        ca_bundle=cert,
        service=k8sclient.AdmissionregistrationV1beta1ServiceReference(
            name=service,
            namespace=namespace,
            path=path))
    webhook = k8sclient.V1beta1Webhook(name=webhook_name,
                                       client_config=client_config,
                                       failure_policy=failure_policy)
    webhook.rules = [{
        "apiGroups": [""],
        "apiVersions": ["v1"],
        "operations": ["CREATE"],
        "resources": ["pods"]
    }]
    config.webhooks = [webhook]


def get_default_webhook_server_config():
    config = {
        "server": {
            "binding-address": "0.0.0.0",
            "port": 443,
            "cert": "/etc/ssl/cert.pem",
            "key": "/etc/ssl/key.pem",
            "mutations": "/etc/webhook/mutations.yaml"
        }
    }
    return config


def get_default_webhook_mutations_config():
    config = {
        "mutations": {
            "perPod": {
                "metadata": {
                    "annotations": {
                        "cmk.intel.com/resources-injected": "true"
                    }
                },
                "spec": {
                    "serviceAccount": "cmk-serviceaccount",
                    "tolerations": [
                        {
                            "operator": "Exists"
                        }
                    ],
                    "volumes": [
                        {
                            "name": "cmk-host-proc",
                            "hostPath": {
                                "path": "/proc"
                            }
                        },
                        {
                            "name": "cmk-config-dir",
                            "hostPath": {
                                "path": "/etc/cmk"
                            }
                        },
                        {
                            "name": "cmk-install-dir",
                            "hostPath": {
                                "path": "/opt/bin"
                            }
                        }
                    ]
                }
            },
            "perContainer": {
                "env": [
                    {
                        "name": "CMK_PROC_FS",
                        "value": "/host/proc"
                    }
                ],
                "volumeMounts": [
                    {
                        "name": "cmk-host-proc",
                        "mountPath": "/host/proc",
                        "readOnly": True
                    },
                    {
                        "name": "cmk-config-dir",
                        "mountPath": "/etc/cmk"
                    },
                    {
                        "name": "cmk-install-dir",
                        "mountPath": "/opt/bin"
                    }
                ]
            }
        }
    }
    return config
