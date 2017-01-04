# kubernetes-comms-mvp

[![Build Status](https://travis-ci.com/intelsdi-x/kubernetes-comms-mvp.svg?token=ajyZ5osyX5HNjsUu5muj&branch=master)](https://travis-ci.com/intelsdi-x/kubernetes-comms-mvp)

## Usage summary

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

_For detailed usage information about each subcommand, see
[Using the kcm command-line tool][doc-cli]._

## Further Reading

- [Building kcm][doc-build]
- [Operator manual][doc-operator]
- [User manual][doc-user]
- [Using the kcm command-line tool][doc-cli]
- [The kcm configuration directory][doc-config]

[doc-build]: docs/build.md
[doc-cli]: docs/cli.md
[doc-config]: docs/config.md
[doc-operator]: docs/operator.md
[doc-user]: docs/user.md
