from intel import reconfigure, config
from kubernetes.client.rest import ApiException
import pytest
import yaml
from unittest.mock import patch, MagicMock


class MockConfig():

    def __init__(self):
        self.assert_hostname = False

    def connect_get_namespaced_pod_exec(self):
        return ""


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


single_pod = [{
            "name": "fake-name",
            "namespace": "fake-namespace",
            "containers": ["container"]
        }]


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
6,6,1,0,,6,6,6,0
7,7,1,0,,7,7,7,0
8,8,1,0,,8,8,8,0
9,9,1,0,,0,0,0,0
10,10,1,0,,1,1,1,0
11,0,0,0,,2,2,2,0
12,1,0,0,,3,3,3,0
13,2,0,0,,4,4,4,0
14,3,0,0,,5,5,5,0
15,4,0,0,,6,6,6,0
16,5,0,0,,7,7,7,0
17,6,1,0,,8,8,8,0
18,7,1,0,,7,7,7,0
19,8,1,0,,8,8,8,0
20,9,1,0,,0,0,0,0
21,10,1,0,,1,1,1,0
"""


def return_proc_info():
    proc_info = []
    pool_names = ["exclusive", "exclusive", "exclusive",
                  "exclusive-non-isolcpus", "exclusive-non-isolcpus"]

    for i in range(len(pool_names)):
        p = reconfigure.ProcessInfo(pool_names[i], "0", [True, True],
                                    "{},{}".format(i, i+10),
                                    "{}".format(i+1000))
        proc_info.append(p)
    return proc_info


def test_pid_class():
    p = reconfigure.Pid()
    p.add_old_clist("1,11")
    p.add_new_clist("1,11")
    assert p.old_clists == ["1,11"]
    assert p.new_clist == "1,11"

    p.add_old_clist("3,13")
    p.add_new_clist("2,12")
    assert p.old_clists == ["1,11", "3,13"]
    assert p.new_clist == "1,11,2,12"


def test_proc_class():
    p = reconfigure.Procs()
    p.add_proc("1000", "1,11")
    assert len(p.process_map.keys()) == 1
    assert "1000" in p.process_map.keys()
    assert p.process_map["1000"].old_clists == ["1,11"]

    p.add_proc("1001", "2,12")
    assert len(p.process_map.keys()) == 2
    assert "1000" in p.process_map.keys()
    assert "1001" in p.process_map.keys()
    assert p.process_map["1001"].old_clists == ["2,12"]

    p.add_proc("1000", "3,13")
    assert len(p.process_map.keys()) == 2
    assert "1000" in p.process_map.keys()
    assert "1001" in p.process_map.keys()
    assert p.process_map["1000"].old_clists == ["1,11", "3,13"]


def test_process_info_class():
    p = reconfigure.ProcessInfo("pool", "0", [True, True], "1,11", ["1000"])
    assert p.pool == "pool"
    assert p.socket == "0"
    assert p.sockets == [True, True]
    assert p.old_clist == "1,11"
    assert p.pid == ["1000"]


def test_check_processes_failure1(caplog):
    with pytest.raises(SystemExit) as err:
        reconfigure.check_processes(return_proc_info(), 2, 2)

    caplog_tuple = caplog.record_tuples
    expected_msg1 = "Not enough exclusive cores in new configuration: 3"\
                    " processes, 2 cores"
    assert caplog_tuple[-2][2] == expected_msg1
    expected_msg2 = "Aborting reconfigure..."
    assert caplog_tuple[-1][2] == expected_msg2
    assert err is not None
    assert err.value.args[0] == 1


def test_check_processes_failure2(caplog):
    with pytest.raises(SystemExit) as err:
        reconfigure.check_processes(return_proc_info(), 3, 1)

    caplog_tuple = caplog.record_tuples
    expected_msg1 = "Not enough exclusive-non-isolcpus cores in new"\
                    " configuration: 2 processes, 1 cores"
    assert caplog_tuple[-2][2] == expected_msg1
    expected_msg2 = "Aborting reconfigure..."
    assert caplog_tuple[-1][2] == expected_msg2
    assert err is not None
    assert err.value.args[0] == 1


def test_check_processes_failure3(caplog):
    with pytest.raises(SystemExit) as err:
        reconfigure.check_processes(return_proc_info(), 2, 1)

    caplog_tuple = caplog.record_tuples
    expected_msg1 = "Not enough exclusive cores in new configuration: 3"\
                    " processes, 2 cores"
    assert caplog_tuple[-3][2] == expected_msg1
    expected_msg2 = "Not enough exclusive-non-isolcpus cores in new"\
                    " configuration: 2 processes, 1 cores"
    assert caplog_tuple[-2][2] == expected_msg2
    expected_msg3 = "Aborting reconfigure..."
    assert caplog_tuple[-1][2] == expected_msg3
    assert err is not None
    assert err.value.args[0] == 1


@patch('kubernetes.client.V1ConfigMap',
       MagicMock(return_value=""))
@patch('intel.clusterinit.update_configmap',
       MagicMock(return_value=""))
def test_set_config_map(caplog):
    with patch('intel.k8s.create_config_map') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        with pytest.raises(SystemExit) as err:
            reconfigure.set_config_map("fake-name", "fake-namespace", "config")

        caplog_tuple = caplog.record_tuples
        expected_msg = "Exception when creating config map fake-name"
        assert caplog_tuple[-2][2] == expected_msg
        expected_rsn = "Fake Reason"
        assert caplog_tuple[-1][2] == expected_rsn
        assert err is not None
        assert err.value.args[0] == 1


def test_delete_config_map(caplog):
    with patch('intel.k8s.delete_config_map') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        with pytest.raises(SystemExit) as err:
            reconfigure.delete_config_map("fake-name", "fake-namespace")

        caplog_tuple = caplog.record_tuples
        expected_msg = "Exception when removing config map fake-name"
        assert caplog_tuple[-2][2] == expected_msg
        expected_rsn = "Fake Reason"
        assert caplog_tuple[-1][2] == expected_rsn
        assert err is not None
        assert err.value.args[0] == 1


@patch('os.environ', MagicMock(return_value="host_pod"))
def test_get_pods():
    with patch('intel.k8s.get_pod_list',
               MagicMock(return_value=returned_pods)):
        pods = reconfigure.get_pods()

    assert len(pods) == 2
    assert pods[0]["name"] == "fake-node1"
    assert pods[0]["namespace"] == "fake-namespace"
    assert len(pods[0]["containers"]) == 1
    assert pods[0]["containers"][0] == "fake-container"

    assert pods[1]["name"] == "fake-node3"
    assert pods[1]["namespace"] == "fake-namespace"
    assert len(pods[1]["containers"]) == 2
    assert pods[1]["containers"][0] == "fake-container1"
    assert pods[1]["containers"][1] == "fake-container2"


"""def test_build_config_map_failure(caplog):
    path = helpers.conf_dir('fail')
    with pytest.raises(SystemExit) as err:
        _ = reconfigure.build_config_map(path)

    caplog_tuple = caplog.record_tuples
    expected_msg = "Error while reading configuration"\
                   " at /cmk/tests/data/config/fail/pools,"\
                   " incorrect pool incorrect_pool_name"
    assert caplog_tuple[-1][2] == expected_msg
    assert err is not None
    assert err.value.args[0] == 1"""


@patch('intel.k8s.get_config_map',
       MagicMock(return_value={'config': yaml.dump(config_before)}))
@patch('intel.k8s.delete_config_map', MagicMock(return_value=''))
def test_build_proc_info1():
    conf = config.Config("fake-name")
    conf.lock()
    c = reconfigure.build_proc_info(conf)
    p = c[1]

    assert len(p.process_map) == 10
    assert p.process_map["2001"].old_clists == ["4,12"]
    assert p.process_map["2002"].old_clists == ["5,13"]
    assert p.process_map["1000"].old_clists == ["6,14,7,15"]
    assert p.process_map["1001"].old_clists == ["6,14,7,15"]
    assert p.process_map["1002"].old_clists == ["6,14,7,15"]
    assert p.process_map["1003"].old_clists == ["6,14,7,15"]
    assert p.process_map["3000"].old_clists == ["0,8,1,9,2,10"]
    assert p.process_map["3001"].old_clists == ["0,8,1,9,2,10"]
    assert p.process_map["3002"].old_clists == ["0,8,1,9,2,10"]


@patch('intel.k8s.get_config_map',
       MagicMock(return_value={'config': yaml.dump(config_before)}))
@patch('intel.k8s.delete_config_map', MagicMock(return_value=''))
def test_proc_info():
    clist_map = {
        "3,11": [""],
        "4,12": ["2001"],
        "5,13": ["2002"],
        "6,14,7,15": ["1000", "1001", "1002", "1003"],
        "0,8,1,9,2,10": ["3000", "3001", "3002"]
    }
    conf = config.Config("fake-name")
    conf.lock()
    c = reconfigure.build_proc_info(conf)
    p = c[0]

    assert len(p) == 5
    for proc_info in p:
        assert proc_info.pid == clist_map[proc_info.old_clist]


"""def test_reconfigure_directory(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("reconf_isolcpus"))

    clist_map = {
        "2001": "3,14",
        "2002": "2,13",
        "1000": "4,15,5,16",
        "1001": "4,15,5,16",
        "1002": "4,15,5,16",
        "1003": "4,15,5,16",
        "3000": "0,11,1,12",
        "3001": "0,11,1,12",
        "3002": "0,11,1,12"
    }

    with patch('intel.topology.lscpu', MagicMock(return_value=lscpu_cores())):
        temp_dir = tempfile.mkdtemp()
        temp_dir_root = temp_dir+"reconfigure"
        shutil.copytree(helpers.conf_dir('reconf_before'), temp_dir_root)
        c = config.Config(temp_dir_root)
        procs = reconfigure.build_config_map(temp_dir_root)
        reconfigure.reconfigure_directory(c, temp_dir_root, 2, 2,
                                          "vertical", "vertical", "-1",
                                          procs[0], procs[1])
        for p in procs[1].process_map.keys():
            assert procs[1].process_map[p].new_clist == clist_map[p]


@patch('intel.k8s.client_from_config', MagicMock(return_value=""))
@patch('kubernetes.client.Configuration',
       MagicMock(return_value=MockConfig()))
@patch('kubernetes.client.Configuration.set_default',
       MagicMock(return_value=""))
@patch('kubernetes.client.CoreV1Api',
       MagicMock(return_value=MockConfig()))
def test_execute_reconfigure_failure(caplog):
    with patch('kubernetes.stream.stream') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        reconfigure.execute_reconfigure("/opt/bin", "fake-node", single_pod,
                                        "fake-namespace")

    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == "Error occured while executing command"\
                                  " in pod: Fake Reason"
"""
