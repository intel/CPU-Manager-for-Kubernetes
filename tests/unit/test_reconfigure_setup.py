from intel import reconfigure_setup
from kubernetes.client.rest import ApiException
import pytest
from unittest.mock import patch, MagicMock


node_list = [
            {
                "metadata": {
                    "labels": {
                        "cmk.intel.com/cmk-node": "true"
                        },
                    "name": "node1"
                    }
                },
            {
                "metadata": {
                    "labels": {
                        },
                    "name": "node2"
                    }
                },
            {
                "metadata": {
                    "labels": {
                        "cmk.intel.com/cmk-node": "true"
                        },
                    "name": "node3"
                    }
                }
            ]


zero_node_list = []


empty_node_list = [
            {
                "metadata": {
                    "labels": {
                        },
                    "name": "node1"
                    }
                },
            {
                "metadata": {
                    "labels": {
                        },
                    "name": "node2"
                    }
                },
            {
                "metadata": {
                    "labels": {
                        },
                    "name": "node3"
                    }
                }
            ]


def test_get_cmk_nodes_success():
    with patch('intel.k8s.get_compute_nodes',
               MagicMock(return_value=node_list)):
        returned_list = reconfigure_setup.get_cmk_nodes()
    assert "node2" not in returned_list
    assert returned_list == ["node1", "node3"]


def test_get_cmk_nodes_failure1(caplog):
    with patch('intel.k8s.get_compute_nodes',
               MagicMock(return_value=zero_node_list)):
        with pytest.raises(SystemExit) as err:
            reconfigure_setup.get_cmk_nodes()

        caplog_tuple = caplog.record_tuples
        expected_msg = "No CMK nodes detected, aborting..."
        assert caplog_tuple[-1][2] == expected_msg
        assert err is not None
        assert err.value.args[0] == 1


def test_get_cmk_nodes_failure2(caplog):
    with patch('intel.k8s.get_compute_nodes',
               MagicMock(return_value=empty_node_list)):
        with pytest.raises(SystemExit) as err:
            reconfigure_setup.get_cmk_nodes()

        caplog_tuple = caplog.record_tuples
        expected_msg = "No CMK nodes detected, aborting..."
        assert caplog_tuple[-1][2] == expected_msg
        assert err is not None
        assert err.value.args[0] == 1


def test_execute_reconfigure_failure1(caplog):
    with patch('intel.k8s.create_pod') as mock:
        mock.side_effect = ApiException(status=0, reason="Fake Reason")
        with pytest.raises(SystemExit) as err:
            reconfigure_setup.execute_reconfigure(2, 2, "-1", "/etc/cmk",
                                                  "packed", "packed",
                                                  "cmk:v1.4.1", "IfNotPresent",
                                                  "/opt/bin", node_list,
                                                  "fake-saname",
                                                  "fake-namespace")

        caplog_tuple = caplog.record_tuples
        expected_msg1 = "Exception when creating pod for"\
                        " reconfigure command: Fake Reason"
        assert caplog_tuple[-2][2] == expected_msg1
        expected_msg2 = "Aborting reconfigure ..."
        assert caplog_tuple[-1][2] == expected_msg2
        assert err is not None
        assert err.value.args[0] == 1


@patch('intel.k8s.create_pod', MagicMock(return_value="Fake response"))
def test_execute_reconfigure_failure2(caplog):
    with patch('intel.clusterinit.wait_for_pod_phase') as mock:
        mock.side_effect = RuntimeError("Fake Error")
        with pytest.raises(SystemExit) as err:
            reconfigure_setup.execute_reconfigure(2, 2, "-1", "/etc/cmk",
                                                  "packed", "packed",
                                                  "cmk:v1.4.1", "IfNotPresent",
                                                  "/opt/bin", node_list,
                                                  "fake-saname",
                                                  "fake-namespace")

            caplog_tuple = caplog.record_tuples
            expected_msg1 = "Exception when creating pod for"\
                            " reconfigure command: Fake Reason"
            assert caplog_tuple[-2][2] == expected_msg1
            expected_msg2 = "Aborting reconfigure ..."
            assert caplog_tuple[-1][2] == expected_msg2
            assert err is not None
            assert err.value.args[0] == 1
