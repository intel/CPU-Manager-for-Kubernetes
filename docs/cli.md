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
                        each host [default: init,reconcile,install,discover].
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
```

## Global configuration

| Environment variable | Description |
| :------------------- | :---------- |
| `KCM_LOCK_TIMEOUT`   | Maximum duration, in seconds, to hold the kcm configuration directory lock file. (Default: 30) |
| `KCM_PROC_FS`        | Path to the [procfs] to consult for pid information. `kcm isolate` and `kcm reconcile` require access to the host's process information in `/proc`. |

## Subcommands

-------------------------------------------------------------------------------

### `kcm init`

Initializes the kcm configuration directory customized for NFV workloads,
including three pools: _infra_, _controlplane_ and _dataplane_. The
_dataplane_ pool is EXCLUSIVE while the _controlplane_ and _infra_ pools
are SHARED.

Processor topology is discovered using [`lscpu`][lscpu].

For more information about the config format on disk, refer to
[the `kcm` configuration directory][doc-config].

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
slots on the Kubernetes node. The number of slots advertised is equal to the
number of cpu lists under the __dataplane__ pool, as determined by examining
the `KCM` configuration directory. For more information about the config
format on disk, refer to [the `kcm` configuration directory][doc-config].

Notes:
- `kcm discover` is expected to be run as a Kubernetes Pod as it uses
[`incluster config`][link-incluster] provided by the
[Kubernetes python client][k8s-python-client] to get the required Kubernetes
cluster configuration. The [instructions][discover-op-manual] provided in the
operator's manual can be used to run the discover Pod.
- The node will be patched with `pod.alpha.kubernetes.io/opaque-int-resource-kcm'
OIR.
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

Outputs a JSON report on node-level KCM configuration problems.

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
        "errors": [],
        "ok": true
      }
    }
  }
}
```

-------------------------------------------------------------------------------

### `kcm cluster-init`

Initializes a Kubernetes cluster for the `KCM` software. It runs `KCM`
subcommands, passed as comma-seperated values to `--kcm-cmd-list`, as
Kubernetes Pods.

Notes:
- `kcm cluster-init` is expected to be run as a Kubernetes Pod as it uses
[`incluster config`][link-incluster] provided by the
[Kubernetes python client][k8s-python-client] to get the required Kubernetes
cluster configuration. The [instructions][cluster-init-op-manual] provided
in the operator's manual can be used to run the discover Pod.
- The KCM subcommands, as specified by the value passed for `--kcm-cmd-list`
are expected to be one of `init`, `discover`, `install`, `reconcile`.
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
  [default: Never].
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


[doc-config]: config.md
[kcm-isolate]: #kcm-isolate
[kcm-reconcile]: #kcm-reconcile
[lscpu]: http://man7.org/linux/man-pages/man1/lscpu.1.html
[procfs]: http://man7.org/linux/man-pages/man5/proc.5.html
[link-incluster]: https://github.com/kubernetes-incubator/client-python/blob/master/kubernetes/config/incluster_config.py#L85
[k8s-python-client]: https://github.com/kubernetes-incubator/client-python
[discover-op-manual]: operator.md#advertising-kcm-opaque-integer-resource-oir-slots
[oir-docs]: http://kubernetes.io/docs/user-guide/compute-resources#opaque-integer-resources-alpha-feature
