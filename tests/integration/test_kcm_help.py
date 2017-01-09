from .. import helpers
from . import integration


def test_kcm_help():
    assert helpers.execute(integration.kcm(), ["--help"]) == b"""kcm.

Usage:
  kcm (-h | --help)
  kcm --version
  kcm cluster-init (--host-list=<list>|--all-hosts) [--kcm-cmd-list=<list>]
                   [--kcm-img=<img>] [--conf-dir=<dir>] [--install-dir=<dir>]
                   [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm init [--conf-dir=<dir>] [--num-dp-cores=<num>] [--num-cp-cores=<num>]
  kcm discover [--conf-dir=<dir>]
  kcm describe [--conf-dir=<dir>]
  kcm reconcile [--conf-dir=<dir>] [--publish] [--interval=<seconds>]
  kcm isolate [--conf-dir=<dir>] --pool=<pool> <command> [-- <args> ...]
  kcm install --install-dir=<dir>
  kcm node-report [--conf-dir=<dir>] [--publish]

Options:
  -h --help             Show this screen.
  --version             Show version.
  --host-list=<list>    Comma seperated list of Kubernetes nodes to prepare
                        for KCM software.
  --all-hosts           Prepare all Kubernetes nodes for the KCM software.
  --kcm-cmd-list=<list> Comma seperated list of KCM sub-commands to run on
                        each host [default: init,reconcile,install,discover].
  --kcm-img=<img>       KCM Docker image [default: kcm].
  --conf-dir=<dir>      KCM configuration directory [default: /etc/kcm].
<<<<<<< HEAD
  --install-dir=<dir>   KCM install directory.
  --interval=<seconds>  Number of seconds to wait between rerunning.
                        If set to 0, will only run once. [default: 0]
=======
  --install-dir=<dir>   KCM install directory [default: /opt/bin].
>>>>>>> Added kcm cluster-init.
  --num-dp-cores=<num>  Number of data plane cores [default: 4].
  --num-cp-cores=<num>  Number of control plane cores [default: 1].
  --pool=<pool>         Pool name: either infra, controlplane or dataplane.
  --publish             Whether to publish reports to the Kubernetes
                        API server.
"""
