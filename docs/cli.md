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

# Using the `cmk` command-line tool

## Usage

```
cmk.

Usage:
  cmk (-h | --help)
  cmk --version
  cmk cluster-init (--host-list=<list>|--all-hosts) [--cmk-cmd-list=<list>]
                   [--cmk-img=<img>] [--cmk-img-pol=<pol>] [--conf-dir=<dir>]
                   [--install-dir=<dir>] [--num-exclusive-cores=<num>]
                   [--num-shared-cores=<num>] [--pull-secret=<name>]
                   [--saname=<name>] [--shared-mode=<mode>]
                   [--exclusive-mode=<mode>] [--namespace=<name>]
  cmk init [--conf-dir=<dir>] [--num-exclusive-cores=<num>]
           [--num-shared-cores=<num>] [--socket-id=<num>]
           [--shared-mode=<mode>] [--exclusive-mode=<mode>]
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
  --cmk-img=<img>              CMK Docker image [default: cmk:v1.3.1].
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
```

## Global configuration

| Environment variable  | Description |
| :-------------------- | :---------- |
| `CMK_LOCK_TIMEOUT`    | Maximum duration, in seconds, to hold the cmk configuration directory lock file. (Default: 30) |
| `CMK_PROC_FS`         | Path to the [procfs] to consult for pid information. `cmk isolate` and `cmk reconcile` require access to the host's process information in `/proc`. |
| `CMK_LOG_LEVEL`       | Adjusts logging verbosity. Valid values are: CRITICAL, ERROR, WARNING, INFO and DEBUG. The default log level is INFO. |
| `CMK_DEV_LSCPU_SYSFS` | Path to the system root to be used by `lscpu` for enumerating the cpu topology. NOTE: should only be used for development purposes. |
| `CMK_NUM_CORES` | Sets number of cores to be allocated by `cmk isolate`. If not set, "1" is being used as default. |

## Subcommands

-------------------------------------------------------------------------------

### `cmk init`

Initializes the cmk configuration directory customized for NFV workloads,
including three pools: _infra_, _shared_ and _exclusive_. The
_exclusive_ pool is EXCLUSIVE while the _shared_ and _infra_ pools
are SHARED.

Processor topology is discovered using [`lscpu`][lscpu].

This command succeeds if the config directory is already written. If
that is the case, logs are output saying so. If the existing
configuration does not match the requested pool allocations, then the
command logs at error level and exits with a nonzero status.

For more information about the config format on disk, refer to
[the `cmk` configuration directory][doc-config].

#### Core assignment policy

CMK isolate constrains user tasks to CPUs in the requested pool.
However, this does not prevent other system tasks from running on reserved CPUs.
The recommended way to resolve this problem is to use the [`isolcpus`][isolcpus] Linux kernel parameter.

CMK init discovers the value of `isolcpus` by inspecting `/proc/cmdline`.
These isolated CPU IDs are used to construct the exclusive and shared pools.
 In this way, the process scheduler will avoid co-scheduling other tasks there.
 If no isolated CPUs are available, CMK will continue to operate but the only guarantee is that pools are assigned in
 a core granular manner.

The number of _fully isolated cores_ should match the number of requested exclusive plus
shared cores. A core is fully isolated if all the logical cpu ids for the core are
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

We assign 4 cores to the exclusive pool, 1 core to the shared pool and the rest to the infra pool.
Therefore, 5 physical cores must be isolated. These are the default values for `cmk init`.

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

After this, running `cmk init --num-exclusive-cores=4 --num-shared-cores=1` will allocate
the first 4 cores (cpu id 0, 8, 1, 9, 2, 10, 3 and 11) for the exclusive pool,
the next core (cpu id 4, 12) for the shared pool and the rest (cpu id 5,13,6,14,7,15) to the infra pool

##### Caveats

CPUs may be stranded, i.e. not be utilized, if they are not isolated
 in a core granular manner. For example, consider a system with 4 cpus with id 0, 1, 2, 3
 where 0 and 2 are resident on core 0 and 1 and 3 are resident on core 1. Then having
 `isolcpus=0,1` will result in two stranded cpus where data and control containers may or may not land.
In this case, CMK will emit warnings such as `WARNING:root:Physical core 1 is partially isolated`.

