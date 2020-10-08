# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from intel import describe, config
from unittest.mock import patch, MagicMock
from contextlib import redirect_stdout
import io


class MockConfig(config.Config):

    def __init__(self, conf):
        self.cm_name = "fake-name"
        self.owner = "fake-owner"
        self.c_data = conf

    def lock(self):
        return

    def unlock(self):
        return


FAKE_CONFIG = {
    "exclusive": {
        "0": {
            "0,9": ["1001"],
            "1,10": ["1002"],
            "2,11": ["1003"]
        },
        "1": {
            "3,12": ["1004"]
        }
    },
    "shared": {
        "0": {
            "4,13,5,14": ["2001", "2002", "2003"]
        },
        "1": {}
    },
    "infra": {
        "0": {
            "6,15,7,16,8,17": ["3001", "4002", "5003"]
        },
        "1": {}
    }
}


@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_describe():
    c = MockConfig(config.build_config(FAKE_CONFIG))
    with patch('intel.config.Config', MagicMock(return_value=c)):
        f = io.StringIO()
        with redirect_stdout(f):
            describe.describe()
        out = f.getvalue()
        assert out == """{
  "pools": {
    "exclusive": {
      "cpuLists": {
        "0,9": {
          "cpus": "0,9",
          "tasks": [
            "1001"
          ]
        },
        "1,10": {
          "cpus": "1,10",
          "tasks": [
            "1002"
          ]
        },
        "2,11": {
          "cpus": "2,11",
          "tasks": [
            "1003"
          ]
        },
        "3,12": {
          "cpus": "3,12",
          "tasks": [
            "1004"
          ]
        }
      },
      "exclusive": true,
      "name": "exclusive"
    },
    "infra": {
      "cpuLists": {
        "6,15,7,16,8,17": {
          "cpus": "6,15,7,16,8,17",
          "tasks": [
            "3001",
            "4002",
            "5003"
          ]
        }
      },
      "exclusive": false,
      "name": "infra"
    },
    "shared": {
      "cpuLists": {
        "4,13,5,14": {
          "cpus": "4,13,5,14",
          "tasks": [
            "2001",
            "2002",
            "2003"
          ]
        }
      },
      "exclusive": false,
      "name": "shared"
    }
  }
}
"""
