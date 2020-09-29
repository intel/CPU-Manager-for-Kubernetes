from intel import isolate, config
from unittest.mock import patch, MagicMock
import pytest


EXCL_ONE = [
    {
        "pool": "exclusive",
        "socket": "0",
        "cl": "0,11",
        "tasks": ["123"]
    }
]


SHAR_ONE = [
    {
        "pool": "shared",
        "socket": "0",
        "cl": "4,15,5,16",
        "tasks": ["123"]
    }
]


INF_ONE = [
    {
        "pool": "infra",
        "socket": "0",
        "cl": "6,17,7,18,8,19",
        "tasks": ["123"]
    }
]


EXNI_ONE = [
    {
        "pool": "exclusive-non-isolcpus",
        "socket": "0",
        "cl": "9,20",
        "tasks": ["123"]
    }
]


FAKE_CONFIG = {
    "exclusive": {
        "0": {
            "0,11": [],
            "1,12": [],
            "2,13": []
        },
        "1": {
            "3,14": []
        }
    },
    "shared": {
        "0": {
            "4,15,5,16": []
        },
        "1": {}
    },
    "infra": {
        "0": {
            "6,17,7,18,8,19": []
        },
        "1": {}
    },
    "exclusive-non-isolcpus": {
        "0": {
            "9,20": [],
            "10,21": []
        },
        "1": {}
    }
}


def return_config(conf):
    c = FAKE_CONFIG
    for item in conf:
        c[item["pool"]][item["socket"]][item["cl"]] = item["tasks"]
    return config.build_config(c)


class MockConfig(config.Config):

    def __init__(self, conf):
        self.cm_name = "fake-name"
        self.owner = "fake-owner"
        self.c_data = conf

    def lock(self):
        return

    def unlock(self):
        return


class MockProcess():

    def __init__(self):
        self.pid = 9
        self.affinity = []

    def cpu_affinity(self, cpus=None):
        if not cpus:
            return self.get_cpu_affinity()
        else:
            self.set_cpu_affinity(cpus)

    def get_cpu_affinity(self):
        return self._cpu_affin

    def set_cpu_affinity(self, new_affin):
        self._cpu_affin = new_affin


class MockChild():

    def __init__(self):
        self.name = "child"
        self.terminate = "term"

    def wait(self):
        return


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
@patch('intel.k8s.delete_config_map',
       MagicMock(return_value=''))
