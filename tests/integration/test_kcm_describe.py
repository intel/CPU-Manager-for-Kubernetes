from . import integration


def test_kcm_describe():
    args = ["describe", "--conf-dir={}".format(integration.conf_dir("ok"))]
    assert integration.execute(integration.kcm(), args) == b"""{
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
"""
