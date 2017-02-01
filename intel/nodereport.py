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

from . import config, proc, third_party
import itertools
import json
from kubernetes import config as k8sconfig, client as k8sclient
import logging
import os
import time


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

            node_report_type = third_party.ThirdPartyResourceType(
                v1beta,
                "kcm.intel.com",
                "Nodereport")

            # third_party throws an exception if the environment variable
            # is not set.
            node_report = node_report_type.create(os.getenv("NODE_NAME"))
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
    check_kcm_config(report, conf_dir)
    # TODO: check_procfs(report)
    return report


def check_describe(report, conf_dir):
    try:
        report.add_description(config.Config(conf_dir).as_dict())
    except Exception:
        pass


def check_kcm_config(report, conf_dir):
    check_conf = report.add_check("configDirectory")

    # Verify we can read the config directory
    try:
        c = config.Config(conf_dir)
    except Exception:
        check_conf.add_error("Unable to read the KCM configuration directory")
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

    def add_description(self, description):
        self.description = description

    def add_check(self, name):
        check = Check(name)
        self.checks.append(check)
        return check

    def as_dict(self):
        return {
            "description": self.description,
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
