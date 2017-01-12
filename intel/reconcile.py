from . import config, proc
import json
import logging
import sys
import time


def reconcile(conf_dir, seconds):
    conf = config.Config(conf_dir)

    should_exit = (seconds <= 0)

    while not should_exit:
        with conf.lock():
            report = generate_report(conf)
            print(report.json())
            reclaim_cpu_lists(conf, report)
            if len(report.mismatched_cpu_masks()) > 0:
                logging.error("Exiting due to cpuset mismatch")
                sys.exit(1)

        if seconds > 0:
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
