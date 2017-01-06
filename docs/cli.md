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
| `KCM_PROC_FS`        | `kcm isolate` and `kcm reconcile` requires access to the host's process information in `/proc`. For this, the `KCM_PROC_FS` environment variable is required. |

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
docker run -it --volume=/etc/kcm:/etc/kcm:rw kcm init \
  --conf-dir=/etc/kcm \
  --num-dp-cores=4 \
  --num-cp-cores=1
```

### `kcm describe`
TODO

### `kcm reconcile`
TODO

### `kcm isolate`
TODO

### `kcm install`
TODO

[lscpu]: http://man7.org/linux/man-pages/man1/lscpu.1.html
[doc-config]: config.md
