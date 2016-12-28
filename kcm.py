#!/usr/bin/env python


"""kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm (init | describe | reconcile) [--conf-dir=<dir>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]

Options:
  -h --help         Show this screen.
  --version         Show version.
  --conf-dir=<dir>  KCM configuration directory [default: /etc/kcm].
  --pool=<pool>     Pool name: either infra, controlplane or dataplane.
"""
from intel import config, util
from docopt import docopt
import json
import os
import random
import subprocess


def main():
    args = docopt(__doc__, version="KCM 0.1.0")
    if args["init"]:
        init(args["--conf-dir"])
        return
    if args["describe"]:
        describe(args["--conf-dir"])
        return
    if args["isolate"]:
        isolate(args["--conf-dir"], args["--pool"],
                args["<command>"], args["<args>"])
        return


def init(conf_dir):
    util.check_hugepages()


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


if __name__ == "__main__":
    main()
