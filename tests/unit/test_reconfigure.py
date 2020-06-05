from .. import helpers
from intel import reconfigure, proc, topology, config
from kubernetes.client.rest import ApiException
import pytest
import shutil
import tempfile
from unittest.mock import patch, MagicMock


class MockConfig():

    def __init__(self):
        self.assert_hostname = False

    def connect_get_namespaced_pod_exec(self):
        return ""


correct_dict_config = {
                 "exclusive": {
                              "0": {
                                   "4,12": ["2000"],
                                   "5,13": ["2001"],
                                   "6,14": ["2002"],
                                   "7,15": ["2003"]
                                   }
                              },
                 "shared": {
                              "0": {
                                   "3,11": ["1000", "1001", "1002", "1003"]
                                   }
                              },
                 "infra": {
                              "0": {
                                   "0-2,8-10": ["3000", "3001", "3002"]
                                   }
                              }
                 }

correct_str_config = "exclusive|0$4,12:2000&5,13:2001&6,14:2002&7,15:2003#" +\
                      "shared|0$3,11:1000,1001,1002,1003#" +\
                      "infra|0$0-2,8-10:3000,3001,3002"

config_before = {
                 "exclusive": {
                              "0": {
                                   "3,11": [""],
                                   "4,12": ["2001"],
                                   "5,13": ["2002"]
                                   }
                              },
                 "shared": {
                              "0": {
                                   "6,14,7,15": ["1000", "1001", "1002",
                                                 "1003"]
                                   }
                              },
                 "infra": {
                              "0": {
                                   "0,8,1,9,2,10": ["3000", "3001", "3002"]
                                   }
                              }
                 }

config_after = {
                 "exclusive": {
                              "0": {
                                   "3,11": ["2001"],
                                   "4,12": ["2002"],
                                   }
                              },
                 "shared": {
                              "0": {
                                   "5,13": ["1000", "1001", "1002", "1003"]
                                   }
                              },
                 "infra": {
                              "0": {
                                   "0,8,1,9,2,10": ["3000", "3001", "3002"]
                                   }
                              }
                 }

non_isols_config = {
                 "exclusive": {
                              "0": {
                                   "4,12": ["2000"],
                                   "5,13": ["2001"],
                                   "6,14": ["2002"],
                                   "7,15": ["2003"]
                                   }
                              },
                 "shared": {
                              "0": {
                                   "3,11": ["1000", "1001", "1002", "1003"]
                                   }
                              },
                 "infra": {
                              "0": {
                                   "0-2,8-10": ["3000", "3001", "3002"]
                                   }
                              },
                 "exclusive-non-isolcpus": {
                              "0": {
                                   "20,21": ["6001"],
                                   "22,23": ["6002"]
                                   }
                              }
                 }


returned_pods = {
                "items": [
                    {
                        "status": {
                            "conditions": [
                                {"reason": "Running"}
                            ]
                        },
                        "metadata": {
                            "name": "fake-node1",
                            "namespace": "fake-namespace"
                        },
                        "spec": {
                            "containers": [{"name": "fake-container"}]
                        }
                    },
                    {
                        "status": {
                            "conditions": [{"reason": "PodCompleted"}]
                        },
                        "metadata": {
                            "name": "fake-node2",
                            "namespace": "fake-namespace"
                        },
                        "spec": {
                            "containers": [{"name": "fake-container"}]
                        }
                    },
                    {
                        "status": {
                            "conditions": [{"reason": "Running"}]
                        },
                        "metadata": {
                            "name": "fake-node3",
                            "namespace": "fake-namespace"
                        },
                        "spec": {
                            "containers": [
                                {"name": "fake-container1"},
                                {"name": "fake-container2"}
                            ]
                        }
                    }
                ]
            }


single_pod = [{
            "name": "fake-name",
            "namespace": "fake-namespace",
            "containers": ["container"]
        }]


def get_mock_config():
    return MockConfig()


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


def lscpu_cores():
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


def test_build_config_map_pass():
    path = helpers.conf_dir('ok')
    config_map = reconfigure.build_config_map(path)
    assert config_map == correct_dict_config


