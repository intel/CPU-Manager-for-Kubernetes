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

import ast
import json
import logging
import os
import shutil
import sys

from time import sleep
from kubernetes.client.rest import ApiException as K8sApiException
from . import custom_resource
from . import config, third_party
from . import reconcile
from . import discover
from . import k8s


def uninstall(install_dir, conf_dir, namespace):
    delete_cmk_pod("cmk-init-install-discover-pod", namespace,
                   postfix=os.getenv("NODE_NAME"))
    delete_cmk_pod("cmk-reconcile-nodereport-ds", namespace,
                   postfix=os.getenv("NODE_NAME"))

    delete_cmk_pod("cmk-node-report-ds-all", namespace)
    delete_cmk_pod("cmk-reconcile-ds-all", namespace)

    delete_cmk_pod("cmk-cluster-init-pod", namespace)
    delete_cmk_pod("cmk-discover-pod", namespace)
    delete_cmk_pod("cmk-init-pod", namespace)
    delete_cmk_pod("cmk-install-pod", namespace)

    remove_all_report()
    remove_node_taint()
    remove_resource_tracking()

    check_remove_conf_dir(conf_dir)
    remove_binary(install_dir)

    remove_node_label()


def remove_binary(install_dir):
    remove_file = os.path.join(install_dir, "cmk")
    try:
        os.remove(remove_file)
        logging.info("cmk binary from \"{}\" removed successfully.".format(
            install_dir))
    except FileNotFoundError as err:
        logging.warning("Could not found cmk binary in "
                        "\"{}\".".format(install_dir))
        logging.warning("Wrong path or file has already been removed.")


def remove_all_report():
    version = k8s.get_kubelet_version(None)

    if version >= "v1.7.0":
        remove_report_crd("cmk-nodereport", ["cmk-nr"])
        remove_report_crd("cmk-reconcilereport", ["cmk-rr"])

    else:
        remove_report_tpr("Nodereport")
        remove_report_tpr("Reconcilereport")


def remove_report_crd(report_type, short_names):
    logging.info(
        "Removing \"{}\" from Kubernetes API server for node \"{}\".".format(
            report_type, os.getenv("NODE_NAME")))
    node_report_type = custom_resource.CustomResourceDefinitionType(
        k8s.extensions_client_from_config(None),
        "intel.com",
        report_type,
        short_names
    )
    node_report = node_report_type.create(os.getenv("NODE_NAME"))

    try:
        node_report.remove()
    except K8sApiException as err:
        if json.loads(err.body)["reason"] != "NotFound":
            logging.error(
                "Aborting uninstall: Exception when removing custom"
                " resource definition \"{}\": {}".format(report_type, err))
            sys.exit(1)

        logging.warning("\"{}\" for node \"{}\" does not exist.".format(
            report_type, os.getenv("NODE_NAME")))

    logging.info("\"{}\" for node \"{}\" removed.".format(
        report_type, os.getenv("NODE_NAME")))


def remove_report_tpr(report_type):
    logging.info(
        "Removing \"{}\" from Kubernetes API server for node \"{}\".".format(
            report_type, os.getenv("NODE_NAME")))
    node_report_type = third_party.ThirdPartyResourceType(
        k8s.extensions_client_from_config(None),
        "cmk.intel.com",
        report_type
    )
    node_report = node_report_type.create(os.getenv("NODE_NAME"))

    try:
        node_report.remove()
    except K8sApiException as err:
        if json.loads(err.body)["reason"] != "NotFound":
            logging.error(
                "Aborting uninstall: Exception when removing third"
                " party resource \"{}\": {}".format(report_type, err))
            sys.exit(1)

        logging.warning("\"{}\" for node \"{}\" does not exist.".format(
            report_type, os.getenv("NODE_NAME")))
    logging.info("\"{}\" for node \"{}\" removed.".format(
        report_type, os.getenv("NODE_NAME")))


def delete_cmk_pod(pod_base_name, namespace, postfix=None,):
    if postfix:
        pod_name = "{}-{}".format(pod_base_name, postfix)
    else:
        pod_name = pod_base_name

    logging.info("Removing \"{}\"".format(pod_name))

    try:
        if "-ds-" in pod_name:
            # Pod is part of DaemonSet - remove ds otherwise ds
            # controller will restart pod
            logging.info("\"{}\" is DaemonSet".format(pod_name))
            k8s.delete_ds(None, pod_name, namespace)
        else:
            k8s.delete_pod(None, pod_name, namespace)
    except K8sApiException as err:
        if json.loads(err.body)["reason"] != "NotFound":
            logging.error(
                "Aborting uninstall: Exception when removing pod \"{}\": "
                "{}".format(pod_name, err))
            sys.exit(1)

        logging.warning("\"{}\" does not exist".format(pod_name))
    logging.info("\"{}\" deleted".format(pod_name))


