#!/usr/bin/env python
# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm cluster-init (--host-list=<list>|--all-hosts) [--kcm-cmd-list=<list>]
                   [--kcm-img=<img>] [--kcm-img-pol=<pol>] [--conf-dir=<dir>]
                   [--install-dir=<dir>] [--num-dp-cores=<num>]
                   [--num-cp-cores=<num>] [--pull-secret=<name>]
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm discover [--conf-dir=<dir>]
  kcm describe [--conf-dir=<dir>]
  kcm reconcile [--conf-dir=<dir>] [--publish] [--interval=<seconds>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]
              [--no-affinity]
  kcm install [--install-dir=<dir>]
  kcm node-report [--conf-dir=<dir>] [--publish] [--interval=<seconds>]
  kcm uninstall [--install-dir=<dir>] [--conf-dir=<dir>]

Options:
  -h --help             Show this screen.
  --version             Show version.
  --host-list=<list>    Comma seperated list of Kubernetes nodes to prepare
                        for KCM software.
  --all-hosts           Prepare all Kubernetes nodes for the KCM software.
  --kcm-cmd-list=<list> Comma seperated list of KCM sub-commands to run on
                        each host
                        [default: init,reconcile,install,discover,nodereport].
  --kcm-img=<img>       KCM Docker image [default: kcm:v0.5.0].
  --kcm-img-pol=<pol>   Image pull policy for the KCM Docker image
                        [default: IfNotPresent].
  --conf-dir=<dir>      KCM configuration directory [default: /etc/kcm].
  --install-dir=<dir>   KCM install directory [default: /opt/bin].
  --interval=<seconds>  Number of seconds to wait between rerunning.
                        If set to 0, will only run once. [default: 0]
  --num-dp-cores=<num>  Number of data plane cores [default: 4].
  --num-cp-cores=<num>  Number of control plane cores [default: 1].
  --pool=<pool>         Pool name: either infra, controlplane or dataplane.
  --publish             Whether to publish reports to the Kubernetes
                        API server.
  --pull-secret=<name>  Name of secret used for pulling Docker images from
                        restricted Docker registry.
  --no-affinity         Do not set cpu affinity before forking the child
                        command. In this mode the user program is responsible
                        for reading the `KCM_CPUS_ASSIGNED` environment
                        variable and moving a subset of its own processes
                        and/or tasks to the assigned CPUs.
"""
from intel import (
    clusterinit, describe, discover, init, install,
    isolate, nodereport, reconcile, uninstall)
from docopt import docopt
import logging
import os
import sys


def main():
    setup_logging()

    args = docopt(__doc__, version="KCM v0.5.0")
    if args["cluster-init"]:
        clusterinit.cluster_init(args["--host-list"], args["--all-hosts"],
                                 args["--kcm-cmd-list"], args["--kcm-img"],
                                 args["--kcm-img-pol"], args["--conf-dir"],
                                 args["--install-dir"], args["--num-dp-cores"],
                                 args["--num-cp-cores"], args["--pull-secret"])
        return
    if args["init"]:
        init.init(args["--conf-dir"],
                  int(args["--num-dp-cores"]),
                  int(args["--num-cp-cores"]))
        return
    if args["discover"]:
        discover.discover(args["--conf-dir"])
        return
    if args["describe"]:
        describe.describe(args["--conf-dir"])
        return
    if args["isolate"]:
        isolate.isolate(args["--conf-dir"],
                        args["--pool"],
                        args["--no-affinity"],
                        args["<command>"],
                        args["<args>"])
        return
    if args["reconcile"]:
        reconcile.reconcile(args["--conf-dir"],
                            int(args["--interval"]),
                            args["--publish"])
        return
    if args["install"]:
        install.install(args["--install-dir"])
        return
    if args["uninstall"]:
        uninstall.uninstall(args["--install-dir"],
                            args["--conf-dir"])
        return
    if args["node-report"]:
        nodereport.nodereport(args["--conf-dir"],
                              int(args["--interval"]),
                              args["--publish"])
        return


def setup_logging():
    level = os.getenv("KCM_LOG_LEVEL", logging.INFO)
    logging.basicConfig(level=level)


if __name__ == "__main__":
    try:
        main()

    except RuntimeError as e:
        logging.error(e)
        sys.exit(1)
