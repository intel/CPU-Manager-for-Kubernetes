from .. import helpers
from . import integration
from intel import config
from intel import proc
import os
import tempfile
import pytest
import subprocess


def test_kcm_reconcile():
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

    helpers.execute(
        integration.kcm(),
        ["reconcile", "--conf-dir={}"
         .format(os.path.join(temp_dir, "reconcile"))],
        {proc.ENV_PROC_FS: "/kcm/tests/data/proc/ok"}
    )

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


def test_kcm_reconcile_cpu_set_mismatch():
    temp_dir = tempfile.mkdtemp()
    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("cpuset_mismatch"),
         "{}".format(os.path.join(temp_dir, "reconcile"))]
    )

    with pytest.raises(subprocess.CalledProcessError):
        helpers.execute(
            integration.kcm(),
            ["reconcile", "--conf-dir={}"
             .format(os.path.join(temp_dir, "reconcile"))],
            {proc.ENV_PROC_FS: "/kcm/tests/data/proc/cpuset_mismatch"}
        )