def test_build_config_map_fail(caplog):
    path = helpers.conf_dir('fail')
    with pytest.raises(SystemExit) as err:
        reconfigure.build_config_map(path)

    caplog_tuple = caplog.record_tuples
    expected_msg = "Error while reading configuration"\
                   " at /cmk/tests/data/config/fail/pools, incorrect"\
                   " pool incorrect_pool_name"
    assert caplog_tuple[-1][2] == expected_msg
    assert err is not None
    assert err.value.args[0] == 1


def test_reconfigure_directory(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("reconf_isolcpus"))

    with patch('intel.topology.lscpu', MagicMock(return_value=lscpu_cores())):
        temp_dir = tempfile.mkdtemp()
        temp_dir_root = temp_dir+"reconfigure"
        shutil.copytree(helpers.conf_dir('reconf_before'), temp_dir_root)
        c = config.Config(temp_dir_root)
        reconfigure.reconfigure_directory(c, config_after, temp_dir_root, 2, 1,
                                          "vertical", "vertical", "-1")
        new_config = reconfigure.build_config_map(temp_dir_root)
        assert new_config == config_after


def test_check_processes_success1():
    err = reconfigure.check_processes(correct_dict_config, "exclusive", 4)
    assert err == ""


def test_check_processes_success2():
    err = reconfigure.check_processes(correct_dict_config, "exclusive", 5)
    assert err == ""


def test_check_processes_success_non_isolcpus1():
    num_excl_non_isols = len(topology.parse_cpus_str("1,2".split(",")))
    err = reconfigure.check_processes(non_isols_config,
                                      "exclusive-non-isolcpus",
                                      num_excl_non_isols)

    assert err == ""


def test_check_processes_success_non_isolcpus2():
    num_excl_non_isols = len(topology.parse_cpus_str("1,2,3".split(",")))
    err = reconfigure.check_processes(non_isols_config,
                                      "exclusive-non-isolcpus",
                                      num_excl_non_isols)

    assert err == ""


def test_check_processes_failure():
    err = reconfigure.check_processes(correct_dict_config, "exclusive", 2)
    assert err != ""
    assert err == "Not enough exclusive cores in"\
                  " new configuration: 4 processes, 2 cores"


def test_check_processes_failure_non_isolcpus1():
    num_excl_non_isols = len(topology.parse_cpus_str("1".split(",")))
    err = reconfigure.check_processes(non_isols_config,
                                      "exclusive-non-isolcpus",
                                      num_excl_non_isols)

    assert err != ""
    assert err == "Not enough exclusive-non-isolcpus cores in"\
                  " new configuration: 2 processes, 1 cores"


def test_check_processes_failure_non_isolcpus2():
    num_excl_non_isols = len(topology.parse_cpus_str("-1".split(",")))
    err = reconfigure.check_processes(non_isols_config,
                                      "exclusive-non-isolcpus",
                                      num_excl_non_isols)

    assert err != ""
    assert err == "Not enough exclusive-non-isolcpus cores in"\
                  " new configuration: 2 processes, 0 cores"


def test_check_processes_non_isolcpus_not_active(caplog):
    err = reconfigure.check_processes(correct_dict_config,
                                      "exclusive-non-isolcpus", "-1")
    assert err == ""
    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == "exclusive-non-isolcpus pool not"\
                                  " detected, continuing reconfiguration"


def test_check_processes_fake_pool(caplog):
    err = reconfigure.check_processes(correct_dict_config, "fake-pool", "2")
    assert err == ""
    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == "fake-pool pool not detected,"\
                                  " continuing reconfiguration"


@patch('intel.reconfigure.set_config_map',
       MagicMock(return_value=correct_dict_config))
def test_reconfigure_failure1(caplog):
    with patch('intel.reconfigure.build_config_map',
               MagicMock(return_value=correct_dict_config)):
        with pytest.raises(SystemExit) as err:
            reconfigure.reconfigure("fake-node", 2, 2, "-1", "/etc/cmk",
                                    "packed", "packed", "/opt/bin",
                                    "fake-namespace")

        caplog_tuple = caplog.record_tuples
        expected_msg = "Error while checking processes: "\
                       "Not enough exclusive cores in new"\
                       " configuration: 4 processes, 2 cores"
        assert caplog_tuple[-1][2] == expected_msg
        assert err is not None
        assert err.value.args[0] == 1


