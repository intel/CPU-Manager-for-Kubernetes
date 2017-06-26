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

import json
import logging
import sys

from kubernetes.client.rest import ApiException as K8sApiException

from intel import k8s


def cluster_init(host_list, all_hosts, cmd_list, kcm_img, kcm_img_pol,
                 conf_dir, install_dir, num_dp_cores, num_cp_cores,
                 pull_secret):
    kcm_node_list = get_kcm_node_list(host_list, all_hosts)
    logging.debug("KCM node list: {}".format(kcm_node_list))

    kcm_cmd_list = [cmd.strip() for cmd in cmd_list.split(',')]
    logging.debug("KCM command list: {}".format(kcm_cmd_list))

    # Check if all the flag values passed are valid.
    # Check if kcm_cmd_list is valid.
    valid_cmd_list = ["init", "discover", "install", "reconcile", "nodereport"]
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

    # Split the kcm_cmd_list based on whether the cmd should be run as
    # one-shot job or long-running daemons.
    cmd_init_list = ["init", "discover", "install"]
    kcm_cmd_init_list = [cmd for cmd in kcm_cmd_list if cmd in cmd_init_list]
    kcm_cmd_list = [cmd for cmd in kcm_cmd_list if cmd not in cmd_init_list]

    # Run the pods based on the kcm_cmd_init_list and kcm_cmd_list with
    # provided options.
    if kcm_cmd_init_list:
        run_pods(None, kcm_cmd_init_list, kcm_img, kcm_img_pol, conf_dir,
                 install_dir, num_dp_cores, num_cp_cores, kcm_node_list,
                 pull_secret)
    if kcm_cmd_list:
        run_pods(kcm_cmd_list, None, kcm_img, kcm_img_pol, conf_dir,
                 install_dir, num_dp_cores, num_cp_cores, kcm_node_list,
                 pull_secret)


# run_pods() runs the pods based on the cmd_list and cmd_init_list
# using run_cmd_pods. It waits for the pods to go into a pod phase based
# on pod_phase_name.
# Note: Only one of cmd_list or cmd_init_list should be specified.
def run_pods(cmd_list, cmd_init_list, kcm_img, kcm_img_pol, conf_dir,
             install_dir, num_dp_cores, num_cp_cores, kcm_node_list,
             pull_secret):
    if cmd_list:
        logging.info("Creating kcm pod for {} commands ...".format(cmd_list))
    elif cmd_init_list:
        logging.info("Creating kcm pod for {} commands ..."
                     .format(cmd_init_list))

    run_cmd_pods(cmd_list, cmd_init_list, kcm_img, kcm_img_pol, conf_dir,
                 install_dir, num_dp_cores, num_cp_cores, kcm_node_list,
                 pull_secret)

    pod_name_prefix = ""
    pod_phase_name = ""
    if cmd_init_list:
        pod_name_prefix = "kcm-{}-pod-".format("-".join(cmd_init_list))
        pod_phase_name = "Succeeded"
        logging.info("Waiting for kcm pod running {} cmds to enter {} state."
                     .format(cmd_init_list, pod_phase_name))
    elif cmd_list:
        pod_name_prefix = "kcm-{}-ds-".format("-".join(cmd_list))
        pod_phase_name = "Running"
        logging.info("Waiting for kcm pod running {} cmds to enter {} state."
                     .format(cmd_list, pod_phase_name))

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
def run_cmd_pods(cmd_list, cmd_init_list, kcm_img, kcm_img_pol, conf_dir,
                 install_dir, num_dp_cores, num_cp_cores, kcm_node_list,
                 pull_secret):
    pod = k8s.get_pod_template()
    if pull_secret:
        update_pod_with_pull_secret(pod, pull_secret)
    if cmd_list:
        update_pod(pod, "Always", conf_dir, install_dir)
        for cmd in cmd_list:
            args = ""
            if cmd == "reconcile":
                args = "/kcm/kcm.py isolate --pool=infra /kcm/kcm.py -- reconcile --interval=5 --publish"  # noqa: E501
            elif cmd == "nodereport":
                args = "/kcm/kcm.py isolate --pool=infra /kcm/kcm.py -- node-report --interval=5 --publish"  # noqa: E501

            update_pod_with_container(pod, cmd, kcm_img, kcm_img_pol, args)
    elif cmd_init_list:
        update_pod(pod, "Never", conf_dir, install_dir)
        for cmd in cmd_init_list:
            args = ""
            if cmd == "init":
                args = ("/kcm/kcm.py init --num-dp-cores={} "
                        "--num-cp-cores={}").format(num_dp_cores, num_cp_cores)
                # If init is the only cmd in cmd_init_list, it should be run
                # as regular container as spec.containers is a required field.
                # Otherwise, it should be run as init-container.
                if len(cmd_init_list) == 1:
                    update_pod_with_container(pod, cmd, kcm_img,
                                              kcm_img_pol, args)
                else:
                    update_pod_with_init_container(pod, cmd, kcm_img,
                                                   kcm_img_pol, args)
            else:
                if cmd == "discover":
                    args = "/kcm/kcm.py discover"
                elif cmd == "install":
                    args = "/kcm/kcm.py install"
                update_pod_with_container(pod, cmd, kcm_img, kcm_img_pol,
                                          args)

    for node_name in kcm_node_list:
        if cmd_list:
            update_pod_with_node_details(pod, node_name, cmd_list)
            daemon_set = k8s.ds_from(pod=pod)
        elif cmd_init_list:
            update_pod_with_node_details(pod, node_name, cmd_init_list)

        try:
            if cmd_list:
                cr_pod_resp = k8s.create_ds(None, daemon_set)
                logging.debug("Response while creating ds for {} command(s): "
                              "{}".format(cmd_list, cr_pod_resp))
            elif cmd_init_list:
                cr_pod_resp = k8s.create_pod(None, pod)
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


