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

import itertools
import json
import logging
import os
import time

from kubernetes import config as k8sconfig, client as k8sclient
from . import config, custom_resource, k8s, proc, third_party, topology


def nodereport(conf_dir, seconds, publish):
    if seconds is None:
        seconds = 0
    else:
        seconds = int(seconds)
    should_exit = (seconds <= 0)

    while True:
        report = generate_report(conf_dir)

        print(report.json())

        if publish and report is not None:
            logging.debug("Publishing node report to Kubernetes API server")
            k8sconfig.load_incluster_config()
            v1beta = k8sclient.ExtensionsV1beta1Api()

            version = k8s.get_kubelet_version(None)

            if version >= "v1.7.0":
                node_report_type = \
                    custom_resource.CustomResourceDefinitionType(
                        v1beta,
                        "intel.com",
                        "cmk-nodereport",
                        ["cmk-nr"]
                    )
                # custom_resource throws an exception if the environment
                # variable is not set.
                node_name = os.getenv("NODE_NAME")
                node_report = node_report_type.create(node_name)
                node_report.body["spec"]["report"] = report.as_dict()
                node_report.save()
            else:
                node_report_type = third_party.ThirdPartyResourceType(
                    v1beta,
                    "cmk.intel.com",
                    "Nodereport")
                # third_party throws an exception if the environment
                # variable is not set.
                node_name = os.getenv("NODE_NAME")
                node_report = node_report_type.create(node_name)
                node_report.body["report"] = report.as_dict()
                node_report.save()

        if should_exit:
            break

        logging.info(
                "Waiting {} seconds until next node report...".format(seconds))
        time.sleep(seconds)


def generate_report(conf_dir):
    report = NodeReport()
    check_describe(report, conf_dir)
    check_cmk_config(report, conf_dir)
    for socket in topology.discover().sockets.values():
        report.add_socket(socket)
    return report


def check_describe(report, conf_dir):
    try:
        report.add_description(config.Config(conf_dir).as_dict())
    except Exception:
        pass


def check_cmk_config(report, conf_dir):
    check_conf = report.add_check("configDirectory")

    # Verify we can read the config directory
    try:
        c = config.Config(conf_dir)
    except Exception:
        check_conf.add_error("Unable to read the CMK configuration directory")
        return  # Nothing more we can check for now

    # Ensure pool cpu lists are disjoint
    with c.lock():
        cpu_lists = [
            {
                "pool": p,
                "list": cl,
                "cpus": proc.unfold_cpu_list(cl)
            }
            for p in c.pools()
            for cl in c.pool(p).cpu_lists()
        ]

    # Subset of cartesian product without self-maplets:
    # If a -> b is in the result then b -> a is not.
    # Search the filtered product for overlapping CPU lists.
    def same_list(a, b):
        return a["pool"] is b["pool"] and a["list"] is b["list"]

    def disjoint(a, b):
        return not set(a["cpus"]).intersection(set(b["cpus"]))

    for (a, b) in itertools.combinations_with_replacement(cpu_lists, 2):
        if not same_list(a, b) and not disjoint(a, b):
            check_conf.add_error(
                    "CPU list overlap detected in "
                    "{}:{} and {}:{} (in both: {})".format(
                        a["pool"], a["list"],
                        b["pool"], b["list"],
                        b["cpus"]))


class NodeReport():
    def __init__(self):
        self.description = None
        self.checks = []
        self.sockets = {}

    def add_description(self, description):
        self.description = description

    def add_socket(self, socket):
        self.sockets[socket.socket_id] = socket.as_dict(include_pool=False)

    def add_check(self, name):
        check = Check(name)
        self.checks.append(check)
        return check

    def as_dict(self):
        return {
            "description": self.description,
            "topology": {"sockets": self.sockets},
            "checks": {c.name: c.as_dict() for c in self.checks}
        }

    def json(self):
        self.checks.sort()
        return json.dumps(self.as_dict(), sort_keys=True, indent=2)


class Check():
    def __init__(self, name):
        self.name = name
        self.ok = True
        self.errors = []

    def add_error(self, msg):
        self.ok = False
        self.errors.append(msg)

    def as_dict(self):
        return {
            "ok": self.ok,
            "errors": self.errors
        }
