#!/usr/bin/env python
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


"""cmk.

Usage:
  cmk (-h | --help)
  cmk --version
  cmk cluster-init (--host-list=<list>|--all-hosts) [--cmk-cmd-list=<list>]
                   [--cmk-img=<img>] [--cmk-img-pol=<pol>] [--conf-dir=<dir>]
                   [--install-dir=<dir>] [--num-exclusive-cores=<num>]
                   [--num-shared-cores=<num>] [--pull-secret=<name>]
                   [--saname=<name>] [--shared-mode=<mode>]
                   [--exclusive-mode=<mode>] [--namespace=<name>]
                   [--excl-non-isolcpus=<list>]
  cmk init [--conf-dir=<dir>] [--num-exclusive-cores=<num>]
           [--num-shared-cores=<num>] [--socket-id=<num>]
           [--shared-mode=<mode>] [--exclusive-mode=<mode>]
           [--excl-non-isolcpus=<list>]
  cmk discover [--conf-dir=<dir>]
  cmk describe [--conf-dir=<dir>]
  cmk reconcile [--conf-dir=<dir>] [--publish] [--interval=<seconds>]
  cmk isolate [--conf-dir=<dir>] [--socket-id=<num>] --pool=<pool> <command>
              [-- <args> ...][--no-affinity]
  cmk install [--install-dir=<dir>]
  cmk node-report [--conf-dir=<dir>] [--publish] [--interval=<seconds>]
  cmk uninstall [--install-dir=<dir>] [--conf-dir=<dir>] [--namespace=<name>]
  cmk webhook [--conf-file=<file>]

Options:
  -h --help                    Show this screen.
  --version                    Show version.
  --host-list=<list>           Comma seperated list of Kubernetes nodes to
                               prepare for CMK software.
  --all-hosts                  Prepare all Kubernetes nodes for the CMK
                               software.
  --cmk-cmd-list=<list>        Comma seperated list of CMK sub-commands to run
                               on each host
                               [default: init,reconcile,install,discover,nodereport].
  --cmk-img=<img>              CMK Docker image [default: cmk:v1.4.1].
  --cmk-img-pol=<pol>          Image pull policy for the CMK Docker image
                               [default: IfNotPresent].
  --conf-dir=<dir>             CMK configuration directory [default: /etc/cmk].
  --install-dir=<dir>          CMK install directory [default: /opt/bin].
  --interval=<seconds>         Number of seconds to wait between rerunning.
                               If set to 0, will only run once. [default: 0]
  --num-exclusive-cores=<num>  Number of cores in exclusive pool. [default: 4].
  --num-shared-cores=<num>     Number of cores in shared pool. [default: 1].
  --pool=<pool>                Pool name: either infra, shared or exclusive.
  --shared-mode=<mode>         Shared pool core allocation mode. Possible
                               modes: packed and spread [default: packed].
  --exclusive-mode=<mode>      Exclusive pool core allocation mode. Possible
                               modes: packed and spread [default: packed].
  --publish                    Whether to publish reports to the Kubernetes
                               API server.
  --pull-secret=<name>         Name of secret used for pulling Docker images
                               from restricted Docker registry.
  --saname=<name>              ServiceAccount name to pass
                               [default: cmk-serviceaccount].
  --socket-id=<num>            ID of socket where allocated core should come
                               from. If it's set to -1 then child command will
                               be assigned to any socket [default: -1].
  --no-affinity                Do not set cpu affinity before forking the child
                               command. In this mode the user program is
                               responsible for reading the `CMK_CPUS_ASSIGNED`
                               environment variable and moving a subset of its
                               own processes and/or tasks to the assigned CPUs.
  --namespace=<name>           Set the namespace to deploy pods to during the
                               cluster-init deployment process.
                               [default: default].
  --excl-non-isolcpus=<list>   List of physical cores to be added to the extra
                               exclusive pool, not governed by isolcpus. Both
                               hyperthreads of the core will be added to the pool
                               [default: -1]
"""  # noqa: E501
from intel import (
    clusterinit, describe, discover, init, install,
    isolate, nodereport, reconcile, uninstall, webhook)
from docopt import docopt
import logging
import os
import sys


def main():
    setup_logging()

    args = docopt(__doc__, version="CMK v1.4.1")
    if args["cluster-init"]:
        clusterinit.cluster_init(args["--host-list"], args["--all-hosts"],
                                 args["--cmk-cmd-list"], args["--cmk-img"],
                                 args["--cmk-img-pol"], args["--conf-dir"],
                                 args["--install-dir"],
                                 args["--num-exclusive-cores"],
                                 args["--num-shared-cores"],
                                 args["--pull-secret"],
                                 args["--saname"], args["--exclusive-mode"],
                                 args["--shared-mode"], args["--namespace"],
                                 args["--excl-non-isolcpus"])
        return
    if args["init"]:
        init.init(args["--conf-dir"],
                  int(args["--num-exclusive-cores"]),
                  int(args["--num-shared-cores"]),
                  args["--exclusive-mode"],
                  args["--shared-mode"],
                  args["--excl-non-isolcpus"])
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
                        args["<args>"],
                        args["--socket-id"])
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
                            args["--conf-dir"],
                            args["--namespace"])
        return
    if args["node-report"]:
        nodereport.nodereport(args["--conf-dir"],
                              int(args["--interval"]),
                              args["--publish"])
        return
    if args["webhook"]:
        webhook.webhook(args["--conf-file"])


def setup_logging():
    level = os.getenv("CMK_LOG_LEVEL", logging.INFO)
    logging.basicConfig(level=level)


if __name__ == "__main__":
    try:
        main()

    except RuntimeError as e:
        logging.error(e)
        sys.exit(1)