# get_kcm_node_list() returns a list of nodes based on either host_list or
# all_hosts.
def get_kcm_node_list(host_list, all_hosts):
    kcm_node_list = []
    if host_list:
        kcm_node_list = [host.strip() for host in host_list.split(',')]
    if all_hosts:
        try:
            node_list_resp = k8s.get_compute_nodes(None)
            for node in node_list_resp:
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
def update_pod(pod, restart_pol, conf_dir, install_dir):
    pod["spec"]["restartPolicy"] = restart_pol
    pod["spec"]["volumes"][1]["hostPath"]["path"] = conf_dir
    pod["spec"]["volumes"][2]["hostPath"]["path"] = install_dir


def update_pod_with_node_details(pod, node_name, cmd_list):
    pod["spec"]["nodeName"] = node_name
    pod_name = "kcm-{}-pod-{}".format("-".join(cmd_list), node_name)
    pod["metadata"]["name"] = pod_name


def update_pod_with_pull_secret(pod, pull_secret):
    pod["spec"]["imagePullSecrets"] = [{"name": pull_secret}]


# update_pod_with_container() updates the pod template with a container using
# the provided options.
def update_pod_with_container(pod, cmd, kcm_img, kcm_img_pol, args):
    container_template = k8s.get_container_template()
    container_template["image"] = kcm_img
    container_template["imagePullPolicy"] = kcm_img_pol
    container_template["args"][0] = args
    # Each container name should be distinct within a Pod.
    container_template["name"] = cmd
    pod["spec"]["containers"].append(container_template)


# update_pod_with_init_container() updates the pod template with a init
# container using the provided options.
def update_pod_with_init_container(pod, cmd, kcm_img, kcm_img_pol, args):
    container_template = k8s.get_container_template()
    container_template["image"] = kcm_img
    container_template["imagePullPolicy"] = kcm_img_pol
    container_template["args"][0] = args
    # Each container name should be distinct within a Pod.
    container_template["name"] = cmd
    # Note(balajismaniam): Downward API for spec.nodeName doesn't seem to
    # work with init-containers. Removing it as a work-around. Needs further
    # investigation.
    container_template["env"].pop()

    pod_init_containers_list = []
    init_containers_key = "pod.beta.kubernetes.io/init-containers"

    if init_containers_key in pod["metadata"]["annotations"]:
        init_containers = \
            pod["metadata"]["annotations"][init_containers_key]
        pod_init_containers_list = json.loads(init_containers)

    pod_init_containers_list.append(container_template)
    pod["metadata"]["annotations"][init_containers_key] = \
        json.dumps(pod_init_containers_list)
