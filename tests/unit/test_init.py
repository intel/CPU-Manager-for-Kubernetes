from intel import config, init
import collections
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock


def test_init_discover_topo():
    cpumap = init.discover_topo()
    assert len(cpumap) > 0


def test_init_parse_topo():
    input1 = """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
"""
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
"""
    cpumap = init.parse_topo(input1)
    assert len(cpumap) == 2
    assert "0" in cpumap
    assert "1" in cpumap

    cpumap = init.parse_topo(input2)
    assert len(cpumap) == 4
    assert "0" in cpumap
    assert "1" in cpumap
    assert "2" in cpumap
    assert "3" in cpumap
    assert cpumap["0"] == "0,4"
    assert cpumap["1"] == "1,5"
    assert cpumap["2"] == "2,6"
    assert cpumap["3"] == "3,7"


def test_init_success1():
    discover_topo_out = collections.OrderedDict()
    discover_topo_out["0"] = "0,4"
    discover_topo_out["1"] = "1,5"
    discover_topo_out["2"] = "2,6"
    discover_topo_out["3"] = "3,7"
    with patch('intel.init.discover_topo',
               MagicMock(return_value=discover_topo_out)):
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


def test_init_success2():
    discover_topo_out = collections.OrderedDict()
    discover_topo_out["0"] = "0,4"
    discover_topo_out["1"] = "1,5"
    discover_topo_out["2"] = "2,6"
    discover_topo_out["3"] = "3,7"
    with patch('intel.init.discover_topo',
               MagicMock(return_value=discover_topo_out)):
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
        assert "3,7" in cldp
        assert "2,6,1,5" in clcp
        assert "0,4" in clinfra


def test_init_success3():
    discover_topo_out = collections.OrderedDict()
    discover_topo_out["0"] = "0,4"
    discover_topo_out["1"] = "1,5"
    discover_topo_out["2"] = "2,6"
    discover_topo_out["3"] = "3,7"
    with patch('intel.init.discover_topo',
               MagicMock(return_value=discover_topo_out)):
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
        assert cldp["3,7"]
        assert clcp["2,6"]
        assert clinfra["0,4,1,5"]


def test_init_failure1():
    discover_topo_out = collections.OrderedDict()
    discover_topo_out["0"] = "0,4"
    with patch('intel.init.discover_topo',
               MagicMock(return_value=discover_topo_out)):
        temp_dir = tempfile.mkdtemp()
        with pytest.raises(KeyError) as err:
            init.init(os.path.join(temp_dir, "init"), 2, 1)
        expected_msg = "No more cpus left to assign for data plane"
        assert err.value.args[0] == expected_msg


def test_init_failure2():
    discover_topo_out = collections.OrderedDict()
    discover_topo_out["0"] = "0,4"
    discover_topo_out["1"] = "1,5"
    with patch('intel.init.discover_topo',
               MagicMock(return_value=discover_topo_out)):
        temp_dir = tempfile.mkdtemp()
        with pytest.raises(KeyError) as err:
            init.init(os.path.join(temp_dir, "init"), 2, 1)
        expected_msg = "No more cpus left to assign for control plane"
        assert err.value.args[0] == expected_msg


def test_init_failure3():
    discover_topo_out = collections.OrderedDict()
    discover_topo_out["0"] = "0,4"
    discover_topo_out["1"] = "1,5"
    discover_topo_out["2"] = "2,6"
    with patch('intel.init.discover_topo',
               MagicMock(return_value=discover_topo_out)):
        temp_dir = tempfile.mkdtemp()
        with pytest.raises(KeyError) as err:
            init.init(os.path.join(temp_dir, "init"), 2, 1)
        expected_msg = "No more cpus left to assign for infra"
        assert err.value.args[0] == expected_msg
