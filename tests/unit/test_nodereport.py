from intel import nodereport, topology


def return_socket():
    socket = topology.Socket(0)
    core = topology.Core(0)
    socket.cores[0] = core
    cpu0 = topology.CPU(0)
    cpu1 = topology.CPU(1)
    core.cpus[0] = cpu0
    core.cpus[1] = cpu1
    return socket


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


def test_check_class():
    check = nodereport.Check("fake_check")
    assert check.ok
    assert check.errors == []
    assert check.name == "fake_check"

    check.add_error("fake_error")
    assert not check.ok
    assert len(check.errors) == 1
    assert check.errors[0] == "fake_error"

    expected_resp = {
        "ok": False,
        "errors": ["fake_error"]
    }

    resp = check.as_dict()
    assert resp == expected_resp


def test_nodereport_class():
    nr = nodereport.NodeReport()
    nr.add_description("fake_description")
    nr.add_socket(return_socket())
    nr.add_check(nodereport.Check("fake_check"))

    resp = nr.as_dict()
    assert resp["description"] == "fake_description"
    assert 0 in resp["topology"]["sockets"].keys()