@patch('intel.reconfigure.set_config_map',
       MagicMock(return_value=non_isols_config))
def test_reconfigure_failure2(caplog):
    with patch('intel.reconfigure.build_config_map',
               MagicMock(return_value=non_isols_config)):
        with pytest.raises(SystemExit) as err:
            reconfigure.reconfigure("fake-node", 4, 1, "-1", "etc/cmk",
                                    "packed", "packed", "/opt/bin",
                                    "fake-namespace")

        caplog_tuple = caplog.record_tuples
        expected_msg = "Error while checking processes: "\
                       "Not enough exclusive-non-isolcpus cores in new"\
                       " configuration: 2 processes, 0 cores"
        assert caplog_tuple[-1][2] == expected_msg
        assert err is not None
        assert err.value.args[0] == 1


@patch('intel.reconfigure.set_config_map',
       MagicMock(return_value=non_isols_config))
def test_reconfigure_failure3(caplog):
    with patch('intel.reconfigure.build_config_map',
               MagicMock(return_value=non_isols_config)):
        with pytest.raises(SystemExit) as err:
            reconfigure.reconfigure("fake-node", 4, 1, "1", "etc/cmk",
                                    "packed", "packed", "/opt/bin",
                                    "fake-namespace")

        caplog_tuple = caplog.record_tuples
        expected_msg = "Error while checking processes: "\
                       "Not enough exclusive-non-isolcpus cores in new"\
                       " configuration: 2 processes, 1 cores"
        assert caplog_tuple[-1][2] == expected_msg
        assert err is not None
        assert err.value.args[0] == 1


@patch('os.environ', MagicMock(return_value="host_pod"))
def test_get_pods():
    with patch('intel.k8s.get_pod_list',
               MagicMock(return_value=returned_pods)):
        all_pods = reconfigure.get_pods()

    assert len(all_pods) == 2
    assert all_pods[0]["name"] == "fake-node1"
    assert all_pods[0]["namespace"] == "fake-namespace"
    assert len(all_pods[0]["containers"]) == 1
    assert all_pods[0]["containers"][0] == "fake-container"

    assert all_pods[1]["name"] == "fake-node3"
    assert all_pods[1]["namespace"] == "fake-namespace"
    assert len(all_pods[1]["containers"]) == 2
    assert all_pods[1]["containers"][0] == "fake-container1"
    assert all_pods[1]["containers"][1] == "fake-container2"


@patch('intel.k8s.client_from_config', MagicMock(return_value=""))
@patch('kubernetes.client.Configuration',
       MagicMock(return_value=get_mock_config()))
@patch('kubernetes.client.Configuration.set_default',
       MagicMock(return_value=""))
@patch('kubernetes.client.CoreV1Api',
       MagicMock(return_value=get_mock_config()))
def test_execute_reconfigure_failure(caplog):
    with patch('kubernetes.stream.stream') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        reconfigure.execute_reconfigure("/opt/bin", "fake-node", single_pod,
                                        "fake-namespace")

    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == "Error occured while executing command"\
                                  " in pod: Fake Reason"


@patch('intel.reconfigure.build_config_map',
       MagicMock(return_value=correct_dict_config))
@patch('kubernetes.client.V1ConfigMap',
       MagicMock(return_value=""))
@patch('intel.clusterinit.update_configmap',
       MagicMock(return_value=""))
def test_set_config_mapi_failure(caplog):
    with patch('intel.k8s.create_config_map') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        with pytest.raises(SystemExit) as err:
            reconfigure.set_config_map("fake-name", "fake-namespace",
                                       "/etc/cmk")

        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-2][2] == "Exception when creating config map"\
                                      " fake-name"
        assert caplog_tuple[-1][2] == "Fake Reason"
        assert err is not None
        assert err.value.args[0] == 1


def test_delete_config_map_failure(caplog):
    with patch('intel.k8s.delete_config_map') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        with pytest.raises(SystemExit) as err:
            reconfigure.delete_config_map("fake-name", "fake-namespace")

        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-2][2] == "Exception when removing config map"\
                                      " fake-name"
        assert caplog_tuple[-1][2] == "Fake Reason"
        assert err is not None
        assert err.value.args[0] == 1