@patch('intel.config.Config.lock', MagicMock(return_value=''))
@patch('intel.config.Config.unlock', MagicMock(return_value=''))
def test_isolate_exclusive1():
    p = MockProcess()
    c = MockConfig(return_config([]))
    with patch('psutil.Process', MagicMock(return_value=p)):
        with patch('intel.config.Config', MagicMock(return_value=c)):
            isolate.isolate("exclusive", False, "fake-cmd",
                            ["fake-args"], socket_id=None)
            assert p.cpu_affinity() == [0, 11]


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_isolate_exclusive2():
    p = MockProcess()
    c = MockConfig(return_config(EXCL_ONE))
    with patch('psutil.Process',
               MagicMock(return_value=p)):
        with patch('intel.config.Config', MagicMock(return_value=c)):
            isolate.isolate("exclusive", False, "fake-cmd",
                            ["fake-args"], socket_id=None)
            assert p.cpu_affinity() == [1, 12]


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_isolate_exclusive3():
    p = MockProcess()
    c = MockConfig(return_config([]))
    with patch('psutil.Process',
               MagicMock(return_value=p)):
        with patch('intel.config.Config', MagicMock(return_value=c)):
            isolate.isolate("exclusive", False, "fake-cmd",
                            ["fake-args"], socket_id="1")
            assert p.cpu_affinity() == [3, 14]


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_isolate_shared1():
    p = MockProcess()
    c = MockConfig(return_config([]))
    with patch('psutil.Process',
               MagicMock(return_value=p)):
        with patch('intel.config.Config', MagicMock(return_value=c)):
            isolate.isolate("shared", False, "fake-cmd",
                            ["fake-args"], socket_id=None)
            assert p.cpu_affinity() == [4, 15, 5, 16]


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_isolate_shared2():
    p = MockProcess()
    c = MockConfig(return_config(SHAR_ONE))
    with patch('psutil.Process',
               MagicMock(return_value=p)):
        with patch('intel.config.Config', MagicMock(return_value=c)):
            isolate.isolate("shared", False, "fake-cmd",
                            ["fake-args"], socket_id=None)
            assert p.cpu_affinity() == [4, 15, 5, 16]


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_isolate_infra1():
    p = MockProcess()
    c = MockConfig(return_config([]))
    with patch('psutil.Process',
               MagicMock(return_value=p)):
        with patch('intel.config.Config', MagicMock(return_value=c)):
            isolate.isolate("infra", False, "fake-cmd",
                            ["fake-args"], socket_id=None)
            assert p.cpu_affinity() == [6, 17, 7, 18, 8, 19]


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_isolate_infra2():
    p = MockProcess()
    c = MockConfig(return_config(INF_ONE))
    with patch('psutil.Process',
               MagicMock(return_value=p)):
        with patch('intel.config.Config', MagicMock(return_value=c)):
            isolate.isolate("infra", False, "fake-cmd",
                            ["fake-args"], socket_id=None)
            assert p.cpu_affinity() == [6, 17, 7, 18, 8, 19]


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_isolate_exclusive_non_isolcpus2():
    p = MockProcess()
    c = MockConfig(return_config(EXNI_ONE))
    with patch('psutil.Process',
               MagicMock(return_value=p)):
        with patch('intel.config.Config', MagicMock(return_value=c)):
            isolate.isolate("exclusive-non-isolcpus", False, "fake-cmd",
                            ["fake-args"], socket_id=None)
            assert p.cpu_affinity() == [10, 21]


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_pool_not_exist():
    c = MockConfig(return_config([]))
    with patch('intel.config.Config', MagicMock(return_value=c)):
        with pytest.raises(KeyError) as err:
            isolate.isolate("fake-pool", False, "fake-cmd",
                            ["fake-args"], socket_id=None)

        assert err is not None
        assert err.value.args[0] == "Requested pool fake-pool does not exist"


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.getenv', MagicMock(return_value=0))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_n_cpus_lt_one():
    c = MockConfig(return_config([]))
    with patch('intel.config.Config', MagicMock(return_value=c)):
        with pytest.raises(ValueError) as err:
            isolate.isolate("exclusive", False, "fake-cmd",
                            ["fake-args"], socket_id=None)

        assert err is not None
        assert err.value.args[0] == "Requested numbers of cores "\
                                    "must be positive integer"


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.getenv', MagicMock(return_value=5))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_not_enough_cpus():
    c = MockConfig(return_config([]))
    with patch('intel.config.Config', MagicMock(return_value=c)):
        with pytest.raises(SystemError) as err:
            isolate.isolate("exclusive", False, "fake-cmd",
                            ["fake-args"], socket_id=None)

        assert err is not None
        assert err.value.args[0] == "Not enough free cpu lists "\
                                    "in pool exclusive"


@patch('subprocess.Popen', MagicMock(return_value=MockChild()))
@patch('intel.proc.getpid', MagicMock(return_value=1234))
@patch('signal.signal', MagicMock(return_value=None))
@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_isolate_shared_failure1():
    c = MockConfig(return_config([]))
    with patch('intel.config.Config', MagicMock(return_value=c)):
        with pytest.raises(SystemError) as err:
            isolate.isolate("shared", False, "fake-cmd",
                            ["fake-args"], socket_id="1")

        assert err is not None
        assert err.value.args[0] == "No cpu lists in pool shared"
