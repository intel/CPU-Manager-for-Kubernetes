# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .. import helpers
from . import integration
from intel import proc, topology


test_env = {
    proc.ENV_PROC_FS: helpers.procfs_dir("ok"),
    topology.ENV_LSCPU_SYSFS: helpers.sysfs_dir("xeon_d")
}


def test_kcm_nodereport_ok():
    assert helpers.execute(
        integration.kcm(),
        ["node-report", "--conf-dir={}".format(helpers.conf_dir("ok"))],
        test_env).decode() == """{
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
  },
  "topology": {
    "sockets": {
      "0": {
        "cores": [
          {
            "cpus": [
              {
                "id": 0,
                "isolated": false
              },
              {
                "id": 8,
                "isolated": false
              }
            ],
            "id": 0
          },
          {
            "cpus": [
              {
                "id": 1,
                "isolated": false
              },
              {
                "id": 9,
                "isolated": false
              }
            ],
            "id": 1
          },
          {
            "cpus": [
              {
                "id": 2,
                "isolated": false
              },
              {
                "id": 10,
                "isolated": false
              }
            ],
            "id": 2
          },
          {
            "cpus": [
              {
                "id": 3,
                "isolated": false
              },
              {
                "id": 11,
                "isolated": false
              }
            ],
            "id": 3
          },
          {
            "cpus": [
              {
                "id": 4,
                "isolated": false
              },
              {
                "id": 12,
                "isolated": false
              }
            ],
            "id": 4
          },
          {
            "cpus": [
              {
                "id": 5,
                "isolated": false
              },
              {
                "id": 13,
                "isolated": false
              }
            ],
            "id": 5
          },
          {
            "cpus": [
              {
                "id": 6,
                "isolated": false
              },
              {
                "id": 14,
                "isolated": false
              }
            ],
            "id": 6
          },
          {
            "cpus": [
              {
                "id": 7,
                "isolated": false
              },
              {
                "id": 15,
                "isolated": false
              }
            ],
            "id": 7
          }
        ],
        "id": 0
      }
    }
  }
}
"""


def test_kcm_nodereport_minimal():
    assert helpers.execute(
        integration.kcm(),
        ["node-report", "--conf-dir={}".format(helpers.conf_dir("minimal"))],
        test_env).decode() == """{
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
  },
  "topology": {
    "sockets": {
      "0": {
        "cores": [
          {
            "cpus": [
              {
                "id": 0,
                "isolated": false
              },
              {
                "id": 8,
                "isolated": false
              }
            ],
            "id": 0
          },
          {
            "cpus": [
              {
                "id": 1,
                "isolated": false
              },
              {
                "id": 9,
                "isolated": false
              }
            ],
            "id": 1
          },
          {
            "cpus": [
              {
                "id": 2,
                "isolated": false
              },
              {
                "id": 10,
                "isolated": false
              }
            ],
            "id": 2
          },
          {
            "cpus": [
              {
                "id": 3,
                "isolated": false
              },
              {
                "id": 11,
                "isolated": false
              }
            ],
            "id": 3
          },
          {
            "cpus": [
              {
                "id": 4,
                "isolated": false
              },
              {
                "id": 12,
                "isolated": false
              }
            ],
            "id": 4
          },
          {
            "cpus": [
              {
                "id": 5,
                "isolated": false
              },
              {
                "id": 13,
                "isolated": false
              }
            ],
            "id": 5
          },
          {
            "cpus": [
              {
                "id": 6,
                "isolated": false
              },
              {
                "id": 14,
                "isolated": false
              }
            ],
            "id": 6
          },
          {
            "cpus": [
              {
                "id": 7,
                "isolated": false
              },
              {
                "id": 15,
                "isolated": false
              }
            ],
            "id": 7
          }
        ],
        "id": 0
      }
    }
  }
}
"""
