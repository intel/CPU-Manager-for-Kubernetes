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
from intel import topology, config, init, proc
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock


# Returns a socket with 4 physical cores and HT enabled.
def quad_core():
    return topology.Socket(0, {
        0: topology.Core(0, {
            0: topology.CPU(0),
            4: topology.CPU(4)
        }),
        1: topology.Core(1, {
            1: topology.CPU(1),
            5: topology.CPU(5)
        }),
        2: topology.Core(2, {
            2: topology.CPU(2),
            6: topology.CPU(6)
        }),
        3: topology.Core(3, {
            3: topology.CPU(3),
            7: topology.CPU(7)
        })
    })


def quad_core_lscpu():
    return """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
2,2,0,0,,2,2,2,0
3,3,0,0,,3,3,3,0
4,0,0,0,,0,0,0,0
5,1,0,0,,1,1,1,0
6,2,0,0,,2,2,2,0
7,3,0,0,,3,3,3,0
"""


def test_init_success1(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = {0: quad_core()}

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        temp_dir = tempfile.mkdtemp()
        init.init(os.path.join(temp_dir, "init"), 2, 1)
        c = config.Config(os.path.join(temp_dir, "init"))
        pools = c.pools()
        assert len(pools) == 3
        assert "controlplane" in pools
        assert "dataplane" in pools
        assert "infra" in pools
        cldp = pools["dataplane"].cpu_lists()
        clcp = pools["controlplane"].cpu_lists()
        clinfra = pools["infra"].cpu_lists()
        assert not pools["controlplane"].exclusive()
        assert pools["dataplane"].exclusive()
        assert not pools["infra"].exclusive()
        assert "0,4" in cldp
        assert "1,5" in cldp
        assert "2,6" in clcp
        assert "3,7" in clinfra


def test_init_success1_isolcpus(monkeypatch):
    # Set the procfs environment variable. This test kernel command line
    # sets isolcpus to lcpu IDs from cores 1, 2 and 3.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("isolcpus"))

    with patch("intel.topology.lscpu",
               MagicMock(return_value=quad_core_lscpu())):
        temp_dir = tempfile.mkdtemp()
        init.init(os.path.join(temp_dir, "init"), 2, 1)
        c = config.Config(os.path.join(temp_dir, "init"))
        pools = c.pools()
        assert len(pools) == 3
        assert "controlplane" in pools
        assert "dataplane" in pools
        assert "infra" in pools
        cldp = pools["dataplane"].cpu_lists()
        clcp = pools["controlplane"].cpu_lists()
        clinfra = pools["infra"].cpu_lists()
        assert not pools["controlplane"].exclusive()
        assert pools["dataplane"].exclusive()
        assert not pools["infra"].exclusive()
        assert "1,5" in cldp
        assert "2,6" in cldp
        assert "3,7" in clcp
        assert "0,4" in clinfra


def test_init_success2(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = {0: quad_core()}

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        temp_dir = tempfile.mkdtemp()
        init.init(os.path.join(temp_dir, "init"), 1, 2)
        c = config.Config(os.path.join(temp_dir, "init"))
        pools = c.pools()
        assert len(pools) == 3
        assert "controlplane" in pools
        assert "dataplane" in pools
        assert "infra" in pools
        cldp = pools["dataplane"].cpu_lists()
        clcp = pools["controlplane"].cpu_lists()
        clinfra = pools["infra"].cpu_lists()
        assert not pools["controlplane"].exclusive()
        assert pools["dataplane"].exclusive()
        assert not pools["infra"].exclusive()
        assert "0,4" in cldp
        assert "1,5,2,6" in clcp
        assert "3,7" in clinfra


def test_init_success2_isolcpus(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("isolcpus"))

    with patch("intel.topology.lscpu",
               MagicMock(return_value=quad_core_lscpu())):
        temp_dir = tempfile.mkdtemp()
        init.init(os.path.join(temp_dir, "init"), 1, 2)
        c = config.Config(os.path.join(temp_dir, "init"))
        pools = c.pools()
        assert len(pools) == 3
        assert "controlplane" in pools
        assert "dataplane" in pools
        assert "infra" in pools
        cldp = pools["dataplane"].cpu_lists()
        clcp = pools["controlplane"].cpu_lists()
        clinfra = pools["infra"].cpu_lists()
        assert not pools["controlplane"].exclusive()
        assert pools["dataplane"].exclusive()
        assert not pools["infra"].exclusive()
        assert "1,5" in cldp
        assert "2,6,3,7" in clcp
        assert "0,4" in clinfra


def test_init_success3(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = {0: quad_core()}

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        temp_dir = tempfile.mkdtemp()
        init.init(os.path.join(temp_dir, "init"), 1, 1)
        c = config.Config(os.path.join(temp_dir, "init"))
        pools = c.pools()
        assert len(pools) == 3
        assert "controlplane" in pools
        assert "dataplane" in pools
        assert "infra" in pools
        cldp = pools["dataplane"].cpu_lists()
        clcp = pools["controlplane"].cpu_lists()
        clinfra = pools["infra"].cpu_lists()
        assert not pools["controlplane"].exclusive()
        assert pools["dataplane"].exclusive()
        assert not pools["infra"].exclusive()
        assert cldp["0,4"]
        assert clcp["1,5"]
        assert clinfra["2,6,3,7"]


def test_init_failure1(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = {
        0: topology.Socket(0, {
            0: topology.Core(0, {
                0: topology.CPU(0),
                2: topology.CPU(2)
            }),
            1: topology.Core(1, {
                1: topology.CPU(1),
                3: topology.CPU(3)
            })
        })
    }

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        temp_dir = tempfile.mkdtemp()
        with pytest.raises(RuntimeError):
            init.init(os.path.join(temp_dir, "init"), 2, 1)


def test_init_failure2(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = {
        0: topology.Socket(0, {
            0: topology.Core(0, {
                0: topology.CPU(0),
                4: topology.CPU(4)
            }),
            1: topology.Core(1, {
                1: topology.CPU(1),
                5: topology.CPU(5)
            })
        })
    }

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        temp_dir = tempfile.mkdtemp()
        with pytest.raises(RuntimeError) as err:
            init.init(os.path.join(temp_dir, "init"), 2, 1)
        assert err is not None
        expected_msg = "No more free cores left to assign for controlplane"
        assert err.value.args[0] == expected_msg


def test_init_failure3(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = {
        0: topology.Socket(0, {
            0: topology.Core(0, {
                0: topology.CPU(0),
                4: topology.CPU(4)
            }),
            1: topology.Core(1, {
                1: topology.CPU(1),
                5: topology.CPU(5)
            }),
            2: topology.Core(2, {
                2: topology.CPU(2),
                6: topology.CPU(6)
            })
        })
    }

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        temp_dir = tempfile.mkdtemp()
        with pytest.raises(RuntimeError) as err:
            init.init(os.path.join(temp_dir, "init"), 2, 1)
        assert err is not None
        expected_msg = "No more free cores left to assign for infra"
        assert err.value.args[0] == expected_msg
