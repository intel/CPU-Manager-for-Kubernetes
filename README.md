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
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm discover [--conf-dir=<dir>]
  kcm describe [--conf-dir=<dir>]
  kcm reconcile [--conf-dir=<dir>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]
  kcm install --install-dir=<dir>
  kcm node-report [--conf-dir=<dir>] [--publish]

Options:
  -h --help             Show this screen.
  --version             Show version.
  --conf-dir=<dir>      KCM configuration directory [default: /etc/kcm].
  --install-dir=<dir>   KCM install directory.
  --num-dp-cores=<num>  Number of data plane cores [default: 4].
  --num-cp-cores=<num>  Number of control plane cores [default: 1].
  --pool=<pool>         Pool name: either infra, controlplane or dataplane.
  --publish             Whether to publish reports to the Kubernetes
                        API server.
```

_For detailed usage information about each subcommand, see
[Using the kcm command-line tool][doc-cli]._

## Further Reading

- [Building kcm][doc-build]
- [Operator manual][doc-operator]
- [User manual][doc-user]
- [Using the kcm command-line tool][doc-cli]
- [The kcm configuration directory][doc-config]

[cpu-list]: http://man7.org/linux/man-pages/man7/cpuset.7.html#FORMATS
[doc-build]: docs/build.md
[doc-cli]: docs/cli.md
[doc-config]: docs/config.md
[doc-operator]: docs/operator.md
[doc-user]: docs/user.md
[procfs]: http://man7.org/linux/man-pages/man5/proc.5.html