Similarily, even fully isolated cores in excess of the number of exclusive
plus shared cores will be stranded i.e. CMK will not assign any
left over isolated cores to the infra pool. In this case, CMK will emit warnings such as
`WARNING:root:Not all isolated cores will be used by data and shared pools.`.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the CMK configuration directory. This
  directory must either not exist or be an empty directory.
- `--num-exclusive-cores=<num>` Number of (physical) processor cores to include
  in the exclusive pool.
- `--num-shared-cores=<num>` Number of (physical) processor cores to include
  in the shared pool.

**Example:**

```shell
$ docker run -it --volume=/etc/cmk:/etc/cmk:rw \
  cmk init --conf-dir=/etc/cmk --num-exclusive-cores=4 --num-shared-cores=1
```

-------------------------------------------------------------------------------

### `cmk discover`

Advertises the appropriate number of `CMK` [Opaque Integer Resource (OIR)][oir-docs]
slots, node label and node taint to the Kubernetes node. The number of
OIR slots advertised is equal to the number of cpu lists under the
__exclusive__ pool, as determined by examining the `CMK` configuration directory.
For more information about the config format on disk, refer to
the [`cmk` configuration directory][doc-config].

**Notes:**
- `cmk discover` is expected to be run as a Kubernetes Pod as it uses
[`incluster config`][link-incluster] provided by the
[Kubernetes python client][k8s-python-client] to get the required Kubernetes
cluster configuration. The [instructions][discover-op-manual] provided in the
operator's manual can be used to run the discover Pod.
- The node will be patched with `pod.alpha.kubernetes.io/opaque-int-resource-cmk`
OIR.
- The node will be labeled with `"cmk.intel.com/cmk-node": "true"` label.
- The node will be tainted with `cmk=true:NoSchedule` taint.
- The `CMK` configuration directory should exist and contain the exclusive
pool to run `cmk discover`.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the CMK configuration directory.

**Example:**

```shell
$ docker run -it --volume=/etc/cmk:/etc/cmk \
  cmk discover --conf-dir=/etc/cmk
```

-------------------------------------------------------------------------------

### `cmk describe`

Prints a JSON representation of the cmk configuration directory.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the CMK configuration directory.

**Example:**

```
$ docker run -it --volume=/etc/cmk:/etc/cmk cmk describe --conf-dir=/etc/cmk
{
  "path": "/etc/cmk",
  "pools": {
    "shared": {
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
      "name": "shared"
    },
    "exclusive": {
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
      "name": "exclusive"
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

### `cmk reconcile`

Reconcile removes invalid process IDs from the cmk configuration directory by
checking them against [procfs]. This is to recover from the case where
[`cmk isolate`][cmk-isolate] exits before it has a chance to remove its own
PID from the `tasks` file. This could happen for a number of reasons, including
receiving the KILL signal while its subprocess is executing.

`--interval=<seconds>` will turn the reconciliation command into a long lived
process which runs reconciliation every `<seconds>`. If run with `--interval=0`,
reconcile is run once and exits.

`--publish` will send the reconciliation report to the Kubernetes API server.
This enables the operator to get reconciliation reports for all kubelets in one
place through `kubectl`. This option should only be used when the CMK
container is run as a Kubernetes Pod.

For instance:

For Kubernetes 1.6 and older versions which using third part resources:
```bash
$ kubectl get ReconcileReport
NAME            KIND
cmk-02-zzwt7w   ReconcileReport.v1.cmk.intel.com
```

```bash
$ kubectl get ReconcileReport cmk-02-zzwt7w -o json
{
  "apiVersion": "cmk.intel.com/v1",
  "kind": "ReconcileReport",
  "last_updated": "2017-01-12T23:55:08.735918",
  "metadata": {
    "creationTimestamp": "2017-01-12T23:55:08Z",
    "name": "cmk-02-zzwt7w",
    "namespace": "default",
    "resourceVersion": "263029",
    "selfLink": "/apis/cmk.intel.com/v1/namespaces/default/reconcilereports/cmk-02-zzwt7w",
    "uid": "8c4d6173-d922-11e6-a746-42010a800002"
  },
  "report": {
    "mismatchedCpuMasks": [],
    "reclaimedCpuLists": []
  }
}
```
For Kubernetes 1.7 and newer versions which using custom resources definitions:
```bash
$ kubectl get cmk-reconcilereport
NAME            KIND
cmk-02-zzwt7w   Cmk-reconcilereport.v1.intel.com
```

```bash
$ kubectl get cmk-reconcilereport cmk-02-zzwt7w -o json
{
  "apiVersion": "intel.com/v1",
    "kind": "Cmk-reconcilereport",
    "metadata": {
        "clusterName": "",
        "creationTimestamp": "2017-09-20T12:29:04Z",
        "deletionGracePeriodSeconds": null,
        "deletionTimestamp": null,
        "name": "cmk-02-zzwt7w",
        "namespace": "default",
        "resourceVersion": "7165673",
        "selfLink": "/apis/intel.com/v1/namespaces/default/cmk-reconcilereports/cmk-02-zzwt7w",
        "uid": "4a365a42-9dff-11e7-b032-fa163e7cbcb6"
    },
    "spec": {
        "report": {
            "reclaimedCpuLists": []
        }
    }
}
```

_**NOTE:** This subcommand requires the `CMK_PROC_FS` environment variable
to be set._

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the CMK configuration directory.
- `--publish` Whether to publish reports to the Kubernetes API server
- `--interval=<seconds>` Number of seconds to wait between rerunning. If set
  to 0, will only run once.

**Example:**

```shell
$ docker run -it \
  --volume=/etc/cmk:/etc/cmk \
  --volume=/proc:/host/proc:ro \
  -e "CMK_PROC_FS=/host/proc" \
  cmk reconcile --interval=60 --conf-dir=/etc/cmk
