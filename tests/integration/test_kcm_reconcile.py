# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the "Software"), without modification,
# provided the following conditions are met:
#
# * Neither the name of Intel nor the names of its suppliers may be used to
#   endorse or promote products derived from this Software without specific
#   prior written permission.
# * No reverse engineering, decompilation, or disassembly of this Software
#   is permitted.
#
# Limited patent license.  Intel grants you a world-wide, royalty-free,
# non-exclusive license under patents it now or hereafter owns or controls to
# make, have made, use, import, offer to sell and sell ("Utilize") this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  "Third Party Programs" are the files
# listed in the "third-party-programs.txt" text file that is included with the
# Software and may include Intel programs under separate license terms. Third
# Party Programs, even if included with the distribution of the Materials, are
# governed by separate license terms and those license terms solely govern your
# use of those programs.
#
# DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
# DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS
# OR APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR
# DEATH.
#
# LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO
# INDEMNIFIY AND HOLD INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING
# FROM YOUR USE OR UNAUTHORIZED USE OF THE SOFTWARE.
#
# No support.  Intel may make changes to the Software, at any time without
# notice, and is not obligated to support, update or provide training for the
# Software.
#
# Termination. Intel may terminate your right to use the Software in the event
# of your breach of this Agreement and you fail to cure the breach within a
# reasonable period of time.
#
# Feedback.  Should you provide Intel with comments, modifications,
# corrections, enhancements or other input ("Feedback") related to the Software
# Intel will be free to use, disclose, reproduce, license or otherwise
# distribute or exploit the Feedback in its sole discretion without any
# obligations or restrictions of any kind, including without limitation,
# intellectual property rights or licensing obligations.
#
# Compliance with laws.  You agree to comply with all relevant laws and
# regulations governing your use, transfer, import or export (or prohibition
# thereof) of the Software.
#
# Governing law.  All disputes will be governed by the laws of the United
# States of America and the State of Delaware without reference to conflict of
# law principles and subject to the exclusive jurisdiction of the state or
# federal courts sitting in the State of Delaware, and each party agrees that
# it submits to the personal jurisdiction and venue of those courts and waives
# any objections. The United Nations Convention on Contracts for the
# International Sale of Goods (1980) is specifically excluded and will not
# apply to the Software.

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
  "mismatchedCpuMasks": [],
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
