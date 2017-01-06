# Using the `kcm` command-line tool

## Usage
```
kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm discover [--conf-dir=<dir>]
  kcm describe [--conf-dir=<dir>]
  kcm reconcile [--conf-dir=<dir>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]
  kcm install --install-dir=<dir>

Options:
  -h --help             Show this screen.
  --version             Show version.
  --conf-dir=<dir>      KCM configuration directory [default: /etc/kcm].
  --install-dir=<dir>   KCM install directory.
  --num-dp-cores=<num>  Number of data plane cores [default: 4].
  --num-cp-cores=<num>  Number of control plane cores [default: 1].
  --pool=<pool>         Pool name: either infra, controlplane or dataplane.
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

_**NOTE:** This subcommand requires the `KCM_PROC_FS` environment variable
to be set._

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the KCM configuration directory.

**Example:**

```shell
$ docker run \
  -it \
  -e "KCM_PROC_FS=/host/proc" \
  -v /proc:/host/proc:ro \
  -v /etc/kcm:/etc/kcm \
  kcm reconcile --conf-dir=/etc/kcm
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
$ docker run \
  -it \
  -e "KCM_PROC_FS=/host/proc" \
  -v /proc:/host/proc:ro \
  -v /etc/kcm:/etc/kcm \
  kcm isolate --pool=infra sleep -- inf
```

-------------------------------------------------------------------------------

### `kcm install`
TODO

[doc-config]: config.md
[kcm-isolate]: #kcm-isolate
[kcm-reconcile]: #kcm-reconcile
[lscpu]: http://man7.org/linux/man-pages/man1/lscpu.1.html
[procfs]: http://man7.org/linux/man-pages/man5/proc.5.html
