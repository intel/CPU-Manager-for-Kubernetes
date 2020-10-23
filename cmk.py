#!/usr/bin/env python3
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
                   [--cmk-img=<img>] [--cmk-img-pol=<pol>]
                   [--install-dir=<dir>] [--num-exclusive-cores=<num>]
                   [--num-shared-cores=<num>] [--pull-secret=<name>]
                   [--saname=<name>] [--shared-mode=<mode>]
                   [--exclusive-mode=<mode>] [--namespace=<name>]
                   [--excl-non-isolcpus=<list>] [--cafile=<file>]
                   [--insecure=<bool>] [--no-taint]
  cmk init [--num-exclusive-cores=<num>]
           [--num-shared-cores=<num>] [--socket-id=<num>]
           [--shared-mode=<mode>] [--exclusive-mode=<mode>]
           [--excl-non-isolcpus=<list>]
  cmk discover [--no-taint]
  cmk describe
  cmk reconcile [--publish] [--interval=<seconds>]
  cmk isolate [--socket-id=<num>] --pool=<pool> <command>
              [-- <args>...][--no-affinity]
  cmk install [--install-dir=<dir>]
  cmk node-report [--publish] [--interval=<seconds>]
  cmk uninstall [--install-dir=<dir>] [--conf-dir=<dir>] [--namespace=<name>]
  cmk webhook [--conf-file=<file>] [--cafile=<file>] [--insecure=<bool>]
  cmk reconfigure [--node-name=<name>] [--num-exclusive-cores=<num>]
                  [--num-shared-cores=<num>] [--excl-non-isolcpus=<list>]
                  [--exclusive-mode=<mode>]
                  [--shared-mode=<mode>] [--install-dir=<dir>]
                  [--namespace=<name>]
  cmk reconfigure_setup [--num-exclusive-cores=<num>] [--num-shared-cores=<num>]
                        [--excl-non-isolcpus=<list>]
                        [--exclusive-mode=<mode>] [--shared-mode=<mode>]
                        [--cmk-img=<img>] [--cmk-img-pol=<pol>]
                        [--install-dir=<dir>] [--saname=<name>]
                        [--namespace=<name>]
  cmk reaffinitize [--node-name=<name>] [--namespace=<name>]

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
  --cmk-img=<img>              CMK Docker image [default: cmk:v1.5.1].
  --cmk-img-pol=<pol>          Image pull policy for the CMK Docker image
                               [default: IfNotPresent].
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
  --node-name=<name>           The name of the node that is being reaffinitized
  --cafile=<file>              The location of the cafile used by the webhook to
                               authenticate the Kubernetes API server.
                               [default: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt]
  --insecure=<bool>            Determines whether the webhook service will be set up to
                               authenticate using mutual TLS or not.
                               [default: False]
  --no-taint                   Don't taint Kubernetes nodes.
"""  # noqa: E501
from intel import (
    clusterinit, describe, discover, init, install,
    isolate, nodereport, reconcile, uninstall, webhook,
    reconfigure, reconfigure_setup, reaffinitize)
from docopt import docopt
import logging
import os
import sys


def main():
    setup_logging()

    args = docopt(__doc__, version="CMK v1.5.1")
    if args["cluster-init"]:
        clusterinit.cluster_init(args["--host-list"], args["--all-hosts"],
                                 args["--cmk-cmd-list"], args["--cmk-img"],
                                 args["--cmk-img-pol"],
                                 args["--install-dir"],
                                 args["--num-exclusive-cores"],
                                 args["--num-shared-cores"],
                                 args["--pull-secret"],
                                 args["--saname"], args["--exclusive-mode"],
                                 args["--shared-mode"], args["--namespace"],
                                 args["--excl-non-isolcpus"],
                                 args["--cafile"], args["--insecure"],
                                 args["--no-taint"])
        return
    if args["init"]:
        init.init(int(args["--num-exclusive-cores"]),
                  int(args["--num-shared-cores"]),
                  args["--exclusive-mode"],
                  args["--shared-mode"],
                  args["--excl-non-isolcpus"])
        return
    if args["discover"]:
        discover.discover(args["--no-taint"])
        return
    if args["describe"]:
        describe.describe()
        return
    if args["isolate"]:
        isolate.isolate(args["--pool"],
                        args["--no-affinity"],
                        args["<command>"],
                        args["<args>"],
                        args["--socket-id"])
        return
    if args["reconcile"]:
        reconcile.reconcile(int(args["--interval"]),
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
        nodereport.nodereport(int(args["--interval"]),
                              args["--publish"])
        return
    if args["webhook"]:
        webhook.webhook(args["--conf-file"], args["--cafile"],
                        args["--insecure"])
        return

    if args["reconfigure_setup"]:
        reconfigure_setup.reconfigure_setup(args["--num-exclusive-cores"],
                                            args["--num-shared-cores"],
                                            args["--excl-non-isolcpus"],
                                            args["--exclusive-mode"],
                                            args["--shared-mode"],
                                            args["--cmk-img"],
                                            args["--cmk-img-pol"],
                                            args["--install-dir"],
                                            args["--saname"],
                                            args["--namespace"])
        return

    if args["reconfigure"]:
        reconfigure.reconfigure(args["--node-name"],
                                args["--num-exclusive-cores"],
                                args["--num-shared-cores"],
                                args["--excl-non-isolcpus"],
                                args["--exclusive-mode"],
                                args["--shared-mode"], args["--install-dir"],
                                args["--namespace"])
        return

    if args["reaffinitize"]:
        reaffinitize.reaffinitize(args["--node-name"], args["--namespace"])
        return


def setup_logging():
    level = os.getenv("CMK_LOG_LEVEL", logging.INFO)
    logging.basicConfig(level=level)


if __name__ == "__main__":
    try:
        main()

    except RuntimeError as e:
        logging.error(e)
        sys.exit(1)
