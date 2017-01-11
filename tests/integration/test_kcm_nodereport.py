from .. import helpers
from . import integration
from intel import proc


def test_kcm_nodereport_ok():
    assert helpers.execute(
        integration.kcm(),
        ["node-report", "--conf-dir={}".format(helpers.conf_dir("ok"))],
        {proc.ENV_PROC_FS: helpers.procfs_dir("ok")}) == b"""{
  "checks": {
    "configDirectory": {
      "errors": [],
      "ok": true
    }
  }
}
"""


def test_kcm_nodereport_minimal():
    assert helpers.execute(
        integration.kcm(),
        ["node-report", "--conf-dir={}".format(helpers.conf_dir("minimal"))],
        {proc.ENV_PROC_FS: helpers.procfs_dir("ok")}) == b"""{
  "checks": {
    "configDirectory": {
      "errors": [
        "CPU list overlap detected in exclusive:0 and shared:0 (in both: [0])"
      ],
      "ok": false
    }
  }
}
"""
