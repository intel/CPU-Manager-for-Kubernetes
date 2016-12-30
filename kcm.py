#!/usr/bin/env python


"""kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm (describe | reconcile) [--conf-dir=<dir>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]
  kcm install --install-dir=<dir>

Options:
  -h --help             Show this screen.
  --version             Show version.
  --conf-dir=<dir>      KCM configuration directory [default: /etc/kcm].
  --install-dir=<dir>   KCM install directory.
  --num-dp-cores=<num>  Number of data plane cores [default: 4].
  --num-cp-cores=<num>  Number of control plane cores [default: 1].
  --pool=<pool>         Pool name: either infra, controlplane or dataplane.
"""
from intel import config, util
from docopt import docopt
import json
import os
import random
import subprocess
import logging
import psutil


def main():
    logging.basicConfig(level=logging.INFO)
    args = docopt(__doc__, version="KCM 0.1.0")
    if args["init"]:
        init(args["--conf-dir"],
             args["--num-dp-cores"],
             args["--num-cp-cores"])
        return
    if args["describe"]:
        describe(args["--conf-dir"])
        return
    if args["isolate"]:
        isolate(args["--conf-dir"], args["--pool"],
                args["<command>"], args["<args>"])
        return
    if args["reconcile"]:
        reconcile(args["--conf-dir"])
        return
    if args["install"]:
        install(args["--install-dir"])
        return


def init(conf_dir, num_dp_cores, num_cp_cores):
    util.check_hugepages()
    cpumap = util.discover_topo()
    logging.info("Writing config to {}.".format(conf_dir))
    logging.info("Requested data plane cores = {}.".format(num_dp_cores))
    logging.info("Requested control plane cores = {}.".format(num_cp_cores))
    c = config.new(conf_dir)
    with c.lock():
        logging.info("Adding dataplane pool.")
        dp = c.add_pool("dataplane", True)
        for i in range(int(num_dp_cores)):
            if not cpumap:
                raise KeyError("No more cpus left to assign for data plane")
            k, v = cpumap.popitem()
            logging.info("Adding {} cpus to the dataplane pool.".format(v))
            dp.add_cpu_list(v)
        logging.info("Adding controlplane pool.")
        cp = c.add_pool("controlplane", False)
        cpus = ""
        for i in range(int(num_cp_cores)):
            if not cpumap:
                raise KeyError("No more cpus left to assign for control plane")
            k, v = cpumap.popitem()
            if cpus:
                cpus = cpus + "," + v
            else:
                cpus = v
        logging.info("Adding {} cpus to the controlplane pool.".format(cpus))
        cp.add_cpu_list(cpus)
        logging.info("Adding infra pool.")
        infra = c.add_pool("infra", False)
        cpus = ""
        if not cpumap:
            raise KeyError("No more cpus left to assign for infra")
        for k, v in cpumap.items():
            if cpus:
                cpus = cpus + "," + v
            else:
                cpus = v
        logging.info("Adding {} cpus to the infra pool.".format(cpus))
        infra.add_cpu_list(cpus)


def describe(conf_dir):
    c = config.Config(conf_dir)
    with c.lock():
        print(json.dumps(c.as_dict(), sort_keys=True, indent=2))


def isolate(conf_dir, pool_name, command, args):
    # TODO: handle signals properly, e.g. to release exclusive cpu lists.
    # It's common for container managers to send SIG_TERM shortly before
    # sending SIG_KILL.
    c = config.Config(conf_dir)
    with c.lock():
        pools = c.pools()
        if pool_name not in pools:
            raise KeyError("Requested pool {} does not exist"
                           .format(pool_name))
        pool = pools[pool_name]
        if pool.exclusive():
            for cl in pool.cpu_lists().values():
                if len(cl.tasks()) == 0:
                    clist = cl
                    break
        else:
            # NOTE(CD): This allocation algorithm is probably an
            # oversimplification, however for known use cases the non-exclusive
            # pools should never have more than one cpu list anyhow.
            # If that ceases to hold in the future, we could explore population
            # or load-based spreading. Keeping it simple for now.
            clist = random.choice(list(pool.cpu_lists().values()))
        if not clist:
            raise SystemError("No free cpu lists in pool {}".format(pool_name))
        clist.add_task(os.getpid())
    # NOTE: we spawn the child process after exiting the config lock context.
    try:
        subprocess.check_call("numactl --physcpubind={} -- {} {}".format(
            clist.cpus(), command, " ".join(args)),
            shell=True)
    finally:
        with c.lock():
            clist.remove_task(os.getpid())


def reconcile(conf_dir):
    # TODO: Run reconcile periodically in the background.
    c = config.Config(conf_dir)
    with c.lock():
        for pool_name, pool in c.pools().items():
            for cl in pool.cpu_lists().values():
                for task in cl.tasks():
                    if not psutil.pid_exists(task):
                        cl.remove_task(task)


def install(install_dir):
    kcm_path = os.path.realpath(__file__)
    # Using pyinstaller: http://www.pyinstaller.org
    # to produce an x86-64 ELF executable named `kcm` in the
    # supplied installation directory.
    subprocess.check_call(
        "pyinstaller --onefile --distpath={} {}".format(
            install_dir,
            kcm_path),
        shell=True)
    logging.info("Installed kcm to {}".format(install_dir))


if __name__ == "__main__":
    main()