```

-------------------------------------------------------------------------------

### `cmk isolate`

Constrains a command to the CPUs corresponding to an available CPU list
in a supplied pool.

If the requested pool is exclusive, the command may fail if there are no
unallocated CPU lists in the pool or there are not enough free CPU lists
in that pool. An unallocated CPU list is one where the `tasks` file is empty;
see [the `cmk` configuration format][doc-config] for details.)

If the requested pool is non-exclusive, any CPU lists in that pool may be
chosen, regardless of current allocations.

`cmk isolate` consumes environmental variable `CMK_NUM_CORES`, reads its value
and based on it, allocates a number of available CPU lists, regardless of
its exclusiveness. For exclusive pools first `CMK_NUM_CORES` CPU lists are
allocated. For non-exclusive pools `CMK_NUM_CORES` CPU lists are chosen
randomly. `CMK_NUM_CORES` should be a positive integer, otherwise the command
will fail. If `CMK_NUM_CORES` variable is not set, a single CPU list will be
allocated by default.

`cmk isolate` writes its own PID into the selected `tasks` file before
executing the command in a sub-shell. When the subprocess exits, the program
removes the PID from the `tasks` file before exiting. If the `cmk
isolate` process exits abnormally (or receives the KILL signal) then the
`tasks` file may not be cleaned up. The [`cmk reconcile`][cmk-reconcile]
subcommand is designed to resolve this problem, and must be run
frequently on any host where `cmk isolate` is used.

`cmk isolate` sets the `CMK_CPUS_ASSIGNED`  variable in the child process'
environment. The value is the assigned CPU list from the requested pool,
formatted as a Linux [CPU list][cpu-list] string.

Core affinity is achieved by first setting the CPU mask of the `cmk`
process before executing the command. This step can be turned off by
supplying the `--no-affinity` flag.

_**NOTE:** This subcommand requires the `CMK_PROC_FS` environment variable
to be set._

**Args:**

- `<command>` Command to isolate.
- `<args> ...` Command arguments.

**Flags:**

- `--conf-dir=<dir>` Path to the CMK configuration directory.
- `--pool=<pool>`    Pool name: either _infra_, _shared_ or _exclusive_.
- `--no-affinity`    Do not set cpu affinity before forking the child
                     command. In this mode the user program is responsible
                     for reading the `CMK_CPUS_ASSIGNED` environment
                     variable and moving a subset of its own processes and/or
                     tasks to the assigned CPUs.

**Example:**

```shell
$ docker run -it \
  --volume=/opt/bin/cmk:/host/opt/bin/cmk \
  --volume=/etc/cmk:/etc/cmk \
  --volume=/proc:/host/proc:ro \
  -e "CMK_PROC_FS=/host/proc" \
  -e "CMK_NUM_CORES=1" \
  centos /host/opt/bin/cmk isolate --pool=infra sleep -- inf
