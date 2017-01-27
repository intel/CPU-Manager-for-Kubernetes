# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the “Software”), without modification,
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
# make, have made, use, import, offer to sell and sell (“Utilize”) this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  “Third Party Programs” are the files
# listed in the “third-party-programs.txt” text file that is included with the
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
# corrections, enhancements or other input (“Feedback”) related to the Software
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

from intel import config, init
import os
# import pytest
import tempfile
from unittest.mock import patch, MagicMock


def test_lscpu():
    lines = init.lscpu()
    assert len(lines) > 0


def test_init_topology():
    input1 = """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
""".split("\n")

    input2 = """#The following is the parsable format, which can be fed to other
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
""".split("\n")

    sockets = init.topology(input1)
    assert len(sockets) == 1

    cpumap = sockets[0].cores
    assert len(cpumap) == 2
    assert 0 in cpumap
    assert 1 in cpumap

    sockets = init.topology(input2)
    assert len(sockets) == 1

    print(sockets[0])

    cpumap = sockets[0].cores
    assert len(cpumap) == 4
    assert 0 in cpumap
    assert 1 in cpumap
    assert 2 in cpumap
    assert 3 in cpumap
    assert cpumap[0].cpu_ids() == [0, 4]
    assert cpumap[1].cpu_ids() == [1, 5]
    assert cpumap[2].cpu_ids() == [2, 6]
    assert cpumap[3].cpu_ids() == [3, 7]


def test_init_success1():
    sockets = [init.Socket(0, {
        0: init.Core(0, {
            0: init.CPU(0),
            4: init.CPU(4)
        }),
        1: init.Core(1, {
            1: init.CPU(1),
            5: init.CPU(5)
        }),
        2: init.Core(2, {
            2: init.CPU(2),
            6: init.CPU(6)
        }),
        3: init.Core(3, {
            3: init.CPU(3),
            7: init.CPU(7)
        })
    })]

    with patch('intel.init.topology',
               MagicMock(return_value=sockets)):
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
        assert "3,7" in cldp
        assert "2,6" in cldp
        assert "1,5" in clcp
        assert "0,4" in clinfra
#
#
# def test_init_success2():
#     discover_topo_out = collections.OrderedDict()
#     discover_topo_out["0"] = "0,4"
#     discover_topo_out["1"] = "1,5"
#     discover_topo_out["2"] = "2,6"
#     discover_topo_out["3"] = "3,7"
#     with patch('intel.init.discover_topo',
#                MagicMock(return_value=discover_topo_out)):
#         temp_dir = tempfile.mkdtemp()
#         init.init(os.path.join(temp_dir, "init"), 1, 2)
#         c = config.Config(os.path.join(temp_dir, "init"))
#         pools = c.pools()
#         assert len(pools) == 3
#         assert "controlplane" in pools
#         assert "dataplane" in pools
#         assert "infra" in pools
#         cldp = pools["dataplane"].cpu_lists()
#         clcp = pools["controlplane"].cpu_lists()
#         clinfra = pools["infra"].cpu_lists()
#         assert not pools["controlplane"].exclusive()
#         assert pools["dataplane"].exclusive()
#         assert not pools["infra"].exclusive()
#         assert "3,7" in cldp
#         assert "2,6,1,5" in clcp
#         assert "0,4" in clinfra
#
#
# def test_init_success3():
#     discover_topo_out = collections.OrderedDict()
#     discover_topo_out["0"] = "0,4"
#     discover_topo_out["1"] = "1,5"
#     discover_topo_out["2"] = "2,6"
#     discover_topo_out["3"] = "3,7"
#     with patch('intel.init.discover_topo',
#                MagicMock(return_value=discover_topo_out)):
#         temp_dir = tempfile.mkdtemp()
#         init.init(os.path.join(temp_dir, "init"), 1, 1)
#         c = config.Config(os.path.join(temp_dir, "init"))
#         pools = c.pools()
#         assert len(pools) == 3
#         assert "controlplane" in pools
#         assert "dataplane" in pools
#         assert "infra" in pools
#         cldp = pools["dataplane"].cpu_lists()
#         clcp = pools["controlplane"].cpu_lists()
#         clinfra = pools["infra"].cpu_lists()
#         assert not pools["controlplane"].exclusive()
#         assert pools["dataplane"].exclusive()
#         assert not pools["infra"].exclusive()
#         assert cldp["3,7"]
#         assert clcp["2,6"]
#         assert clinfra["0,4,1,5"]
#
#
# def test_init_failure1():
#     discover_topo_out = collections.OrderedDict()
#     discover_topo_out["0"] = "0,4"
#     with patch('intel.init.discover_topo',
#                MagicMock(return_value=discover_topo_out)):
#         temp_dir = tempfile.mkdtemp()
#         with pytest.raises(KeyError) as err:
#             init.init(os.path.join(temp_dir, "init"), 2, 1)
#         expected_msg = "No more cpus left to assign for data plane"
#         assert err.value.args[0] == expected_msg
#
#
# def test_init_failure2():
#     discover_topo_out = collections.OrderedDict()
#     discover_topo_out["0"] = "0,4"
#     discover_topo_out["1"] = "1,5"
#     with patch('intel.init.discover_topo',
#                MagicMock(return_value=discover_topo_out)):
#         temp_dir = tempfile.mkdtemp()
#         with pytest.raises(KeyError) as err:
#             init.init(os.path.join(temp_dir, "init"), 2, 1)
#         expected_msg = "No more cpus left to assign for control plane"
#         assert err.value.args[0] == expected_msg
#
#
# def test_init_failure3():
#     discover_topo_out = collections.OrderedDict()
#     discover_topo_out["0"] = "0,4"
#     discover_topo_out["1"] = "1,5"
#     discover_topo_out["2"] = "2,6"
#     with patch('intel.init.discover_topo',
#                MagicMock(return_value=discover_topo_out)):
#         temp_dir = tempfile.mkdtemp()
#         with pytest.raises(KeyError) as err:
#             init.init(os.path.join(temp_dir, "init"), 2, 1)
#         expected_msg = "No more cpus left to assign for infra"
#         assert err.value.args[0] == expected_msg
