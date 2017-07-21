<!--
Copyright (c) 2017 Intel Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# CPU Manager for Kubernetes

[![Build Status](https://travis-ci.org/Intel-Corp/CPU-Manager-for-Kubernetes.svg?branch=master)](https://travis-ci.org/Intel-Corp/CPU-Manager-for-Kubernetes)

## Overview

This project provides basic core affinity for NFV-style workloads on top
of vanilla Kubernetes v1.5+.

This project ships a single multi-use command-line program to perform
various functions for host configuration, managing groups of CPUs, and
constraining workloads to specific CPUs.

## Concepts

| Term           | Meaning |
| :------------- | :------ |
| Pool           | A named group of CPU lists. A pool can be either _exclusive_ or _shared_. In an _exclusive_ pool, only one task may be allocated to each CPU list simultaneously. |
| CPU list       | A group of logical CPUs, identified by ID as reported by the operating system. CPU lists conform to the Linux cpuset [CPU list format][cpu-list]. |
| Task list      | A list of Linux process IDs. |
| Isolation      | Steps required to set up a process environment so that it runs only on a desired subset of the available CPUs. |
| Reconciliation | The process of resolving state between the CMK configuration directory and the Linux [procfs][procfs]. |

## Usage summary

```
cmk.

Usage:
  cmk (-h | --help)
  cmk --version
  cmk cluster-init (--host-list=<list>|--all-hosts) [--cmk-cmd-list=<list>]
                   [--cmk-img=<img>] [--cmk-img-pol=<pol>] [--conf-dir=<dir>]
                   [--install-dir=<dir>] [--num-dp-cores=<num>]
                   [--num-cp-cores=<num>] [--pull-secret=<name>]
                   [--saname=<name>]
  cmk init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  cmk discover [--conf-dir=<dir>]
  cmk describe [--conf-dir=<dir>]
  cmk reconcile [--conf-dir=<dir>] [--publish] [--interval=<seconds>]
  cmk isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]
              [--no-affinity]
  cmk install [--install-dir=<dir>]
  cmk node-report [--conf-dir=<dir>] [--publish] [--interval=<seconds>]
  cmk uninstall [--install-dir=<dir>] [--conf-dir=<dir>]

Options:
  -h --help             Show this screen.
  --version             Show version.
  --host-list=<list>    Comma seperated list of Kubernetes nodes to prepare
                        for CMK software.
  --all-hosts           Prepare all Kubernetes nodes for the CMK software.
  --cmk-cmd-list=<list> Comma seperated list of CMK sub-commands to run on
                        each host
                        [default: init,reconcile,install,discover,nodereport].
  --cmk-img=<img>       CMK Docker image [default: cmk:v1.0.1].
  --cmk-img-pol=<pol>   Image pull policy for the CMK Docker image
                        [default: IfNotPresent].
  --conf-dir=<dir>      CMK configuration directory [default: /etc/cmk].
  --install-dir=<dir>   CMK install directory [default: /opt/bin].
  --interval=<seconds>  Number of seconds to wait between rerunning.
                        If set to 0, will only run once. [default: 0]
  --num-dp-cores=<num>  Number of data plane cores [default: 4].
  --num-cp-cores=<num>  Number of control plane cores [default: 1].
  --pool=<pool>         Pool name: either infra, controlplane or dataplane.
  --publish             Whether to publish reports to the Kubernetes
                        API server.
  --pull-secret=<name>  Name of secret used for pulling Docker images from
                        restricted Docker registry.
  --saname=<name>       ServiceAccount name to pass
                        [default: cmk-serviceaccount].
  --no-affinity         Do not set cpu affinity before forking the child
                        command. In this mode the user program is responsible
                        for reading the `CMK_CPUS_ASSIGNED` environment
                        variable and moving a subset of its own processes
                        and/or tasks to the assigned CPUs.
```

_For detailed usage information about each subcommand, see
[Using the cmk command-line tool][doc-cli]._

## Further Reading

- [Architecture][arch]
- [Building cmk][doc-build]
- [Operator manual][doc-operator]
- [User manual][doc-user]
- [Using the cmk command-line tool][doc-cli]
- [The cmk configuration directory][doc-config]
- [Releasing][release]

[arch]: docs/architecture.md
[cpu-list]: http://man7.org/linux/man-pages/man7/cpuset.7.html#FORMATS
[doc-build]: docs/build.md
[doc-cli]: docs/cli.md
[doc-config]: docs/config.md
[doc-operator]: docs/operator.md
[doc-user]: docs/user.md
[procfs]: http://man7.org/linux/man-pages/man5/proc.5.html
[release]: RELEASE.md
