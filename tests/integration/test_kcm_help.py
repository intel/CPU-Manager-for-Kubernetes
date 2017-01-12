from .. import helpers
from . import integration


def test_kcm_help():
    assert helpers.execute(integration.kcm(), ["--help"]) == b"""kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm discover [--conf-dir=<dir>]
  kcm describe [--conf-dir=<dir>]
  kcm reconcile [--conf-dir=<dir>] [--publish]
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
"""
