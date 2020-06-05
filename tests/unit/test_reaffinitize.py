from intel import reaffinitize
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException
import pytest
import yaml


class MockProcess:
    def __init__(self, pid, cpu_affin, children=[]):
        self._pid = pid
        self._cpu_affin = cpu_affin
        self._children = children

    def cpu_affinity(self, cpus=None):
        if not cpus:
            return self.get_cpu_affinity()
        else:
            self.set_cpu_affinity(cpus)

    def children(self, children=None):
        if children is None:
            return self.get_children()
        else:
            self.set_children(children)

    def get_cpu_affinity(self):
        return self._cpu_affin

    def set_cpu_affinity(self, new_affin):
        self._cpu_affin = new_affin

    def get_children(self):
        return self._children

    def set_children(self, child):
        self._children = self._children + [child]


def process_with_affinity_no_children():
    return MockProcess(1, [4, 12])


def process_without_affinity_no_children():
    return MockProcess(1, [i for i in range(0, 15)])


def process_with_affinity_with_children():
    p = MockProcess(1, [4, 12])
    c = MockProcess(10, [4, 12])
    p.children(c)
    return p


def process_without_affinity_with_children():
    p = MockProcess(1, [i for i in range(0, 15)])
    c = MockProcess(10, [4, 12])
    p.children(c)
    return p


node_resp = {
        "metadata": {
            "annotations": {
                "old-config": "old config returned",
                "new-config": "new config returned"
                }
            }
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


non_isols_config_before = {
                 "exclusive": {
                              "0": {
                                   "3,14": [""],
                                   "4,15": ["2000"],
                                   "5,16": ["2001"],
                                   }
                              },
                 "shared": {
                              "0": {
                                   "6,17,7,18": ["1000", "1001",
                                                 "1002", "1003"]
                                   }
                              },
                 "infra": {
                              "0": {
                                   "0,11,1,12,2,13,8,19": ["3000", "3001",
                                                           "3002"]
                                   }
                              },
                 "exclusive-non-isolcpus": {
                              "0": {
                                   "9,20": [""],
                                   "10,21": ["6002"]
                                   }
                              }
                 }


non_isols_config_after = {
                 "exclusive": {
                              "0": {
                                   "3,14": ["2000"],
                                   "4,15": ["2001"]
                                   }
                              },
                 "shared": {
                              "0": {
                                   "5,16,6,17": ["1000", "1001",
                                                 "1002", "1003"]
                                   }
                              },
                 "infra": {
                              "0": {
                                   "0,11,1,12,2,13,8,19,10,21": ["3000",
                                                                 "3001",
                                                                 "3002"]
                                   }
                              },
                 "exclusive-non-isolcpus": {
                              "0": {
                                   "9,20": ["6002"]
                                   }
                              }
                 }


def get_aligned_cores():
    return {
        "3,11": "4,12",
        "4,12": "5,13"
    }


def test_get_core_alignment():
    core_alignment = reaffinitize.get_core_alignment(config_before,
                                                     config_after)
    assert core_alignment["4,12"] == "3,11"
    assert core_alignment["5,13"] == "4,12"
    assert core_alignment["6,14,7,15"] == "5,13"
    assert "3,11" not in core_alignment.keys()
    assert core_alignment["0,8,1,9,2,10"] == "0,8,1,9,2,10"


def test_get_core_alignment_isolcpus():
    core_alignment = reaffinitize.get_core_alignment(non_isols_config_before,
                                                     non_isols_config_after)
    assert core_alignment["4,15"] == "3,14"
    assert core_alignment["5,16"] == "4,15"
    assert core_alignment["6,17,7,18"] == "5,16,6,17"
    assert core_alignment["0,11,1,12,2,13,8,19"] == "0,11,1,12,2,13,8,19,10,21"
    assert core_alignment["10,21"] == "9,20"
    assert "3,14" not in core_alignment.keys()
    assert "7,18" not in core_alignment.keys()
    assert "9,20" not in core_alignment.keys()


def test_reaffinitize_cores_success1():
    core_alignment = reaffinitize.get_core_alignment(config_before,
                                                     config_after)
    mock_proc = process_with_affinity_no_children()
    with patch('psutil.Process',
               MagicMock(return_value=mock_proc)):
        reaffinitize.reaffinitize_cores(core_alignment)

        assert mock_proc.cpu_affinity() == [3, 11]


def test_reaffinitize_cores_success2(caplog):
    core_alignment = reaffinitize.get_core_alignment(config_before,
                                                     config_after)
    mock_proc = process_without_affinity_no_children()
    with patch('psutil.Process',
               MagicMock(return_value=mock_proc)):
        reaffinitize.reaffinitize_cores(core_alignment)

        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == "No affinity found, leaving as old"\
                                      " value {}".format([i for i in
                                                          range(0, 15)])
        assert mock_proc.cpu_affinity() == [i for i in range(0, 15)]


def test_reaffinitize_cores_success3():
    core_alignment = reaffinitize.get_core_alignment(config_before,
                                                     config_after)
    mock_proc = process_with_affinity_with_children()
    with patch('psutil.Process',
               MagicMock(return_value=mock_proc)):
        reaffinitize.reaffinitize_cores(core_alignment)

        assert mock_proc.cpu_affinity() == [3, 11]
        assert mock_proc.children()[0].cpu_affinity() == [3, 11]


def test_reaffinitize_cores_success4(caplog):
    core_alignment = reaffinitize.get_core_alignment(config_before,
                                                     config_after)
    mock_proc = process_without_affinity_with_children()
    with patch('psutil.Process',
               MagicMock(return_value=mock_proc)):
        reaffinitize.reaffinitize_cores(core_alignment)

        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-2][2] == "No affinity found, leaving as old"\
                                      " value {}".format([i for i in
                                                          range(0, 15)])
        assert mock_proc.children()[0].cpu_affinity() == [3, 11]


@patch('intel.discover.get_k8s_node',
       MagicMock(return_value=node_resp))
@patch('intel.reaffinitize.get_config_from_configmap',
       MagicMock(return_value="config returned"))
@patch('intel.reaffinitize.get_core_alignment',
       MagicMock(return_value=get_aligned_cores()))
def test_reaffinitize_logging(caplog):
    with patch('intel.reaffinitize.reaffinitize_cores',
               MagicMock(return_value="")):
        reaffinitize.reaffinitize("fake-node", "fake-namespace")

    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == "{'3,11': '4,12',"\
                                  " '4,12': '5,13'}"
    assert caplog_tuple[-2][2] == "Core alignment:"
    assert caplog_tuple[-3][2] == "config returned"
    assert caplog_tuple[-4][2] == "New CMK config:"
    assert caplog_tuple[-5][2] == "config returned"
    assert caplog_tuple[-6][2] == "Old CMK config:"


def test_get_config_from_configmap():
    get_config_map_return = {"config": yaml.dump(config_before)}
    with patch('intel.k8s.get_config_map',
               MagicMock(return_value=get_config_map_return)):
        config = reaffinitize.get_config_from_configmap("fake-name",
                                                        "fake-namespace")

    assert config == config_before


def test_get_config_from_configmap_failure(caplog):
    with patch('intel.k8s.get_config_map') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        with pytest.raises(SystemExit) as err:
            reaffinitize.get_config_from_configmap("fake-name",
                                                   "fake-namespace")

        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-2][2] == "Error while retreiving configmap"\
                                      " fake-name"
        assert caplog_tuple[-1][2] == "Fake Reason"
        assert err is not None
        assert err.value.args[0] == 1
