from .. import helpers
from intel import sst_cp, topology
from unittest.mock import patch


def return_cores():
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
        }),
        4: topology.Core(4, {
            4: topology.CPU(4),
            8: topology.CPU(8)
        })
    })

    return topology.Platform({0: sockets})


@patch('intel.sst_cp.CPU_EPP_PATH', helpers.sst_cp_dir())
def test_get_epp_order():
    epp_order = sst_cp.get_epp_order(return_cores())
    assert len(epp_order) == 3
    assert epp_order[0] == "performance"
    assert epp_order[1] == "balance_performance"
    assert epp_order[2] == "power"


@patch('intel.sst_cp.CPU_EPP_PATH', helpers.sst_cp_dir())
def test_get_epp_cores_no_limit_performance():
    cores = sst_cp.get_epp_cores_no_limit(return_cores(), "performance")
    assert len(cores) == 2
    assert cores[0].core_id == 3
    assert cores[1].core_id == 4


@patch('intel.sst_cp.CPU_EPP_PATH', helpers.sst_cp_dir())
def test_get_epp_cores_no_limit_balance_performance():
    cores = sst_cp.get_epp_cores_no_limit(return_cores(),
                                          "balance_performance")
    assert len(cores) == 2
    assert cores[0].core_id == 1
    assert cores[1].core_id == 2


@patch('intel.sst_cp.CPU_EPP_PATH', helpers.sst_cp_dir())
def test_get_epp_cores_no_limit_power():
    cores = sst_cp.get_epp_cores_no_limit(return_cores(), "power")
    assert len(cores) == 1
    assert cores[0].core_id == 0


@patch('intel.sst_cp.CPU_EPP_PATH', helpers.sst_cp_dir())
def test_get_epp_cores_performance():
    unavailable = [topology.Core(3)]
    cores = sst_cp.get_epp_cores(return_cores(), "performance",
                                 1, unavailable)
    assert len(cores) == 1
    assert cores[0].core_id == 4

    unavailable = [topology.Core(4)]
    cores = sst_cp.get_epp_cores(return_cores(), "performance",
                                 1, unavailable)
    assert len(cores) == 1
    assert cores[0].core_id == 3


@patch('intel.sst_cp.CPU_EPP_PATH', helpers.sst_cp_dir())
def test_get_epp_cores_balance_performance():
    unavailable = [topology.Core(1)]
    cores = sst_cp.get_epp_cores(return_cores(), "balance_performance",
                                 1, unavailable)
    assert len(cores) == 1
    assert cores[0].core_id == 2

    unavailable = [topology.Core(2)]
    cores = sst_cp.get_epp_cores(return_cores(), "balance_performance",
                                 1, unavailable)
    assert len(cores) == 1
    assert cores[0].core_id == 1
