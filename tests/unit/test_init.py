
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

from .. import helpers
from intel import init, topology, proc, config
from unittest.mock import patch, MagicMock
import pytest
import yaml

TOPOLOGY_PARSE = 'intel.topology.parse'
TOPOLOGY_ISCPU = "intel.topology.lscpu"

TOPOLOGY_PARSE = 'intel.topology.parse'
TOPOLOGY_ISCPU = "intel.topology.lscpu"


def return_quad_core():
    sockets = topology.Socket(0, {
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

    return topology.Platform({0: sockets})


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


def eight_core_lscpu():
    return """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
2,2,0,0,,2,2,2,0
3,3,0,0,,3,3,3,0
4,4,0,0,,4,4,4,0
5,5,0,0,,5,5,5,0
6,6,0,0,,6,6,6,0
7,7,0,0,,7,7,7,0
8,0,0,0,,0,0,0,0
9,1,0,0,,1,1,1,0
10,2,0,0,,2,2,2,0
11,3,0,0,,3,3,3,0
12,4,0,0,,4,4,4,0
13,5,0,0,,5,5,5,0
14,6,0,0,,6,6,6,0
15,7,0,0,,7,7,7,0
"""


@patch('intel.topology.parse', MagicMock(return_value=return_quad_core()))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_init_success1(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))
    monkeypatch.setenv("HOSTNAME", "fake-pod")

    def configmap_mock(unused1, configmap, unused2):
        c = yaml.safe_load(configmap.data["config"])
        conf = config.build_config(c)
        pools = conf.get_pools()
        assert len(pools) == 3
        assert "exclusive" in pools
        assert "shared" in pools
        assert "infra" in pools
        exl_pool = conf.get_pool("exclusive")
        cl_exclusive = [cl.core_id for cl in exl_pool.get_core_lists()]
        sha_pool = conf.get_pool("shared")
        cl_shared = [cl.core_id for cl in sha_pool.get_core_lists()]
        inf_pool = conf.get_pool("infra")
        cl_infra = [cl.core_id for cl in inf_pool.get_core_lists()]
        assert exl_pool.is_exclusive()
        assert not sha_pool.is_exclusive()
        assert not inf_pool.is_exclusive()
        assert "0,4" in cl_exclusive
        assert "1,5" in cl_exclusive
        assert "2,6" in cl_shared
        assert "3,7" in cl_infra

    mock = MagicMock(name="mock")
    mock.side_effect = configmap_mock
    with patch('intel.k8s.create_config_map', new=mock):
        init.init(2, 1, "vertical", "vertical", "-1")


@patch('intel.topology.lscpu', MagicMock(return_value=quad_core_lscpu()))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_init_success1_isolcpus(monkeypatch):
    # Set the procfs environment variable. This test kernel command line
    # sets isolcpus to lcpu IDs from cores 1, 2 and 3.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("isolcpus"))
    monkeypatch.setenv("HOSTNAME", "fake-pod")

    def configmap_mock(unused1, configmap, unused2):
        c = yaml.load(configmap.data["config"], Loader=yaml.FullLoader)
        conf = config.build_config(c)
        pools = conf.get_pools()
        assert len(pools) == 3
        assert "exclusive" in pools
        assert "shared" in pools
        assert "infra" in pools
        exl_pool = conf.get_pool("exclusive")
        cl_exclusive = [cl.core_id for cl in exl_pool.get_core_lists()]
        sha_pool = conf.get_pool("shared")
        cl_shared = [cl.core_id for cl in sha_pool.get_core_lists()]
        inf_pool = conf.get_pool("infra")
        cl_infra = [cl.core_id for cl in inf_pool.get_core_lists()]
        assert exl_pool.is_exclusive()
        assert not sha_pool.is_exclusive()
        assert not inf_pool.is_exclusive()
        assert "1,5" in cl_exclusive
        assert "2,6" in cl_exclusive
        assert "3,7" in cl_shared
        assert "0,4" in cl_infra

    mock = MagicMock(name="mock")
    mock.side_effect = configmap_mock
    with patch('intel.k8s.create_config_map', new=mock):
        init.init(2, 1, "vertical", "vertical", "-1")


@patch('intel.topology.parse', MagicMock(return_value=return_quad_core()))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_init_success2(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))
    monkeypatch.setenv("HOSTNAME", "fake-pod")

    def configmap_mock(unused1, configmap, unused2):
        c = yaml.load(configmap.data["config"], Loader=yaml.FullLoader)
        conf = config.build_config(c)
        pools = conf.get_pools()
        assert len(pools) == 3
        assert "exclusive" in pools
        assert "shared" in pools
        assert "infra" in pools
        exl_pool = conf.get_pool("exclusive")
        cl_exclusive = [cl.core_id for cl in exl_pool.get_core_lists()]
        sha_pool = conf.get_pool("shared")
        cl_shared = [cl.core_id for cl in sha_pool.get_core_lists()]
        inf_pool = conf.get_pool("infra")
        cl_infra = [cl.core_id for cl in inf_pool.get_core_lists()]
        assert exl_pool.is_exclusive()
        assert not sha_pool.is_exclusive()
        assert not inf_pool.is_exclusive()
        assert "0,4" in cl_exclusive
        assert "1,5,2,6" in cl_shared
        assert "3,7" in cl_infra

    mock = MagicMock(name="mock")
    mock.side_effect = configmap_mock
    with patch('intel.k8s.create_config_map', new=mock):
        init.init(1, 2, "vertical", "vertical", "-1")


