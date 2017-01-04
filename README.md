# kubernetes-comms-mvp

[![Build Status](https://travis-ci.com/intelsdi-x/kubernetes-comms-mvp.svg?token=ajyZ5osyX5HNjsUu5muj&branch=master)](https://travis-ci.com/intelsdi-x/kubernetes-comms-mvp)

## Installation

A running docker daemon (with permissions for the current user to issue docker commands) is required before running:

```bash
make
```

After this step completes successfully, `kcm` can be invoked through:

```bash
docker run -it kcm ...
```

Before running any subsequent comments, the KCM configuration directory has to be created.
Note that is it important that this configuration directory is created in a bind-mount into the container,
such that the directory resides on the host system and _not_ in the container.
Configuration directory initialization is done through:

```bash
kcm init
```

Please note that the default setting requires at least 6 physical cores (4 for data plane, 1 for control plane and 1 for other tasks).
To change this, use the `--num-dp-cores` and `--num-cp-cores` flags.

## Usage

```
kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm (describe | reconcile) [--conf-dir=<dir>]
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

## Configuration

_Example KCM pool filesystem configuration format:_

```
etc
└── kcm
    ├── lock
    └── pools
        ├── controlplane
        │   ├── 3,11
        │   │   └── tasks
        │   └── exclusive
        ├── dataplane
        │   ├── 4,12
        │   │   └── tasks
        │   ├── 5,13
        │   │   └── tasks
        │   ├── 6,14
        │   │   └── tasks
        │   ├── 7,15
        │   │   └── tasks
        │   └── exclusive
        └── infra
            ├── 0-2,8-10
            │   └── tasks
            └── exclusive
```

_wherein:_

- `/etc/kcm/lock` is a lock file to protect against conflicting
  concurrent modification
- `/etc/kcm/pools/<pool>/exclusive` determines whether each cpuset in
  the pool can be shared (value 0) or not (value 1).
- `/etc/kcm/pools/<pool>/<cpulist>/tasks` contains the Linux process IDs
  of containers to which the CPUset has been allocated.


# System Requirements

 - Docker 1.12.1 or above
 - Python 3.4.4 or above
