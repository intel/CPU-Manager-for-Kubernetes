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

# Using the `kcm` command-line tool

## Usage

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
```

## Global configuration

| Environment variable  | Description |
| :-------------------- | :---------- |
| `KCM_LOCK_TIMEOUT`    | Maximum duration, in seconds, to hold the kcm configuration directory lock file. (Default: 30) |
| `KCM_PROC_FS`         | Path to the [procfs] to consult for pid information. `kcm isolate` and `kcm reconcile` require access to the host's process information in `/proc`. |
| `KCM_LOG_LEVEL`       | Adjusts logging verbosity. Valid values are: CRITICAL, ERROR, WARNING, INFO and DEBUG. The default log level is INFO. |
| `KCM_DEV_LSCPU_SYSFS` | Path to the system root to be used by `lscpu` for enumerating the cpu topology. NOTE: should only be used for development purposes. |

## Subcommands

-------------------------------------------------------------------------------

### `kcm init`

Initializes the kcm configuration directory customized for NFV workloads,
including three pools: _infra_, _controlplane_ and _dataplane_. The
_dataplane_ pool is EXCLUSIVE while the _controlplane_ and _infra_ pools
are SHARED.

Processor topology is discovered using [`lscpu`][lscpu].

This command succeeds if the config directory is already written. If
that is the case, logs are output saying so. If the existing
configuration does not match the requested pool allocations, then the
command logs at error level and exits with a nonzero status.

For more information about the config format on disk, refer to
[the `kcm` configuration directory][doc-config].

#### Core assignment policy

KCM isolate constrains user tasks to CPUs in the requested pool.
However, this does not prevent other system tasks from running on reserved CPUs.
The recommended way to resolve this problem is to use the [`isolcpus`][isolcpus] Linux kernel parameter.

KCM init discovers the value of `isolcpus` by inspecting `/proc/cmdline`.
These isolated CPU IDs are used to construct the dataplane and controlplane pools.
 In this way, the process scheduler will avoid co-scheduling other tasks there.
 If no isolated CPUs are available, KCM will continue to operate but the only guarantee is that pools are assigned in
 a core granular manner.

The number of _fully isolated cores_ should match the number of requested dataplane plus
controlplane cores. A core is fully isolated if all the logical cpu ids for the core are
in the `isolcpus` list.

##### Example

An example working setup could be as follows. On a single socket system with 8 cores
and 16 cpus, the cpu ids 0, 8 are resident on core 0, cpu ids 1, 9 are resident on core 1 and so on.

The `lscpu -p` output from this system could be:
```
# The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
2,2,0,0,,2,2,2,0
3,3,0,0,,3,3,3,0
4,4,0,0,,4,4,4,0
5,5,0,0,,5,5,5,0
6,6,0,0,,6,6,6,0
7,7,0,0,,7,7,7,0
8,0,0,0,,0,0,0,0
9,1,0,0,,1,1,1,0
10,2,0,0,,2,2,2,0
11,3,0,0,,3,3,3,0
12,4,0,0,,4,4,4,0
13,5,0,0,,5,5,5,0
14,6,0,0,,6,6,6,0
15,7,0,0,,7,7,7,0
```

We assign 4 cores to the dataplane pool, 1 core to the controlplane pool and the rest to the infra pool.
Therefore, 5 physical cores must be isolated. These are the default values for `kcm init`.

On a Ubuntu 16.04 server, `/etc/default/grub` contains:

```
GRUB_CMDLINE_LINUX_DEFAULT="net.ifnames=0 isolcpus=0,1,2,3,4,8,9,10,11,12"
```

The `isolcpus` list contains the cpu ids for the first 5 cores on the system.
To verify the topology on other systems and get the cpu ids, use `lscpu` or `hwloc-ls`.
After changing the file above, run the following:

```
update-grub
```

and reboot the system.

After this, running `kcm init --num-dp-cores=4 --num-cp-cores=1` will allocate
the first 4 cores (cpu id 0, 8, 1, 9, 2, 10, 3 and 11) for the dataplane pool,
the next core (cpu id 4, 12) for the controlplane pool and the rest (cpu id 5,13,6,14,7,15) to the infra pool

##### Caveats

CPUs may be stranded, i.e. not be utilized, if they are not isolated
 in a core granular manner. For example, consider a system with 4 cpus with id 0, 1, 2, 3
 where 0 and 2 are resident on core 0 and 1 and 3 are resident on core 1. Then having
 `isolcpus=0,1` will result in two stranded cpus where data and control containers may or may not land.
In this case, KCM will emit warnings such as `WARNING:root:Physical core 1 is partially isolated`.

Similarily, even fully isolated cores in excess of the number of dataplane
plus controlplane cores will be stranded i.e. KCM will not assign any
left over isolated cores to the infra pool. In this case, KCM will emit warnings such as
`WARNING:root:Not all isolated cores will be used by data and controlplane.`.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the KCM configuration directory. This
  directory must either not exist or be an empty directory.
- `--num-dp-cores=<num>` Number of (physical) processor cores to include
  in the dataplane pool.
- `--num-dp-cores=<num>` Number of (physical) processor cores to include
  in the controlplane pool.

**Example:**

```shell
$ docker run -it --volume=/etc/kcm:/etc/kcm:rw \
  kcm init --conf-dir=/etc/kcm --num-dp-cores=4 --num-cp-cores=1