@patch('intel.topology.lscpu', MagicMock(return_value=quad_core_lscpu()))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_init_success_isolcpus2(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("isolcpus"))
    monkeypatch.setenv("HOSTNAME", "fake-pod")

    def configmap_mock(unused1, configmap, unused2):
        c = yaml.load(configmap.data["config"], Loader=yaml.FullLoader)
        conf = config.build_config(c)
        pools = conf.get_pools()
        assert len(pools) == 3
        assert "exclusive" in pools
        assert "shared" in pools
        assert "infra" in pools
        exl_pool = conf.get_pool("exclusive")
        cl_exclusive = [cl.core_id for cl in exl_pool.get_core_lists()]
        sha_pool = conf.get_pool("shared")
        cl_shared = [cl.core_id for cl in sha_pool.get_core_lists()]
        inf_pool = conf.get_pool("infra")
        cl_infra = [cl.core_id for cl in inf_pool.get_core_lists()]
        assert exl_pool.is_exclusive()
        assert not sha_pool.is_exclusive()
        assert not inf_pool.is_exclusive()
        assert "1,5" in cl_exclusive
        assert "2,6,3,7" in cl_shared
        assert "0,4" in cl_infra

    mock = MagicMock(name="mock")
    mock.side_effect = configmap_mock
    with patch('intel.k8s.create_config_map', new=mock):
        init.init(1, 2, "vertical", "vertical", "-1")


@patch('intel.topology.parse', MagicMock(return_value=return_quad_core()))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_init_success3(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))
    monkeypatch.setenv("HOSTNAME", "fake-pod")

    def configmap_mock(unused1, configmap, unused2):
        c = yaml.load(configmap.data["config"], Loader=yaml.FullLoader)
        conf = config.build_config(c)
        pools = conf.get_pools()
        assert len(pools) == 3
        assert "exclusive" in pools
        assert "shared" in pools
        assert "infra" in pools
        exl_pool = conf.get_pool("exclusive")
        cl_exclusive = [cl.core_id for cl in exl_pool.get_core_lists()]
        sha_pool = conf.get_pool("shared")
        cl_shared = [cl.core_id for cl in sha_pool.get_core_lists()]
        inf_pool = conf.get_pool("infra")
        cl_infra = [cl.core_id for cl in inf_pool.get_core_lists()]
        assert exl_pool.is_exclusive()
        assert not sha_pool.is_exclusive()
        assert not inf_pool.is_exclusive()
        assert "0,4" in cl_exclusive
        assert "1,5" in cl_shared
        assert "2,6,3,7" in cl_infra

    mock = MagicMock(name="mock")
    mock.side_effect = configmap_mock
    with patch('intel.k8s.create_config_map', new=mock):
        init.init(1, 1, "vertical", "vertical", "-1")


@patch('intel.topology.lscpu', MagicMock(return_value=eight_core_lscpu()))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_init_success_excl_non_isolcpus1(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS,
                       helpers.procfs_dir("exclusive_non_isolcpus"))
    monkeypatch.setenv("HOSTNAME", "fake-pod")

    def configmap_mock(unused1, configmap, unused2):
        c = yaml.load(configmap.data["config"], Loader=yaml.FullLoader)
        conf = config.build_config(c)
        pools = conf.get_pools()
        assert len(pools) == 4
        assert "exclusive" in pools
        assert "shared" in pools
        assert "infra" in pools
        assert "exclusive-non-isolcpus" in pools
        exl_pool = conf.get_pool("exclusive")
        cl_exclusive = [cl.core_id for cl in exl_pool.get_core_lists()]
        sha_pool = conf.get_pool("shared")
        cl_shared = [cl.core_id for cl in sha_pool.get_core_lists()]
        inf_pool = conf.get_pool("infra")
        cl_infra = [cl.core_id for cl in inf_pool.get_core_lists()]
        exl_non_pool = conf.get_pool("exclusive-non-isolcpus")
        cl_excl_non = [cl.core_id for cl in exl_non_pool.get_core_lists()]
        assert exl_pool.is_exclusive()
        assert not sha_pool.is_exclusive()
        assert not inf_pool.is_exclusive()
        assert exl_non_pool.is_exclusive()
        assert "1,9" in cl_exclusive
        assert "2,10" in cl_shared
        assert "3,11,4,12,5,13,6,14,7,15" in cl_infra
        assert "0,8" in cl_excl_non

    mock = MagicMock(name="mock")
    mock.side_effect = configmap_mock
    with patch('intel.k8s.create_config_map', new=mock):
        init.init(1, 1, "vertical", "vertical", "0")


