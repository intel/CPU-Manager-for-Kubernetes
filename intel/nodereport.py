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
                "NodeReport")

            # third_party throws an exception if the environment variable
            # is not set.
            node_report = node_report_type.create(os.getenv("NODE_NAME"))
            node_report.body["report"] = report
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