```

-------------------------------------------------------------------------------

### `kcm discover`

Advertises the appropriate number of `KCM` [Opaque Integer Resource (OIR)][oir-docs]
slots, node label and node taint to the Kubernetes node. The number of 
OIR slots advertised is equal to the number of cpu lists under the 
__dataplane__ pool, as determined by examining the `KCM` configuration directory. 
For more information about the config format on disk, refer to 
the [`kcm` configuration directory][doc-config].

Notes:
- `kcm discover` is expected to be run as a Kubernetes Pod as it uses
[`incluster config`][link-incluster] provided by the
[Kubernetes python client][k8s-python-client] to get the required Kubernetes
cluster configuration. The [instructions][discover-op-manual] provided in the
operator's manual can be used to run the discover Pod.
- The node will be patched with `pod.alpha.kubernetes.io/opaque-int-resource-kcm`
OIR. 
- The node will be labeled with `"kcm.intel.com/kcm-node": "true"` label. 
- The node will be tainted with `kcm=true:NoSchedule` taint.
- The `KCM` configuration directory should exist and contain the dataplane 
pool to run `kcm discover`.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the KCM configuration directory.

**Example:**

```shell
$ docker run -it --volume=/etc/kcm:/etc/kcm \
  kcm discover --conf-dir=/etc/kcm