```

-------------------------------------------------------------------------------

### `cmk install`

Builds a zero-dependency `cmk` executable in the installation directory.

Use install to place `cmk` on the host filesystem. Subsequent containers
can isolate themselves by mounting the install directory from the host and
then calling [`cmk isolate`][cmk-isolate].

**Args:**

_None_

**Flags:**

- `--install-dir=<dir>` CMK install directory.

**Example:**

_**NOTE:** On CoreOS, /usr is readonly so here we use /opt/bin instead,
which is both writable and on the path._

```shell
$ docker run -it \
  --volume=/opt/bin:/opt/bin:rw \
  cmk install --install-dir=/opt/bin
```

-------------------------------------------------------------------------------

### `cmk node-report`

Outputs a JSON report on node-level CMK configuration.

`--publish` will send the node report to the Kubernetes API server.
This enables the operator to get node reports for all kubelets in one
place through `kubectl`. This option should only be used when the CMK
container is run as a Kubernetes Pod.

`--interval=<seconds>` will turn the node-report command into a long lived
process which runs node-report every `<seconds>`. If run with `--interval=0`,
node-report is run once and exits.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the CMK configuration directory.
- `--publish` Whether to publish reports to the Kubernetes API server.
- `--interval=<seconds>` Number of seconds to wait between rerunning. If set
  to 0, will only run once.

**Example:**

_Generate a node report:_

```shell
$ docker run -it \
  --volume=/etc/cmk:/etc/cmk \
  --volume=/proc:/host/proc:ro \
  -e "CMK_PROC_FS=/host/proc" \
  cmk node-report --conf-dir=/etc/cmk --interval=60
