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

from .. import helpers
from . import integration


def test_cmk_help():
    assert helpers.execute(integration.cmk(), ["--help"]) == b"""cmk.

Usage:
  cmk (-h | --help)
  cmk --version
  cmk cluster-init (--host-list=<list>|--all-hosts) [--cmk-cmd-list=<list>]
                   [--cmk-img=<img>] [--cmk-img-pol=<pol>] [--conf-dir=<dir>]
                   [--install-dir=<dir>] [--num-exclusive-cores=<num>]
                   [--num-shared-cores=<num>] [--pull-secret=<name>]
                   [--saname=<name>] [--shared-mode=<mode>]
                   [--exclusive-mode=<mode>] [--namespace=<name>]
                   [--excl-non-isolcpus=<list>] [--no-taint]
  cmk init [--conf-dir=<dir>] [--num-exclusive-cores=<num>]
           [--num-shared-cores=<num>] [--socket-id=<num>]
           [--shared-mode=<mode>] [--exclusive-mode=<mode>]
           [--excl-non-isolcpus=<list>]
  cmk discover [--conf-dir=<dir>] [--no-taint]
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
  --no-taint                   Don't taint Kubernetes nodes.
"""  # noqa: E501
