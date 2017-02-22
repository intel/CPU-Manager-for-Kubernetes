# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the “Software”), without modification,
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
# make, have made, use, import, offer to sell and sell (“Utilize”) this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  “Third Party Programs” are the files
# listed in the “third-party-programs.txt” text file that is included with the
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
# corrections, enhancements or other input (“Feedback”) related to the Software
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

import ast
import json
import logging
import os
import shutil
import sys
from time import sleep
from kubernetes import config as k8sconfig, client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException
from . import config, third_party
from . import reconcile
from . import discover


def uninstall(install_dir, conf_dir):
    delete_reconcile_nodereport_pod()
    remove_report("Nodereport")
    remove_report("Reconcilereport")

    check_remove_conf_dir(conf_dir)

    remove_node_label()
    remove_node_taint()
    remove_node_kcm_oir()

    remove_binary(install_dir)


def remove_binary(install_dir):
    remove_file = os.path.join(install_dir, "kcm")
    try:
        os.remove(remove_file)
        logging.info("kcm binary from \"{}\" removed successfully".format(
            install_dir))
    except OSError as err:
        logging.error("Aborting uninstall: Could not remove kcm "
                      "from \"{}\": {}".format(install_dir, err))
        sys.exit(1)


def remove_report(report_type):
    logging.info(
        "Removing \"{}\" from Kubernetes API server for node \"{}\"".format(
            report_type, os.getenv("NODE_NAME")))
    k8sconfig.load_incluster_config()
    v1beta = k8sclient.ExtensionsV1beta1Api()
    node_report_type = third_party.ThirdPartyResourceType(
        v1beta,
        "kcm.intel.com",
        report_type)
    node_report = node_report_type.create(os.getenv("NODE_NAME"))

    try:
        node_report.remove()
    except K8sApiException as err:
        if json.loads(err.body)["reason"] != "NotFound":
            logging.error(
                "Aborting uninstall: Exception when removing third"
                " party resource \"{}\": {}".format(report_type, err))
            sys.exit(1)

        logging.debug("\"{}\" for node \"{}\" does not exist".format(
            report_type, os.getenv("NODE_NAME")))
    logging.info("\"{}\" for node \"{}\" removed.".format(
        report_type, os.getenv("NODE_NAME")))


def delete_reconcile_nodereport_pod():
    k8sconfig.load_incluster_config()
    v1api = k8sclient.CoreV1Api()
    pod_name = "kcm-reconcile-nodereport-pod-{}".format(os.getenv("NODE_NAME"))
    logging.info("Removing \"{}\" pod".format(pod_name))

    try:
        v1api.delete_namespaced_pod(
            name=pod_name,
            namespace="default",
            body=k8sclient.V1DeleteOptions(),
            grace_period_seconds=0)
    except K8sApiException as err:
        if json.loads(err.body)["reason"] != "NotFound":
            logging.error(
                "Aborting uninstall: Exception when removing pod \"{}\": "
                "{}".format(pod_name, err))
            sys.exit(1)

        logging.debug("\"{}\" pod does not exist".format(pod_name))
    logging.info("\"{}\" pod deleted".format(pod_name))


def check_remove_conf_dir(conf_dir):
    # Verify we can read the config directory
    logging.info("Removing \"{}\"".format(conf_dir))
    try:
        conf = config.Config(conf_dir)
    except Exception as err:
        logging.error(
            "Aborting uninstall: Unable to read the KCM configuration "
            "directory at \"{}\": {}".format(conf_dir, err))
        sys.exit(1)

    try:
        retries = 5
        # Check if there are no "kmc isolate" processes running before removing
        # configuration directory, timeout is 5 seconds
        while retries:
            # Reconcile first before check
            pending_pools = ["controlplane", "dataplane", "infra"]
            sleep(1)
            logging.info("Running reconcile before removing config "
                         "dir, attempts left: {}".format(retries))
            with conf.lock():
                reconcile.reclaim_cpu_lists(
                    conf, reconcile.generate_report(conf))
                for pool_name in pending_pools[:]:
                    if len(get_pool_tasks(conf, pool_name)) == 0:
                        pending_pools.remove(pool_name)
                        continue
                    logging.warn("\"{}\" pool still has running tasks".format(
                        pool_name))
                    retries -= 1
                    break

                # Remove kcm pools if pending_pools is empty
                if len(pending_pools) == 0:
                    shutil.rmtree(os.path.join(conf_dir, "pools"))

            if len(pending_pools) == 0:
                # Remove kcm lock file with rest of dir after "with" scope
                # that has lock
                os.remove(os.path.join(conf_dir, "lock"))
                logging.info(
                    "\"{}\" removed".format(os.path.join(conf_dir, "lock")))
                break
            elif not retries:
                # If no retries left, it's a fail
                raise RuntimeError("There are running "
                                   "tasks, check pools in "
                                   "\"{}\"".format(conf_dir))
    except Exception as err:
        logging.error("Aborting uninstall: Exception when removing "
                      "\"{}\": {}".format(conf_dir, err))
        sys.exit(1)


def get_pool_tasks(c, pool_name):
    if pool_name not in c.pools():
        raise KeyError("\"{}\" pool does not exist".format(pool_name))
    if len(c.pool(pool_name).cpu_lists()) == 0:
        raise KeyError("No CPU list in \"{}\" pool".format(pool_name))
    return c.pool(pool_name).tasks_list()


def remove_node_label():
    logging.info("Removing node label")
    patch_path = '/metadata/labels/kcm.intel.com~1kcm-node'
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
        logging.warning("Label \"{}\" does not exist".format(patch_path))
    logging.info("Removed node label \"{}\"".format(patch_path))


def remove_node_taint():
    logging.info("Removing node taint")
    node_name = os.getenv("NODE_NAME")

    try:
        node_resp = discover.get_k8s_node(node_name)
    except K8sApiException as err:
        logging.error("Aborting uninstall: Exception when getting the node "
                      "\"{}\" obj: {}".format(node_name, err))
        sys.exit(1)

    node_taints_list = []
    node_taint_key = "scheduler.alpha.kubernetes.io/taints"
    if node_taint_key in node_resp["metadata"]["annotations"]:
        node_taints = node_resp["metadata"]["annotations"][node_taint_key]
        node_taints_list = ast.literal_eval(node_taints)
        node_taints_list = \
            [taint for taint in node_taints_list if taint["key"] != "kcm"]

    patch_path = '/metadata/annotations/scheduler.alpha.kubernetes.io~1taints'
    patch_body = [{
        "op": "replace",
        "path": patch_path,
        "value": json.dumps(node_taints_list)
    }]

    try:
        discover.patch_k8s_node(patch_body)
    except K8sApiException as err:
        logging.error(
            "Aborting uninstall: Exception when removing taint \"{}\": "
            "{}".format(patch_path, err))
        sys.exit(1)
    logging.info("Removed node taint with key\"{}\"".format("kcm"))


def remove_node_kcm_oir():
    patch_path = ('/status/capacity/pod.alpha.kubernetes.io~1opaque-int-'
                  'resource-kcm')
    logging.info("Removing node oir \"{}\"".format(patch_path))
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
        logging.warning("KCM oir \"{}\" does not exist".format(patch_path))
    logging.info("Removed node oir \"{}\"".format(patch_path))
