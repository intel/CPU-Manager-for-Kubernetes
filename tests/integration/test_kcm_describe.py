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


def test_kcm_describe_ok():
    args = ["describe", "--conf-dir={}".format(helpers.conf_dir("ok"))]
    assert helpers.execute(integration.kcm(), args) == b"""{
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


def test_kcm_describe_minimal():
    args = ["describe",
            "--conf-dir={}".format(helpers.conf_dir("minimal"))]
    assert helpers.execute(integration.kcm(), args) == b"""{
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
"""
