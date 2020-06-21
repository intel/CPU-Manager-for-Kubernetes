from intel import reaffinitize, reconfigure
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


def return_procs_class():
    procs = reconfigure.Procs()
    procs.add_proc("1000", "1,11")
    procs.process_map["1000"].add_new_clist("1,11")
    procs.add_proc("1001", "3,13")
    procs.process_map["1001"].add_new_clist("2,12")
    procs.add_proc("1002", "5,15")
    procs.add_proc("1002", "6,16")
    procs.process_map["1002"].add_new_clist("4,14")
    procs.process_map["1002"].add_new_clist("5,15")
    return procs


def return_mock_process():
    mock = MockProcess(1, [1, 2, 3, 4, 11, 12, 13, 14])
    child1 = MockProcess(6, [3, 13])
    child2 = MockProcess(10, [3, 13])
    child1.children(child2)
    mock.children(child1)
    return mock


def test_get_config_from_configmap_failure(caplog):
    with patch('intel.k8s.get_config_map') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        with pytest.raises(SystemExit) as err:
            reaffinitize.get_config_from_configmap("fake-name",
                                                   "fake-namespace")

        caplog_tuple = caplog.record_tuples
        expected_msg = "Error while retreiving configmap fake-name"
        expected_rsn = "Fake Reason"
        assert caplog_tuple[-2][2] == expected_msg
        assert caplog_tuple[-1][2] == expected_rsn

        assert err is not None
        assert err.value.args[0] == 1


def test_get_config_from_configmap_success():
    procs = return_procs_class()
    with patch('intel.k8s.get_config_map',
               MagicMock(return_value={"config": yaml.dump(procs)})):
        config = reaffinitize.get_config_from_configmap("fake-name",
                                                        "fake-namespace")

    assert len(config.process_map.keys()) == 3
    assert "1000" in config.process_map.keys()
    assert "1001" in config.process_map.keys()
    assert "1002" in config.process_map.keys()
    assert config.process_map["1000"].old_clists == ["1,11"]
    assert config.process_map["1000"].new_clist == "1,11"
    assert config.process_map["1001"].old_clists == ["3,13"]
    assert config.process_map["1001"].new_clist == "2,12"
    assert config.process_map["1002"].old_clists == ["5,15", "6,16"]
    assert config.process_map["1002"].new_clist == "4,14,5,15"


def test_reaffinitize_cores():
    procs = return_procs_class()
    mock_proc = return_mock_process()
    with patch('psutil.Process',
               MagicMock(return_value=mock_proc)):
        reaffinitize.reaffinitize_cores(procs)

    child1 = mock_proc.children()[0]
    child2 = child1.children()[0]
    assert mock_proc.cpu_affinity() != [2, 12]
    assert mock_proc.cpu_affinity() == [1, 2, 3, 4, 11, 12, 13, 14]
    assert child1.cpu_affinity() != [3, 13]
    assert child1.cpu_affinity() == [2, 12]
    assert child2.cpu_affinity() != [3, 13]
    assert child2.cpu_affinity() == [2, 12]
