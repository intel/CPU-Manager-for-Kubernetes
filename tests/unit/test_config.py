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

from intel import config, topology
from unittest.mock import patch, MagicMock
import yaml


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


def return_fake_platform():
    sockets = dict()
    sockets["0"] = topology.Socket("0")
    sockets["1"] = topology.Socket("1")

    core0 = topology.Core("0")
    core0.pool = "exclusive"
    cpu0 = topology.CPU("0")
    cpu0.isolated = True
    cpu3 = topology.CPU("3")
    cpu3.isolated = True
    core0.cpus["0"] = cpu0
    core0.cpus["3"] = cpu3
    sockets["0"].cores["0"] = core0

    core1 = topology.Core("1")
    core1.pool = "shared"
    cpu1 = topology.CPU("1")
    cpu1.isolated = True
    cpu4 = topology.CPU("4")
    cpu4.isolated = True
    core1.cpus["1"] = cpu1
    core1.cpus["4"] = cpu4
    sockets["0"].cores["1"] = core1

    core2 = topology.Core("2")
    core2.pool = "shared"
    cpu2 = topology.CPU("2")
    cpu5 = topology.CPU("5")
    core2.cpus["2"] = cpu2
    core2.cpus["5"] = cpu5
    sockets["0"].cores["2"] = core2

    return topology.Platform(sockets)


@patch('intel.k8s.get_config_map',
       MagicMock(return_value={'config': yaml.dump(FAKE_CONFIG)}))
def test_get_config():
    c = config.get_config("fake-name")
    assert len(c.pools.keys()) == 3
    assert len(c.pools["exclusive"].sockets.keys()) == 2
    assert len(c.pools["shared"].sockets.keys()) == 2
    assert len(c.pools["infra"].sockets.keys()) == 2
    assert len(c.pools["exclusive"].sockets["0"].core_lists.keys()) == 3
    assert len(c.pools["exclusive"].sockets["1"].core_lists.keys()) == 1
    assert len(c.pools["shared"].sockets["0"].core_lists.keys()) == 1
    assert "0,9" in c.pools["exclusive"].sockets["0"].core_lists.keys()
    assert "1,10" in c.pools["exclusive"].sockets["0"].core_lists.keys()
    assert "2,11" in c.pools["exclusive"].sockets["0"].core_lists.keys()
    assert "3,12" in c.pools["exclusive"].sockets["1"].core_lists.keys()
    assert "1001" in c.pools["exclusive"].sockets["0"].core_lists["0,9"].tasks
    assert "1002" in c.pools["exclusive"].sockets["0"].core_lists["1,10"].tasks
    assert "1003" in c.pools["exclusive"].sockets["0"].core_lists["2,11"].tasks
    assert "1004" in c.pools["exclusive"].sockets["1"].core_lists["3,12"].tasks


@patch('intel.k8s.get_config_map',
       MagicMock(return_value={'config': yaml.dump(FAKE_CONFIG)}))
@patch('intel.k8s.delete_config_map',
       MagicMock(return_value=''))
def test_config_class():
    c = config.Config("fake-name")
    c.lock()

    assert len(c.get_pools()) == 3
    assert "exclusive" in c.get_pools()
    assert "shared" in c.get_pools()
    assert "infra" in c.get_pools()

    assert c.get_pool("exclusive").name == "exclusive"
    assert c.get_pool("shared").name == "shared"
    assert c.get_pool("infra").name == "infra"
    assert c.get_pool("exclusive").exclusive
    assert not c.get_pool("shared").exclusive
    assert not c.get_pool("infra").exclusive

    c.add_pool(True, "fake-pool")
    assert "fake-pool" in c.get_pools()
    assert c.get_pool("fake-pool").name == "fake-pool"
    assert c.get_pool("fake-pool").exclusive


@patch('intel.k8s.get_config_map',
       MagicMock(return_value={'config': yaml.dump(FAKE_CONFIG)}))
@patch('intel.k8s.delete_config_map',
       MagicMock(return_value=''))