```

-------------------------------------------------------------------------------

### `kcm describe`

Prints a JSON representation of the kcm configuration directory.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the KCM configuration directory.

**Example:**

```
$ docker run -it --volume=/etc/kcm:/etc/kcm kcm describe --conf-dir=/etc/kcm
{
  "path": "/etc/kcm",
  "pools": {
    "controlplane": {
      "cpuLists": {
        "3,11": {
          "cpus": "3,11",
          "tasks": [
            1000,
            1001,
            1002,
            1003
          ]
        }
      },
      "exclusive": false,
      "name": "controlplane"
    },
    "dataplane": {
      "cpuLists": {
        "4,12": {
          "cpus": "4,12",
          "tasks": [
            2000
          ]
        },
        "5,13": {
          "cpus": "5,13",
          "tasks": [
            2001
          ]
        },
        "6,14": {
          "cpus": "6,14",
          "tasks": [
            2002
          ]
        },
        "7,15": {
          "cpus": "7,15",
          "tasks": [
            2003
          ]
        }
      },
      "exclusive": true,
      "name": "dataplane"
    },
    "infra": {
      "cpuLists": {
        "0-2,8-10": {
          "cpus": "0-2,8-10",
          "tasks": [
            3000,
            3001,
            3002
          ]
        }
      },
      "exclusive": false,
      "name": "infra"
    }
  }
}
```

-------------------------------------------------------------------------------

### `kcm reconcile`

Reconcile removes invalid process IDs from the kcm configuration directory by
checking them against [procfs]. This is to recover from the case where
[`kcm isolate`][kcm-isolate] exits before it has a chance to remove its own
PID from the `tasks` file. This could happen for a number of reasons, including
receiving the KILL signal while its subprocess is executing.

`--interval=<seconds>` will turn the reconciliation command into a long lived
process which runs reconciliation every `<seconds>`. If run with `--interval=0`,
reconcile is run once and exits.

`--publish` will send the reconciliation report to the Kubernetes API server.
This enables the operator to get reconciliation reports for all kubelets in one
place through `kubectl`. This option should only be used when the KCM
container is run as a Kubernetes Pod.

For instance:

```bash
$ kubectl get ReconcileReport
NAME            KIND
kcm-02-zzwt7w   ReconcileReport.v1.kcm.intel.com
```

```bash
$ kubectl get ReconcileReport kcm-02-zzwt7w -o json
{
  "apiVersion": "kcm.intel.com/v1",
  "kind": "ReconcileReport",
  "last_updated": "2017-01-12T23:55:08.735918",
  "metadata": {
    "creationTimestamp": "2017-01-12T23:55:08Z",
    "name": "kcm-02-zzwt7w",
    "namespace": "default",
    "resourceVersion": "263029",
    "selfLink": "/apis/kcm.intel.com/v1/namespaces/default/reconcilereports/kcm-02-zzwt7w",
    "uid": "8c4d6173-d922-11e6-a746-42010a800002"
  },
  "report": {
    "mismatchedCpuMasks": [],
    "reclaimedCpuLists": []
  }
}
```


_**NOTE:** This subcommand requires the `KCM_PROC_FS` environment variable
to be set._

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the KCM configuration directory.
- `--publish` Whether to publish reports to the Kubernetes API server
- `--interval=<seconds>` Number of seconds to wait between rerunning. If set
  to 0, will only run once.

**Example:**

```shell
$ docker run -it \
  --volume=/etc/kcm:/etc/kcm \
  --volume=/proc:/host/proc:ro \
  -e "KCM_PROC_FS=/host/proc" \
  kcm reconcile --interval=60 --conf-dir=/etc/kcm
```

-------------------------------------------------------------------------------

### `kcm isolate`

Constrains a command to the CPUs corresponding to an available CPU list
in a supplied pool.

If the requested pool is exclusive, the command may fail if there are no
unallocated CPU lists in the pool. An unallocated CPU list is one where the
`tasks` file is empty; see [the `kcm` configuration format][doc-config] for
details.)

If the requested pool is non-exclusive, any CPU list in that pool may be
chosen, regardless of current allocations.

`kcm isolate` writes its own PID into the selected `tasks` file before
executing the command in a sub-shell. When the subprocess exits, the program
removes the PID from the `tasks` file before exiting. If the `kcm
isolate` process exits abnormally (or receives the KILL signal) then the
`tasks` file may not be cleaned up. The [`kcm reconcile`][kcm-reconcile]
subcommand is designed to resolve this problem, and must be run
frequently on any host where `kcm isolate` is used.

Core affinity is achieved by first setting the CPU mask of the `kcm`
process before executing the command.

_**NOTE:** This subcommand requires the `KCM_PROC_FS` environment variable
to be set._

**Args:**

- `<command>` Command to isolate.
- `<args> ...` Command arguments.

**Flags:**

- `--conf-dir=<dir>` Path to the KCM configuration directory.
- `--pool=<pool>` Pool name: either _infra_, _controlplane_ or _dataplane_.

**Example:**

```shell
$ docker run -it \
  --volume=/opt/bin/kcm:/host/opt/bin/kcm \
  --volume=/etc/kcm:/etc/kcm \
  --volume=/proc:/host/proc:ro \
  -e "KCM_PROC_FS=/host/proc" \
  centos /host/opt/bin/kcm isolate --pool=infra sleep -- inf
