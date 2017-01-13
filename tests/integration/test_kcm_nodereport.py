from .. import helpers
from . import integration
from intel import proc


def test_kcm_nodereport_ok():
    assert helpers.execute(
        integration.kcm(),
        ["node-report", "--conf-dir={}".format(helpers.conf_dir("ok"))],
        {proc.ENV_PROC_FS: helpers.procfs_dir("ok")}).decode() == """{
  "checks": {
    "configDirectory": {
      "errors": [],
      "ok": true
    }
  },
  "description": {
    "path": "/kcm/tests/data/config/ok",
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
}
"""


def test_kcm_nodereport_minimal():
    assert helpers.execute(
        integration.kcm(),
        ["node-report", "--conf-dir={}".format(helpers.conf_dir("minimal"))],
        {proc.ENV_PROC_FS: helpers.procfs_dir("ok")}).decode() == """{
  "checks": {
    "configDirectory": {
      "errors": [
        "CPU list overlap detected in exclusive:0 and shared:0 (in both: [0])"
      ],
      "ok": false
    }
  },
  "description": {
    "path": "/kcm/tests/data/config/minimal",
    "pools": {
      "exclusive": {
        "cpuLists": {
          "0": {
            "cpus": "0",
            "tasks": []
          }
        },
        "exclusive": true,
        "name": "exclusive"
      },
      "shared": {
        "cpuLists": {
          "0": {
            "cpus": "0",
            "tasks": []
          }
        },
        "exclusive": false,
        "name": "shared"
      }
    }
  }
}
"""