@patch('intel.topology.lscpu', MagicMock(return_value=eight_core_lscpu()))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_init_success_excl_non_isolcpus2(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS,
                       helpers.procfs_dir("exclusive_non_isolcpus"))
    monkeypatch.setenv("HOSTNAME", "fake-pod")

    def configmap_mock(unused1, configmap, unused2):
        c = yaml.load(configmap.data["config"], Loader=yaml.FullLoader)
        conf = config.build_config(c)
        pools = conf.get_pools()
        assert len(pools) == 4
        assert "exclusive" in pools
        assert "shared" in pools
        assert "infra" in pools
        assert "exclusive-non-isolcpus" in pools
        exl_pool = conf.get_pool("exclusive")
        cl_exclusive = [cl.core_id for cl in exl_pool.get_core_lists()]
        sha_pool = conf.get_pool("shared")
        cl_shared = [cl.core_id for cl in sha_pool.get_core_lists()]
        inf_pool = conf.get_pool("infra")
        cl_infra = [cl.core_id for cl in inf_pool.get_core_lists()]
        exl_non_pool = conf.get_pool("exclusive-non-isolcpus")
        cl_excl_non = [cl.core_id for cl in exl_non_pool.get_core_lists()]
        assert exl_pool.is_exclusive()
        assert not sha_pool.is_exclusive()
        assert not inf_pool.is_exclusive()
        assert exl_non_pool.is_exclusive()
        assert "1,9" in cl_exclusive
        assert "2,10" in cl_shared
        assert "6,14,7,15" in cl_infra
        assert "0,8" in cl_excl_non
        assert "3,11" in cl_excl_non
        assert "4,12" in cl_excl_non
        assert "5,13" in cl_excl_non

    mock = MagicMock(name="mock")
    mock.side_effect = configmap_mock
    with patch('intel.k8s.create_config_map', new=mock):
        init.init(1, 1, "vertical", "vertical", "0,3-5")


def test_init_success_excl_non_isolcpus1(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS,
                       helpers.procfs_dir("exclusive_non_isolcpus"))

    with patch(TOPOLOGY_ISCPU,
               MagicMock(return_value=eight_core_lscpu())):
        temp_dir = tempfile.mkdtemp()
        init.init(os.path.join(temp_dir, "init"), 1, 1,
                  "vertical", "vertical", "0")
        c = config.Config(os.path.join(temp_dir, "init"))
        pools = c.pools()
        assert len(pools) == 4
        assert "shared" in pools
        assert "exclusive" in pools
        assert "infra" in pools
        assert "exclusive-non-isolcpus" in pools
        cl_exclusive = pools["exclusive"].cpu_lists()
        cl_shared = pools["shared"].cpu_lists()
        cl_infra = pools["infra"].cpu_lists()
        cl_excl_non_isolcpus = pools["exclusive-non-isolcpus"].cpu_lists()
        assert not pools["shared"].exclusive()
        assert pools["exclusive"].exclusive()
        assert not pools["infra"].exclusive()
        assert pools["exclusive-non-isolcpus"].exclusive()
        assert cl_exclusive["1,9"]
        assert cl_shared["2,10"]
        assert cl_excl_non_isolcpus["0,8"]
        assert cl_infra["3,11,4,12,5,13,6,14,7,15"]


