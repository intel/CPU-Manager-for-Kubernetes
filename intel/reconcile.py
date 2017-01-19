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

from . import config, proc, third_party
from kubernetes import config as k8sconfig, client as k8sclient
import json
import logging
import os
import time


def reconcile(conf_dir, seconds, publish):
    conf = config.Config(conf_dir)
    report = None

    if seconds is None:
        seconds = 0
    else:
        seconds = int(seconds)

    should_exit = (seconds <= 0)

    while True:
        with conf.lock():
            report = generate_report(conf)
            print(report.json())
            reclaim_cpu_lists(conf, report)

        if publish and report is not None:
            logging.debug("Publishing reconcile report to "
                          "Kubernetes API server")
            k8sconfig.load_incluster_config()
            v1beta = k8sclient.ExtensionsV1beta1Api()

            reconcile_report_type = third_party.ThirdPartyResourceType(
                v1beta,
                "kcm.intel.com",
                "Reconcilereport")

            node_name = os.getenv("NODE_NAME")
            reconcile_report = reconcile_report_type.create(node_name)
            reconcile_report.body["report"] = report
            reconcile_report.save()

        if should_exit:
            break

        logging.info(
            "Waiting %d seconds until next reconciliation..." % seconds)
        time.sleep(seconds)


def reclaim_cpu_lists(conf, report):
    for r in report["reclaimedCpuLists"]:
        pool = conf.pool(r.pool())
        cl = pool.cpu_list(r.cpus())
        logging.debug("Removing pid {} from cpu list \"{}\" in pool {}".format(
            r.pid(), r.cpus(), r.pool()))
        cl.remove_task(r.pid())


def generate_report(conf):
    report = ReconcileReport()

    for pool_name, pool in conf.pools().items():
        for cl in pool.cpu_lists().values():
            for task in cl.tasks():
                p = proc.Process(task)
                if not p.exists():
                    report.add_reclaimed_cpu_list(
                        p.pid,
                        pool.name(),
                        cl.cpus())

                else:
                    expected_cpus = proc.unfold_cpu_list(cl.cpus())
                    if is_cpuset_mismatch(p, expected_cpus):
                        report.add_mismatched_cpu_mask(
                            p.pid,
                            pool.name(),
                            cl.cpus(),
                            p.cpus_allowed())
    return report


def is_cpuset_mismatch(process, desired_allowed):
    return not set_equals(process.cpus_allowed(), desired_allowed)


def set_equals(a, b):
    return set(a) == set(b)


class ReconcileReport(dict):
    def __init__(self):
        self["reclaimedCpuLists"] = []
        self["mismatchedCpuMasks"] = []

    def reclaimed_cpu_lists(self):
        return self["reclaimedCpuLists"]

    def mismatched_cpu_masks(self):
        return self["mismatchedCpuMasks"]

    def add_reclaimed_cpu_list(self, pid, pool_name, cpus):
        self["reclaimedCpuLists"].append(Reclaimed(pid, pool_name, cpus))

    def add_mismatched_cpu_mask(self, pid, pool_name, cpus, actual_cpus):
        self["mismatchedCpuMasks"].append(
            Mismatch(pid, pool_name, cpus, actual_cpus))

    def json(self):
        def by_pid(item): return item.pid()
        self.reclaimed_cpu_lists().sort(key=by_pid)
        self.mismatched_cpu_masks().sort(key=by_pid)
        return json.dumps(self, sort_keys=True, indent=2)


class Reclaimed(dict):
    def __init__(self, pid, pool_name, cpus):
        self["pid"] = pid
        self["pool"] = pool_name
        self["cpus"] = cpus

    def pid(self):
        return self["pid"]

    def pool(self):
        return self["pool"]

    def cpus(self):
        return self["cpus"]


class Mismatch(dict):
    def __init__(self, pid, pool_name, cpus, actual_cpus):
        self["pid"] = pid
        self["pool"] = pool_name
        self["cpus"] = cpus
        self["actualCpus"] = actual_cpus

    def pid(self):
        return self["pid"]

    def pool(self):
        return self["pool"]

    def cpus(self):
        return self["cpus"]

    def actual_cpus(self):
        return self["actualCpus"]