def test_pool_class():
    c = config.Config("fake-name")
    c.lock()

    p = c.get_pool("exclusive")
    assert p.name == "exclusive"
    assert p.is_exclusive()
    assert len(p.get_sockets()) == 2
    assert "0" in p.get_sockets()
    assert "1" in p.get_sockets()
    assert p.get_socket("0").socket_id == "0"

    assert len(p.get_core_lists()) == 4
    assert len(p.get_core_lists("0")) == 3
    assert len(p.get_core_lists("1")) == 1

    assert p.get_core_list("0,9", "0").core_id == "0,9"
    assert p.get_core_list("1,10").core_id == "1,10"
    assert p.get_core_list("3,12").core_id == "3,12"

    p.update_clist("0,9", "1004")
    assert "1001" in p.sockets["0"].core_lists["0,9"].tasks
    assert "1004" in p.sockets["0"].core_lists["0,9"].tasks

    p.remove_task("0,9", "1004")
    assert "1001" in p.sockets["0"].core_lists["0,9"].tasks
    assert "1004" not in p.sockets["0"].core_lists["0,9"].tasks


@patch('intel.k8s.get_config_map',
       MagicMock(return_value={'config': yaml.dump(FAKE_CONFIG)}))
@patch('intel.k8s.delete_config_map',
       MagicMock(return_value=''))
def test_socket_class():
    c = config.Config("fake-name")
    c.lock()

    s = c.get_pool("exclusive").get_socket("0")
    assert s.socket_id == "0"
    assert len(s.core_lists.keys()) == 3

    assert s.get_core_list("0,9").core_id == "0,9"
    assert len(s.get_core_lists()) == 3
    assert "0,9" in s.get_core_lists()
    assert "1,10" in s.get_core_lists()
    assert "2,11" in s.get_core_lists()

    s.add_core_list("fake-core")
    assert len(s.get_core_lists()) == 4
    assert "fake-core" in s.get_core_lists()


@patch('intel.k8s.get_config_map',
       MagicMock(return_value={'config': yaml.dump(FAKE_CONFIG)}))
@patch('intel.k8s.delete_config_map',
       MagicMock(return_value=''))
def test_core_list_class():
    c = config.Config("fake-name")
    c.lock()

    cl = c.get_pool("exclusive").get_core_list("0,9", "0")
    assert cl.core_id == "0,9"
    assert len(cl.tasks) == 1

    assert len(cl.get_tasks()) == 1
    assert "1001" in cl.get_tasks()

    cl.add_task("1005")
    assert len(cl.get_tasks()) == 2
    assert "1001" in cl.get_tasks()
    assert "1005" in cl.get_tasks()

    cl.remove_task("1005")
    assert len(cl.get_tasks()) == 1
    assert "1001" in cl.get_tasks()
    assert "1005" not in cl.get_tasks()


def test_update_configmap_exclusive():
    c = dict()

    c = config.update_configmap_exclusive("exclusive",
                                          return_fake_platform(), c)
    assert "exclusive" in c.keys()
    assert len(c["exclusive"].keys()) == 2
    assert "0" in c["exclusive"].keys()
    assert "1" in c["exclusive"].keys()
    assert len(c["exclusive"]["0"].keys()) == 1
    assert "0,3" in c["exclusive"]["0"].keys()
    assert len(c["exclusive"]["1"].keys()) == 0


def test_update_configmap_shared():
    c = dict()

    c = config.update_configmap_shared("shared", return_fake_platform(), c)
    assert "shared" in c.keys()
    assert len(c["shared"].keys()) == 2
    assert "0" in c["shared"].keys()
    assert "1" in c["shared"].keys()
    assert len(c["shared"]["0"].keys()) == 1
    assert "1,4,2,5" in c["shared"]["0"].keys()
    assert len(c["shared"]["1"].keys()) == 0


def test_set_configmap():
    c = config.build_config(FAKE_CONFIG)

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
        assert "0,9" in cl_exclusive
        assert "1,10" in cl_exclusive
        assert "2,11" in cl_exclusive
        assert "3,12" in cl_exclusive
        assert "4,13,5,14" in cl_shared
        assert "6,15,7,16,8,17" in cl_infra

    mock = MagicMock(name="mock")
    mock.side_effect = configmap_mock
    with patch('intel.k8s.create_config_map', new=mock):
        config.set_config(c, "fake-name")