```

_Get node reports from the API server using Kubectl:_

For Kubernetes 1.6 and older versions which using third part resources:

```bash
$ kubectl get NodeReport
NAME            KIND
cmk-02-zzwt7w   NodeReport.v1.cmk.intel.com
```

```bash
$ kubectl get NodeReport cmk-02-zzwt7w -o json
{
  "apiVersion": "cmk.intel.com/v1",
  "kind": "NodeReport",
  "last_updated": "2017-01-12T23:55:08.735918",
  "metadata": {
    "creationTimestamp": "2017-01-12T23:55:08Z",
    "name": "cmk-02-zzwt7w",
    "namespace": "default",
    "resourceVersion": "263029",
    "selfLink": "/apis/cmk.intel.com/v1/namespaces/default/nodereports/cmk-02-zzwt7w",
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
      "path": "/etc/cmk",
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
For Kubernetes 1.7 and newer versions which using custom resources definitions:
```bash
$ kubectl get cmk-nodereport
NAME            KIND
cmk-02-zzwt7w   Cmk-nodereport.v1.intel.com
```

```bash
$ kubectl get cmk-nodereport cmk-02-zzwt7w -o json
{
  "apiVersion": "intel.com/v1",      
  "kind": "Cmk-nodereport",
  "metadata": {
    "clusterName": "",           
    "creationTimestamp": "2017-09-20T14:06:20Z",
    "deletionGracePeriodSeconds": null,
    "deletionTimestamp": null,            
    "name": "cmk-02-zzwt7w", 
    "namespace": "default",          
    "resourceVersion": "7180345",
    "selfLink": "/apis/intel.com/v1/namespaces/default/cmk-nodereports/cmk-02-zzwt7w",
    "uid": "e0f78043-9e0c-11e7-b032-fa163e7cbcb6"  
  },
  "spec": {                                                                                                                                                                                                      
        "report": {                                                                                                                                                                                                
            "checks": {                                                                                                                                                                                            
                "configDirectory": {                                                                                                                                                                               
                    "errors": [],                                                                                                                                                                                  
                    "ok": true                                                                                                                                                                                     
                }                                                                                                                                                                                                  
            },                                                                                                                                                                                                     
            "description": {                                                                                                                                                                                       
                "path": "/etc/cmk",                                                                                                                                                                                
                "pools": {                                                                                                                                                                                         
                    "shared": {                                                                                                                                                                              
                        "cpuLists": {                                                                                                                                                                              
                            "2": {                                                                                                                                                                                 
                                "cpus": "2",                                                                                                                                                                       
                                "tasks": []                                                                                                                                                                        
                            }                                                                                                                                                                                      
                        },                                                                                                                                                                                         
                        "exclusive": false,                                                                                                                                                                        
                        "name": "shared"                                                                                                                                                                     
                    },                                                                                                                                                                                             
                    "exclusive": {                                                                                                                                                                                 
                        "cpuLists": {                                                                                                                                                                              
                            "0": {                                                                                                                                                                                 
                                "cpus": "0",                                                                                                                                                                       
                                "tasks": []                                                                                                                                                                        
                            },                                                                                                                                                                                     
                            "1": {                                                                                                                                                                                 
                                "cpus": "1",                                                                                                                                                                       
                                "tasks": []                                                                                                                                                                        
                            }                                                                                                                                                                                      
                        },                                                                                                                                                                                         
                        "exclusive": true,                                                                                                                                                                         
                        "name": "exclusive"                                                                                                                                                                        
                    },
                    "infra": {                                                                                                                                                                                     
                        "cpuLists": {                                                                                                                                                                              
                            "3": {                                                                                                                                                                                 
                                "cpus": "3",                                                                                                                                                                       
                                "tasks": [                                                                                                                                                                         
                                    3416                                                                                                                                                                           
                                ]                                                                                                                                                                                  
                            },                                                                                                                                                                                     
                            "4": {                                                                                                                                                                                 
                                "cpus": "4",                                                                                                                                                                       
                                "tasks": [                                                                                                                                                                         
                                    3387                                                                                                                                                                           
                                ]                                                                                                                                                                                  
                            },                                                                                                                                                                                     
                            "5": {                                                                                                                                                                                 
                                "cpus": "5",
                                "tasks": []
                            },
                            "6": {
                                "cpus": "6",
                                "tasks": []
                            },
                            "7": {
                                "cpus": "7",
                                "tasks": []
                            }
                        },
                        "exclusive": false,
                        "name": "infra"
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
                                    }
                                ],
                                "id": 0
                            }
                        ],
                        "id": 0
                    },
                    "1": {
                        "cores": [
                            {
                                "cpus": [
                                    {
                                        "id": 1,
                                        "isolated": false
                                    }
                                ],
                                "id": 1
                            }
                        ],
                        "id": 1
                    },
                    "2": {
                        "cores": [
                            {
                                "cpus": [
                                    {
                                        "id": 2,
                                        "isolated": false
                                    }
                                ],
                                "id": 2
                            }
                        ],
                        "id": 2
                    },
                    "3": {
                        "cores": [
                            {
                                "cpus": [
                                    {
                                        "id": 3,
                                        "isolated": false
                                    }
                                ],
                                "id": 3
                            }
                        ],
                        "id": 3
                    },
                    "4": {
                        "cores": [
                            {
                                "cpus": [
                                    {
                                        "id": 4,
                                        "isolated": false
                                    }
                                ],
                                "id": 4
                            }
                        ],
                        "id": 4
                    },
                    "5": {
                        "cores": [
                            {
                                "cpus": [
                                    {
                                        "id": 5,
                                        "isolated": false
                                    }
                                ],
                                "id": 5
                            }
                        ],
                        "id": 5
                    },
                    "6": {
                        "cores": [
                            {
                                "cpus": [
                                    {
                                        "id": 6,
                                        "isolated": false
                                    }
                                ],
                                "id": 6
                            }
                        ],
                        "id": 6
                    },
                    "7": {
                        "cores": [
                            {
                                "cpus": [
                                    {
                                        "id": 7,
                                        "isolated": false
                                    }
                                ],
                                "id": 7
                            }
                        ],
                        "id": 7
                    }
                }
            }
        }
    }                    
}
```

-------------------------------------------------------------------------------

### `cmk cluster-init`

Initializes a Kubernetes cluster for the `CMK` software. It runs `CMK`
subcommands, passed as comma-seperated values to `--cmk-cmd-list`, as
Kubernetes Pods. By default, it runs all the subcommands and uses all the
default options.

**Notes:**
- `cmk cluster-init` is expected to be run as a Kubernetes Pod as it uses
[`incluster config`][link-incluster] provided by the
[Kubernetes python client][k8s-python-client] to get the required Kubernetes
cluster configuration. The [instructions][cluster-init-op-manual] provided
in the operator's manual can be used to run the discover Pod.
- The CMK subcommands, as specified by the value passed for `--cmk-cmd-list`
are expected to be one of `init`, `discover`, `install`, `reconcile`, `nodereport`.
If `init` subcommand is specified, it expected to be the first command
in `--cmk-cmd-list`.
- `--cmk-img-pol` should be one of `Never`, `IfNotPresent`, `Always`.
- If Kubernetes version is v1.9.0 or above, Mutating Admission Webhook and its
dependencies (mutating admission configuration, secret, config map and service) are
also deployed. `cmk cluster-init` will create an X509 private key and self-signed
TLS certificate, which can be replaced. Base64 encoded key and certificate are
stored in `cmk-webhook-certs` secret object. After updating them, `cmk-webhook-pod`
should be restarted to load new  Additionally certificate is stored in
the `cmk-webhook-config` MutatingWebhookConfiguration object and in such scenario,
it needs to be updated as well.

**Args:**

_None_

**Flags:**

- `--host-list=<list>` Comma seperated list of Kubernetes nodes to prepare
  for CMK software. Either this flag or `--all-hosts` flag must be used.
- `--all-hosts` Prepare all Kubernetes nodes for the CMK software. Either
  this flag or `--host-list=<list>` flag must be used.
- `--cmk-cmd-list=<list>` Comma seperated list of CMK sub-commands to run on
  each host [default: init,reconcile,install,discover].
- `--cmk-img=<img>` CMK Docker image [default: cmk].
- `--cmk-img-pol=<pol>`   Image pull policy for the CMK Docker image
  [default: IfNotPresent].
- `--conf-dir=<dir>` Path to the CMK configuration directory. This
  directory must either not exist or be an empty directory.
- `--num-exclusive-cores=<num>` Number of (physical) processor cores to include
  in the exclusive pool.
- `--num-shared-cores=<num>` Number of (physical) processor cores to include
  in the shared pool.
- `--pull-secret=<name>`  Name of secret used for pulling Docker images from
  restricted Docker registry.

**Example:**

```shell
$ docker run -it --volume=/etc/cmk:/etc/cmk:rw \
  cmk cluster-init --conf-dir=/etc/cmk --num-exclusive-cores=4 --num-shared-cores=1
```

-------------------------------------------------------------------------------

### `cmk uninstall`

Removes `cmk` from a node. Uninstall process reverts `cmk cluster-init`:
 - deletes `cmk-rediscover-reconcile-nodereport-pod-{node}` if present
 - removes `NodeReport` from Kubernetes ThirdPartyResources if present
 - removes `ReconcileReport` from Kubernetes ThirdPartyResources if present
 - removes cmk node label if present
 - removes cmk node taint if present
 - removes cmk node OIR if present
 - removes `--conf-dir=<dir>` if present and no processes are running that use `cmk isolate`
 - removes cmk binary from `--install-dir=<dir>`, if binary is not present then throws an error
 - removes `cmk-webhook-pod` along with other webhook dependencies (mutating admission
 configuration, secret, config map and service), if CMK was installed on a cluster with mutating admission controller API


**Notes:**
As described above "if present" indicates whether there isn't anything to delete/remove,
uninstall process will not fail and proceed to the next step. This allows `cmk uninstall` command
to fully purge inconsistent environment i.e. of some failures in `cmk cluster-init`

Removing `--conf-dir=<dir>` requires no processes present on system that use `cmk isolate`
(with entry in configuration directory). Please stop/remove them otherwise `cmk uninstall` will
throw an error in that step and uninstall will fail.
For this reason `cmk uninstall` cannot be run through `cmk isolate`.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the CMK configuration directory.
- `--install-dir=<dir>` CMK installation directory.

**Example:**

```sh
$ docker run -it \
--volume=/etc/cmk:/etc/cmk:rw \
--volume=/opt/bin:/opt/bin:rw \
  cmk uninstall
```

-------------------------------------------------------------------------------

### `cmk webhook`

Runs webhook server application which can be called by Mutating Admission Controller in
the API server. When the user tries to create a pod which definition contains any container
requesting CMK Extended Resources, CMK webhook modifies it by injecting environmental
variable `CMK_NUM_CORES` with its value set to a number of cores specified in the Extended
Resource request. This allows `cmk isolate` to assign multiple CPU cores to given process.
Beyond that, the webhook applies additional modifications to the pod which are defined in
the mutations configuration file in YAML format. Mutations can be applied per pod or per
container. Default configuration deployed during `cmk cluster-init` adds CMK installation
and configuration directories and host /proc filesystem volumes, CMK service account,
tolerations required for the pod to be scheduled on the CMK enabled node and approprietly
annotates pod.
Containers specifications are updated with volume mounts (referencing volumes added to
the pod) and environmental variable `CMK_PROC_FS`.

Server configuration is loaded once during `cmk webhook` startup. Example server
configuration:
```
server:
  binding-address: "0.0.0.0"
  port: 443
  cert: "/etc/ssl/cert.pem"
  key: "/etc/ssl/key.pem"
  mutations: "/etc/webhook/mutations.yaml"
```
| Key | Description |
| :- | :- |
| `binding-address` | The IP address on which to advertise the webhook server. |
| `port` | The port on which to serve HTTPS with authentication and authorization. |
| `cert` | SSL certification file used to secure communication with API server. |
| `key` | The path to the file that contains the current private key matching `cert` file. |
| `mutations` | The path to the file containing definition of mutations applied to pod and containers. |

Example mutations config file:
```
mutations:
  perPod:
    metadata:
      annotations:
        cmk.intel.com/resources-injected: "true"
    spec:
      serviceAccount: cmk-serviceaccount
      tolerations:
      - operator: Exists
      volumes:
      - name: cmk-host-proc
        hostPath:
          path: "/proc"
      - name: cmk-config-dir
        hostPath:
          path: "/etc/cmk"
      - name: cmk-install-dir
        hostPath:
          path: "/opt/bin"
  perContainer:
    env:
    - name: CMK_PROC_FS
      value: "/host/proc"
    volumeMounts:
    - name: cmk-host-proc
      mountPath: /host/proc
      readOnly: true
    - name: cmk-config-dir
      mountPath: /etc/cmk
    - name: cmk-install-dir
      mountPath: /opt/bin
```
| Key | Description |
| :- | :- |
| `perPod` | Pod specification in the same format as regular [Kubernetes V1 API Pod][v1-pod] object. Note that it contains only elements, which need to be added (or updated) on top of the original pod specification. |
| `perContainer` | Container specification in the same format as regular [Kubernetes V1 API Container][v1-container] object. Note that it contains only elements, which need to be added (or updated) on top of the original container specification. |

Mutations configuration is loaded from the file on each mutation request, so it can be
modified during webhook server runtime.

**Notes:**

Mutating admission webhook requires Kubernetes 1.9.0 or newer. Mutating Admission Controller
API is in beta in Kubernetes 1.9 and is enabled by default. In order to make Kubernetes API
server send admission review requests to the CMK webhook server,
MutatingAdmissionConfiguration object needs to be created on the Kubernetes cluster.

**Args:**

_None_

**Flags:**

- `--conf-file=<path>` Path to the webhook configuration file.

**Example:**

```sh
$ docker run -it \
--volume=/etc/cmk:/etc/cmk:rw \
--volume=/opt/bin:/opt/bin:rw \
--volume=/etc/webhook:/etc/webhook:rw \
--volume=/etc/ssl:/etc/ssl:rw \
  cmk webhook --conf-file=/etc/webhook/server.yaml
```

-------------------------------------------------------------------------------

[cpu-list]: http://man7.org/linux/man-pages/man7/cpuset.7.html#FORMATS
[doc-config]: config.md
[cmk-isolate]: #cmk-isolate
[cmk-reconcile]: #cmk-reconcile
[lscpu]: http://man7.org/linux/man-pages/man1/lscpu.1.html
[procfs]: http://man7.org/linux/man-pages/man5/proc.5.html
[link-incluster]: https://github.com/kubernetes-incubator/client-python/blob/master/kubernetes/config/incluster_config.py#L85
[k8s-python-client]: https://github.com/kubernetes-incubator/client-python
[discover-op-manual]: operator.md#advertising-cmk-opaque-integer-resource-oir-slots
[cluster-init-op-manual]: operator.md#prepare-cmk-nodes-by-running-cmk-cluster-init
[oir-docs]: http://kubernetes.io/docs/user-guide/compute-resources#opaque-integer-resources-alpha-feature
[isolcpus]: https://github.com/torvalds/linux/blob/master/Documentation/admin-guide/kernel-parameters.txt#L1669
[v1-pod]:https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.11/#pod-v1-core
[v1-container]:https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.11/#container-v1-core