def check_remove_conf_dir(conf_dir):
    # Verify we can read the config directory
    logging.info("Removing \"{}\".".format(conf_dir))
    try:
        conf = config.Config(conf_dir)
    except Exception as err:
        logging.error(
            "Aborting uninstall: Unable to read the CMK configuration "
            "directory at \"{}\": {}.".format(conf_dir, err))
        sys.exit(1)

    try:
        retries = 10
        # Check if there are no "kmc isolate" processes running before removing
        # configuration directory, timeout is 5 seconds
        while retries:
            # Reconcile first before check
            pending_pools = ["controlplane", "dataplane", "infra"]
            sleep(1)
            logging.info("Running reconcile before removing config "
                         "dir, attempts left: {}.".format(retries))
            with conf.lock():
                reconcile.reclaim_cpu_lists(
                    conf, reconcile.generate_report(conf))
                for pool_name in pending_pools[:]:
                    if len(get_pool_tasks(conf, pool_name)) == 0:
                        pending_pools.remove(pool_name)
                        continue
                    logging.warn("\"{}\" pool still has running tasks.".format(
                        pool_name))
                    retries -= 1
                    break

                # Remove cmk pools if pending_pools is empty
                if len(pending_pools) == 0:
                    shutil.rmtree(os.path.join(conf_dir, "pools"))

            if len(pending_pools) == 0:
                # Remove cmk lock file with rest of dir after "with" scope
                # that has lock
                os.remove(os.path.join(conf_dir, "lock"))
                logging.info(
                    "\"{}\" removed".format(os.path.join(conf_dir, "lock")))
                break
            elif not retries:
                # If no retries left, it's a fail
                raise RuntimeError("There are running "
                                   "tasks, check pools in "
                                   "\"{}\".".format(conf_dir))
    except (KeyError, FileNotFoundError) as err:
        logging.warning("Could not remove \"{}\", got exception {}"
                        .format(conf_dir, err))
        logging.warning("Wrong path or \"{}\" has already been removed."
                        .format(conf_dir))
    except Exception as err:
        logging.error("Aborting uninstall: Exception when removing "
                      "\"{}\": {}".format(conf_dir, err))
        sys.exit(1)


def get_pool_tasks(c, pool_name):
    if pool_name not in c.pools():
        raise KeyError("\"{}\" pool does not exist.".format(pool_name))
    if len(c.pool(pool_name).cpu_lists()) == 0:
        raise KeyError("No CPU list in \"{}\" pool.".format(pool_name))
    return c.pool(pool_name).tasks_list()


def remove_node_label():
    logging.info("Removing node label.")
    patch_path = '/metadata/labels/cmk.intel.com~1cmk-node'
    patch_body = [{
        "op": "remove",
        "path": patch_path
    }]

    try:
        discover.patch_k8s_node(patch_body)
    except K8sApiException as err:
        if "nonexistant" not in json.loads(err.body)["message"]:
            logging.error(
                "Aborting uninstall: Exception when removing node "
                "label \"{}\": {}".format(patch_path, err))
            sys.exit(1)
        logging.warning("Label \"{}\" does not exist.".format(patch_path))
    logging.info("Removed node label \"{}\".".format(patch_path))


def remove_node_taint():
    logging.info("Removing node taint.")
    node_name = os.getenv("NODE_NAME")

    try:
        node_resp = discover.get_k8s_node(node_name)
    except K8sApiException as err:
        logging.error("Aborting uninstall: Exception when getting the node "
                      "\"{}\" obj: {}".format(node_name, err))
        sys.exit(1)

    version = k8s.get_kubelet_version(None)
    node_taints_list = []

    if version >= "v1.7.0":
        node_taints = node_resp["spec"]["taints"]
        if node_taints:
            node_taints_list = node_taints
        patch_path = '/spec/taints'
    else:
        node_taint_key = "scheduler.alpha.kubernetes.io/taints"
        if node_taint_key in node_resp["metadata"]["annotations"]:
            node_taints = node_resp["metadata"]["annotations"][node_taint_key]
            node_taints_list = ast.literal_eval(node_taints)
        patch_path = '/metadata/annotations/scheduler.alpha.kubernetes.io~1taints'  # noqa: E501

    node_taints_list = \
        [taint for taint in node_taints_list if taint["key"] != "cmk"]

    if version >= "v1.7.0":
        value = node_taints_list
    else:
        value = json.dumps(node_taints_list)

    patch_body = [{
        "op": "replace",
        "path": patch_path,
        "value": value
    }]

    try:
        discover.patch_k8s_node(patch_body)
    except K8sApiException as err:
        logging.error(
            "Aborting uninstall: Exception when removing taint \"{}\": "
            "{}".format(patch_path, err))
        sys.exit(1)
    logging.info("Removed node taint with key\"{}\".".format("cmk"))


def remove_resource_tracking():
    version = k8s.get_kubelet_version(None)
    if version == "v1.8.0":
        logging.warning("Unsupported Kubernetes version")
    elif version >= "v1.8.1":
        remove_node_cmk_er()
    else:
        remove_node_cmk_oir()


def remove_node_cmk_oir():
    patch_path = ('/status/capacity/pod.alpha.kubernetes.io~1opaque-int-'
                  'resource-cmk')
    logging.info("Removing node oir \"{}\".".format(patch_path))
    patch_body = [{
        "op": "remove",
        "path": patch_path
    }]

    try:
        discover.patch_k8s_node_status(patch_body)
    except K8sApiException as err:
        if "nonexistant" not in json.loads(err.body)["message"]:
            logging.error(
                "Aborting uninstall: Exception when removing OIR \"{}\": "
                "{}".format(patch_path, err))
            sys.exit(1)
        logging.warning("CMK oir \"{}\" does not exist.".format(patch_path))
    logging.info("Removed node oir \"{}\".".format(patch_path))


def remove_node_cmk_er():
    logging.info("Removing node ERs")
    patch_body_capacity = [{
        "op": "remove",
        "path": '/status/capacity/cmk.intel.com~1dp-cores'
    }]
    patch_body_allocatable = [{
        "op": "remove",
        "path": '/status/allocatable/cmk.intel.com~1dp-cores'
    }]

    try:
        discover.patch_k8s_node_status(patch_body_capacity)
        discover.patch_k8s_node_status(patch_body_allocatable)
    except K8sApiException as err:
        if "nonexistant" not in json.loads(err.body)["message"]:
            logging.error(
                "Aborting uninstall: Exception when removing ER: "
                "{}".format(err))
            sys.exit(1)
        logging.warning("CMK ER does not exist.")
    logging.info("Removed node ERs")
