<!--
Intel License for KCM (version January 2017)

Copyright (c) 2017 Intel Corporation.

Use.  You may use the software (the "Software"), without modification, provided
the following conditions are met:

* Neither the name of Intel nor the names of its suppliers may be used to
  endorse or promote products derived from this Software without specific
  prior written permission.
* No reverse engineering, decompilation, or disassembly of this Software
  is permitted.

Limited patent license.  Intel grants you a world-wide, royalty-free,
non-exclusive license under patents it now or hereafter owns or controls to
make, have made, use, import, offer to sell and sell ("Utilize") this Software,
but solely to the extent that any such patent is necessary to Utilize the
Software alone. The patent license shall not apply to any combinations which
include this software.  No hardware per se is licensed hereunder.

Third party and other Intel programs.  "Third Party Programs" are the files
listed in the "third-party-programs.txt" text file that is included with the
Software and may include Intel programs under separate license terms. Third
Party Programs, even if included with the distribution of the Materials, are
governed by separate license terms and those license terms solely govern your
use of those programs.

DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS OR
APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR DEATH.

LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO INDEMNIFIY AND HOLD
INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING FROM YOUR USE OR
UNAUTHORIZED USE OF THE SOFTWARE.

No support.  Intel may make changes to the Software, at any time without
notice, and is not obligated to support, update or provide training for the
Software.

Termination. Intel may terminate your right to use the Software in the event of
your breach of this Agreement and you fail to cure the breach within a
reasonable period of time.

Feedback.  Should you provide Intel with comments, modifications, corrections,
enhancements or other input ("Feedback") related to the Software Intel will be
free to use, disclose, reproduce, license or otherwise distribute or exploit
the Feedback in its sole discretion without any obligations or restrictions of
any kind, including without limitation, intellectual property rights or
licensing obligations.

Compliance with laws.  You agree to comply with all relevant laws and
regulations governing your use, transfer, import or export (or prohibition
thereof) of the Software.

Governing law.  All disputes will be governed by the laws of the United States
of America and the State of Delaware without reference to conflict of law
principles and subject to the exclusive jurisdiction of the state or federal
courts sitting in the State of Delaware, and each party agrees that it submits
to the personal jurisdiction and venue of those courts and waives any
objections. The United Nations Convention on Contracts for the International
Sale of Goods (1980) is specifically excluded and will not apply to the
Software.
-->

# kubernetes-comms-mvp

[![Build Status](https://travis-ci.com/intelsdi-x/kubernetes-comms-mvp.svg?token=ajyZ5osyX5HNjsUu5muj&branch=master)](https://travis-ci.com/intelsdi-x/kubernetes-comms-mvp)

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
| Reconciliation | The process of resolving state between the KCM configuration directory and the Linux [procfs][procfs]. |

## Usage summary

```
kcm.

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
  --kcm-img=<img>       KCM Docker image [default: kcm:v0.4.0-rc1].
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
  --no-affinity         Do not set cpu affinity before forking the child
                        command. In this mode the user program is responsible
                        for reading the `KCM_CPUS_ASSIGNED` environment
                        variable and moving a subset of its own processes
                        and/or tasks to the assigned CPUs.
```

_For detailed usage information about each subcommand, see
[Using the kcm command-line tool][doc-cli]._

## Further Reading

- [Building kcm][doc-build]
- [Operator manual][doc-operator]
- [User manual][doc-user]
- [Using the kcm command-line tool][doc-cli]
- [The kcm configuration directory][doc-config]
- [End to end tests][doc-e2e]
- [Making release] [release]

[cpu-list]: http://man7.org/linux/man-pages/man7/cpuset.7.html#FORMATS
[doc-build]: docs/build.md
[doc-cli]: docs/cli.md
[doc-config]: docs/config.md
[doc-operator]: docs/operator.md
[doc-user]: docs/user.md
[procfs]: http://man7.org/linux/man-pages/man5/proc.5.html
[doc-e2e]: docs/end-to-end-tests.md
[release]: RELEASE.md