```

-------------------------------------------------------------------------------

### `kcm install`

Builds a zero-dependency `kcm` executable in the installation directory.

Use install to place `kcm` on the host filesystem. Subsequent containers
can isolate themselves by mounting the install directory from the host and
then calling [`kcm isolate`][kcm-isolate].

**Args:**

_None_

**Flags:**

- `--install-dir=<dir>` KCM install directory.

**Example:**

_**NOTE:** On CoreOS, /usr is readonly so here we use /opt/bin instead,
which is both writable and on the path._

```shell
$ docker run -it \
  --volume=/opt/bin:/opt/bin:rw \
  kcm install --install-dir=/opt/bin
```

-------------------------------------------------------------------------------

### `kcm node-report`

Outputs a JSON report on node-level KCM configuration.

`--publish` will send the node report to the Kubernetes API server.
This enables the operator to get node reports for all kubelets in one
place through `kubectl`. This option should only be used when the KCM
container is run as a Kubernetes Pod.

`--interval=<seconds>` will turn the node-report command into a long lived
process which runs node-report every `<seconds>`. If run with `--interval=0`,
node-report is run once and exits.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the KCM configuration directory.
- `--publish` Whether to publish reports to the Kubernetes API server.
- `--interval=<seconds>` Number of seconds to wait between rerunning. If set
  to 0, will only run once.

**Example:**

_Generate a node report:_

```shell
$ docker run -it \
  --volume=/etc/kcm:/etc/kcm \
  --volume=/proc:/host/proc:ro \
  -e "KCM_PROC_FS=/host/proc" \
  kcm node-report --conf-dir=/etc/kcm --interval=60