def test_init_success_excl_non_isolcpus2(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS,
                       helpers.procfs_dir("exclusive_non_isolcpus"))

    with patch(TOPOLOGY_ISCPU,
               MagicMock(return_value=eight_core_lscpu())):
        temp_dir = tempfile.mkdtemp()
        init.init(os.path.join(temp_dir, "init"), 1, 1,
                  "vertical", "vertical", "0,3-5")
        c = config.Config(os.path.join(temp_dir, "init"))
        pools = c.pools()
        assert len(pools) == 4
        assert "shared" in pools
        assert "exclusive" in pools
        assert "infra" in pools
        assert "exclusive-non-isolcpus" in pools
        cl_exclusive = pools["exclusive"].cpu_lists()
        cl_shared = pools["shared"].cpu_lists()
        cl_infra = pools["infra"].cpu_lists()
        cl_excl_non_isolcpus = pools["exclusive-non-isolcpus"].cpu_lists()
        assert not pools["shared"].exclusive()
        assert pools["exclusive"].exclusive()
        assert not pools["infra"].exclusive()
        assert pools["exclusive-non-isolcpus"].exclusive()
        assert cl_exclusive["1,9"]
        assert cl_shared["2,10"]
        assert "0,8" in cl_excl_non_isolcpus
        assert "3,11" in cl_excl_non_isolcpus
        assert "4,12" in cl_excl_non_isolcpus
        assert "5,13" in cl_excl_non_isolcpus
        assert cl_infra["6,14,7,15"]


def test_init_failure1(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = topology.Platform({
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
    })

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        with pytest.raises(RuntimeError):
            init.init(2, 1, "vertical",
                      "vertical", "-1")


def test_init_failure2(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = topology.Platform({
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
    })

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        with pytest.raises(RuntimeError) as err:
            init.init(2, 1, "vertical",
                      "vertical", "-1")
        assert err is not None
        expected_msg = "No more free cores left to assign for shared"
        assert err.value.args[0] == expected_msg


def test_init_failure3(monkeypatch):
    # Set the procfs environment variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))

    sockets = topology.Platform({
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
    })

    with patch('intel.topology.parse', MagicMock(return_value=sockets)):
        with pytest.raises(RuntimeError) as err:
            init.init(2, 1, "vertical",
                      "vertical", "-1")
        assert err is not None
        expected_msg = "No more free cores left to assign for infra"
        assert err.value.args[0] == expected_msg


@patch('intel.topology.lscpu', MagicMock(return_value=eight_core_lscpu()))
def test_init_failure_excl_non_isolcpus1(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS,
                       helpers.procfs_dir("exclusive_non_isolcpus"))

    with pytest.raises(RuntimeError) as err:
        init.init(1, 1,
                  "vertical", "vertical", "1,2")
    assert err is not None
    expected_msg = "Core(s) have already been assigned to pool(s): [1, 2]"\
                   ", cannot add them to exclusive-non-isolcpus pool"
    assert err.value.args[0] == expected_msg


@patch('intel.topology.lscpu', MagicMock(return_value=eight_core_lscpu()))
def test_init_failure_excl_non_isolcpus2(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS,
                       helpers.procfs_dir("exclusive_non_isolcpus"))

    with pytest.raises(RuntimeError) as err:
        init.init(1, 1,
                  "vertical", "vertical", "0,1")
    assert err is not None
    expected_msg = "Core(s) have already been assigned to pool(s): [1]"\
                   ", cannot add them to exclusive-non-isolcpus pool"
    assert err.value.args[0] == expected_msg


@patch('intel.topology.lscpu', MagicMock(return_value=eight_core_lscpu()))
def test_init_failure_excl_non_isolcpus3(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS,
                       helpers.procfs_dir("exclusive_non_isolcpus"))

    with pytest.raises(RuntimeError) as err:
        init.init(1, 1,
                  "vertical", "vertical", "-2")
    assert err is not None
    expected_msg = "Invalid core ID: -2"
    assert err.value.args[0] == expected_msg


@patch('intel.topology.lscpu', MagicMock(return_value=eight_core_lscpu()))
def test_init_failure_excl_non_isolcpus4(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS,
                       helpers.procfs_dir("exclusive_non_isolcpus"))

    with pytest.raises(RuntimeError) as err:
        init.init(1, 1,
                  "vertical", "vertical", "20,21")
    assert err is not None
    expected_msg = "Following physical cores not on system: [20, 21];"\
                   " you may be including logical CPUs of each core"
    assert err.value.args[0] == expected_msg


@patch('intel.topology.lscpu', MagicMock(return_value=quad_core_lscpu()))
def test_init_failure_excl_non_isolcpus5(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("isolcpus"))

    with pytest.raises(RuntimeError) as err:
        init.init(1, 1,
                  "vertical", "vertical", "3")
    assert err is not None
    expected_msg = "Isolated cores [3] cannot be placed in"\
                   " exclusive-non-isolcpus pool"
    assert err.value.args[0] == expected_msg


def test_init_check_hugepages_error(caplog):
    with patch('builtins.open', side_effect=FileNotFoundError):
        init.check_hugepages()
    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == ("meminfo file '%s' not found: skipping "
                                   "huge pages check" % "/proc/meminfo")
