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
                "cmk.intel.com",
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
        cl = pool.cpu_list(None, r.cpus())
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
    return report


class ReconcileReport(dict):
    def __init__(self):
        self["reclaimedCpuLists"] = []

    def reclaimed_cpu_lists(self):
        return self["reclaimedCpuLists"]

    def add_reclaimed_cpu_list(self, pid, pool_name, cpus):
        self["reclaimedCpuLists"].append(Reclaimed(pid, pool_name, cpus))

    def json(self):
        def by_pid(item): return item.pid()
        self.reclaimed_cpu_lists().sort(key=by_pid)
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