```

_Get node reports from the API server using Kubectl:_

```bash
$ kubectl get NodeReport
NAME            KIND
kcm-02-zzwt7w   NodeReport.v1.kcm.intel.com
```

```bash
$ kubectl get NodeReport kcm-02-zzwt7w -o json
{
  "apiVersion": "kcm.intel.com/v1",
  "kind": "NodeReport",
  "last_updated": "2017-01-12T23:55:08.735918",
  "metadata": {
    "creationTimestamp": "2017-01-12T23:55:08Z",
    "name": "kcm-02-zzwt7w",
    "namespace": "default",
    "resourceVersion": "263029",
    "selfLink": "/apis/kcm.intel.com/v1/namespaces/default/nodereports/kcm-02-zzwt7w",
    "uid": "8c4d6173-d922-11e6-a746-42010a800002"
  },
  "report": {
    "checks": {
      "configDirectory": {
        "errors": [
          "CPU list overlap detected in exclusive:0 and shared:0 (in both: [0])"
        ],
        "ok": false
      }
    },
    "description": {
      "path": "/etc/kcm",
      "pools": {
        "exclusive": {
          "cpuLists": {
            "0": {
              "cpus": "0",
              "tasks": []
            }
          },
          "exclusive": true,
          "name": "exclusive"
        },
        "shared": {
          "cpuLists": {
            "0": {
              "cpus": "0",
              "tasks": []
            }
          },
          "exclusive": false,
          "name": "shared"
        }
      }
    }
  },
  "topology": {
    "sockets": {
      "0": {
        "cores": [
          {
            "cpus": [
              {
                "id": 0,
                "isolated": false
              },
              {
                "id": 8,
                "isolated": false
              }
            ],
            "id": 0
          },
          {
            "cpus": [
              {
                "id": 1,
                "isolated": false
              },
              {
                "id": 9,
                "isolated": false
              }
            ],
            "id": 1
          },
          {
            "cpus": [
              {
                "id": 2,
                "isolated": false
              },
              {
                "id": 10,
                "isolated": false
              }
            ],
            "id": 2
          },
          {
            "cpus": [
              {
                "id": 3,
                "isolated": false
              },
              {
                "id": 11,
                "isolated": false
              }
            ],
            "id": 3
          },
          {
            "cpus": [
              {
                "id": 4,
                "isolated": false
              },
              {
                "id": 12,
                "isolated": false
              }
            ],
            "id": 4
          },
          {
            "cpus": [
              {
                "id": 5,
                "isolated": false
              },
              {
                "id": 13,
                "isolated": false
              }
            ],
            "id": 5
          },
          {
            "cpus": [
              {
                "id": 6,
                "isolated": false
              },
              {
                "id": 14,
                "isolated": false
              }
            ],
            "id": 6
          },
          {
            "cpus": [
              {
                "id": 7,
                "isolated": false
              },
              {
                "id": 15,
                "isolated": false
              }
            ],
            "id": 7
          }
        ],
        "id": 0
      }
    }
  }
}
```

-------------------------------------------------------------------------------

### `kcm cluster-init`

Initializes a Kubernetes cluster for the `KCM` software. It runs `KCM`
subcommands, passed as comma-seperated values to `--kcm-cmd-list`, as
Kubernetes Pods. By default, it runs all the subcommands and uses all the 
default options. 

Notes:
- `kcm cluster-init` is expected to be run as a Kubernetes Pod as it uses
[`incluster config`][link-incluster] provided by the
[Kubernetes python client][k8s-python-client] to get the required Kubernetes
cluster configuration. The [instructions][cluster-init-op-manual] provided
in the operator's manual can be used to run the discover Pod.
- The KCM subcommands, as specified by the value passed for `--kcm-cmd-list`
are expected to be one of `init`, `discover`, `install`, `reconcile`, `nodereport`.
If `init` subcommand is specified, it expected to be the first command
in `--kcm-cmd-list`.
- `--kcm-img-pol` should be one of `Never`, `IfNotPresent`, `Always`.

**Args:**

_None_

**Flags:**
- `--host-list=<list>` Comma seperated list of Kubernetes nodes to prepare
  for KCM software. Either this flag or `--all-hosts` flag must be used.
- `--all-hosts` Prepare all Kubernetes nodes for the KCM software. Either
  this flag or `--host-list=<list>` flag must be used.
- `--kcm-cmd-list=<list>` Comma seperated list of KCM sub-commands to run on
  each host [default: init,reconcile,install,discover].
- `--kcm-img=<img>` KCM Docker image [default: kcm].
- `--kcm-img-pol=<pol>`   Image pull policy for the KCM Docker image
  [default: IfNotPresent].
- `--conf-dir=<dir>` Path to the KCM configuration directory. This
  directory must either not exist or be an empty directory.
- `--num-dp-cores=<num>` Number of (physical) processor cores to include
  in the dataplane pool.
- `--num-cp-cores=<num>` Number of (physical) processor cores to include
  in the controlplane pool.

**Example:**

```shell
$ docker run -it --volume=/etc/kcm:/etc/kcm:rw \
  kcm init --conf-dir=/etc/kcm --num-dp-cores=4 --num-cp-cores=1
```

-------------------------------------------------------------------------------


[doc-config]: config.md
[kcm-isolate]: #kcm-isolate
[kcm-reconcile]: #kcm-reconcile
[lscpu]: http://man7.org/linux/man-pages/man1/lscpu.1.html
[procfs]: http://man7.org/linux/man-pages/man5/proc.5.html
[link-incluster]: https://github.com/kubernetes-incubator/client-python/blob/master/kubernetes/config/incluster_config.py#L85
[k8s-python-client]: https://github.com/kubernetes-incubator/client-python
[discover-op-manual]: operator.md#advertising-kcm-opaque-integer-resource-oir-slots
[cluster-init-op-manual]: operator.md#prepare-kcm-nodes-by-running-kcm-cluster-init
[oir-docs]: http://kubernetes.io/docs/user-guide/compute-resources#opaque-integer-resources-alpha-feature
[isolcpus]: https://github.com/torvalds/linux/blob/master/Documentation/admin-guide/kernel-parameters.txt#L1669
