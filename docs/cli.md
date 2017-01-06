# Using the `kcm` command-line tool

## Usage

```
kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
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
| `KCM_PROC_FS`        | Path to the [procfs] to consult for pid information. |
| `KCM_LOCK_TIMEOUT`   | Maximum duration, in seconds, to hold the kcm configuration directory lock file. (Default: 30) |

## Subcommands

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
  in the dataplane pool. [Default: 4]
- `--num-dp-cores=<num>` Number of (physical) processor cores to include
  in the controlplane pool. [Default: 1]

**Example:**

```shell
$ docker run -it --volume=/etc/kcm:/etc/kcm:rw kcm init \
  --conf-dir=/etc/kcm \
  --num-dp-cores=4 \
  --num-cp-cores=1
```

### `kcm describe`

Prints a JSON representation of the kcm configuration directory.

**Args:**

_None_

**Flags:**

- `--conf-dir=<dir>` Path to the KCM configuration directory.

**Example:**

```
$ docker run -it --volume=/etc/kcm:/etc/kcm:ro kcm describe --conf-dir=/etc/kcm
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

### `kcm reconcile`
TODO

### `kcm isolate`
TODO

### `kcm install`
TODO

[lscpu]: http://man7.org/linux/man-pages/man1/lscpu.1.html
[doc-config]: config.md
[procfs]: http://man7.org/linux/man-pages/man5/proc.5.html
