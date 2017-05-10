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
from intel import config, proc
import os
import tempfile


def test_kcm_reconcile(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(os.path.join(temp_dir, "reconcile"))]
    )

    c = config.Config(os.path.join(temp_dir, "reconcile"))
    pools = c.pools()
    cldp = pools["dataplane"].cpu_lists()
    clcp = pools["controlplane"].cpu_lists()
    cldp["5,13"].add_task(1)
    cldp["6,14"].add_task(1789101112)
    clcp["3,11"].add_task(1234561231)

    assert helpers.execute(
        integration.kcm(),
        ["reconcile", "--conf-dir={}"
         .format(os.path.join(temp_dir, "reconcile"))],
        {proc.ENV_PROC_FS: helpers.procfs_dir("ok")}) == b"""{
  "reclaimedCpuLists": [
    {
      "cpus": "3,11",
      "pid": 1000,
      "pool": "controlplane"
    },
    {
      "cpus": "3,11",
      "pid": 1001,
      "pool": "controlplane"
    },
    {
      "cpus": "3,11",
      "pid": 1002,
      "pool": "controlplane"
    },
    {
      "cpus": "3,11",
      "pid": 1003,
      "pool": "controlplane"
    },
    {
      "cpus": "4,12",
      "pid": 2000,
      "pool": "dataplane"
    },
    {
      "cpus": "5,13",
      "pid": 2001,
      "pool": "dataplane"
    },
    {
      "cpus": "6,14",
      "pid": 2002,
      "pool": "dataplane"
    },
    {
      "cpus": "7,15",
      "pid": 2003,
      "pool": "dataplane"
    },
    {
      "cpus": "0-2,8-10",
      "pid": 3000,
      "pool": "infra"
    },
    {
      "cpus": "0-2,8-10",
      "pid": 3001,
      "pool": "infra"
    },
    {
      "cpus": "0-2,8-10",
      "pid": 3002,
      "pool": "infra"
    },
    {
      "cpus": "3,11",
      "pid": 1234561231,
      "pool": "controlplane"
    },
    {
      "cpus": "6,14",
      "pid": 1789101112,
      "pool": "dataplane"
    }
  ]
}
"""

    expected_output = """{
  "path": """ + "\"" + temp_dir + """/reconcile",
  "pools": {
    "controlplane": {
      "cpuLists": {
        "3,11": {
          "cpus": "3,11",
          "tasks": []
        }
      },
      "exclusive": false,
      "name": "controlplane"
    },
    "dataplane": {
      "cpuLists": {
        "4,12": {
          "cpus": "4,12",
          "tasks": []
        },
        "5,13": {
          "cpus": "5,13",
          "tasks": [
            1
          ]
        },
        "6,14": {
          "cpus": "6,14",
          "tasks": []
        },
        "7,15": {
          "cpus": "7,15",
          "tasks": []
        }
      },
      "exclusive": true,
      "name": "dataplane"
    },
    "infra": {
      "cpuLists": {
        "0-2,8-10": {
          "cpus": "0-2,8-10",
          "tasks": []
        }
      },
      "exclusive": false,
      "name": "infra"
    }
  }
}
"""

    actual_output = helpers.execute(
        integration.kcm(),
        ["describe", "--conf-dir={}"
            .format(os.path.join(temp_dir, "reconcile"))]
        )

    assert actual_output == expected_output.encode("UTF-8")

    helpers.execute(
        "rm",
        ["-rf",
            "{}".format(os.path.join(temp_dir, "reconcile"))]
    )
