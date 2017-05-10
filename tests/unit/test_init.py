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
