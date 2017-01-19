#!/usr/bin/env python


"""kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm cluster-init (--host-list=<list>|--all-hosts) [--kcm-cmd-list=<list>]
                   [--kcm-img=<img>] [--kcm-img-pol=<pol>] [--conf-dir=<dir>]
                   [--install-dir=<dir>] [--num-dp-cores=<num>]
                   [--num-cp-cores=<num>]
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm discover [--conf-dir=<dir>]
  kcm describe [--conf-dir=<dir>]
  kcm reconcile [--conf-dir=<dir>] [--publish] [--interval=<seconds>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]
  kcm install [--install-dir=<dir>]
  kcm node-report [--conf-dir=<dir>] [--publish] [--interval=<seconds>]

Options:
  -h --help             Show this screen.
  --version             Show version.
  --host-list=<list>    Comma seperated list of Kubernetes nodes to prepare
                        for KCM software.
  --all-hosts           Prepare all Kubernetes nodes for the KCM software.
  --kcm-cmd-list=<list> Comma seperated list of KCM sub-commands to run on
                        each host
                        [default: init,reconcile,install,discover,nodereport].
  --kcm-img=<img>       KCM Docker image [default: kcm].
  --kcm-img-pol=<pol>   Image pull policy for the KCM Docker image
                        [default: Never].
  --conf-dir=<dir>      KCM configuration directory [default: /etc/kcm].
  --install-dir=<dir>   KCM install directory [default: /opt/bin].
  --interval=<seconds>  Number of seconds to wait between rerunning.
                        If set to 0, will only run once. [default: 0]
  --num-dp-cores=<num>  Number of data plane cores [default: 4].
  --num-cp-cores=<num>  Number of control plane cores [default: 1].
  --pool=<pool>         Pool name: either infra, controlplane or dataplane.
  --publish             Whether to publish reports to the Kubernetes
                        API server.
"""
from intel import (
    clusterinit, describe, discover, init, install,
    isolate, nodereport, reconcile)
from docopt import docopt
import logging
import os


def main():
    setup_logging()

    args = docopt(__doc__, version="KCM v0.1.0")
    if args["cluster-init"]:
        clusterinit.cluster_init(args["--host-list"], args["--all-hosts"],
                                 args["--kcm-cmd-list"], args["--kcm-img"],
                                 args["--kcm-img-pol"], args["--conf-dir"],
                                 args["--install-dir"], args["--num-dp-cores"],
                                 args["--num-cp-cores"])
        return
    if args["init"]:
        init.init(args["--conf-dir"],
                  args["--num-dp-cores"],
                  args["--num-cp-cores"])
        return
    if args["discover"]:
        discover.discover(args["--conf-dir"])
        return
    if args["describe"]:
        describe.describe(args["--conf-dir"])
        return
    if args["isolate"]:
        isolate.isolate(args["--conf-dir"], args["--pool"],
                        args["<command>"], args["<args>"])
        return
    if args["reconcile"]:
        reconcile.reconcile(args["--conf-dir"],
                            args["--interval"],
                            args["--publish"])
        return
    if args["install"]:
        install.install(args["--install-dir"])
        return
    if args["node-report"]:
        nodereport.nodereport(args["--conf-dir"],
                              args["--interval"],
                              args["--publish"])
        return


def setup_logging():
    level = os.getenv("KCM_LOG_LEVEL", logging.INFO)
    logging.basicConfig(level=level)


if __name__ == "__main__":
    main()
