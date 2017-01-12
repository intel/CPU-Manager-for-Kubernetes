import pytest
from intel import clusterinit
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException as K8sApiException


def test_clusterinit_invalid_cmd_list_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "fakecmd1, fakecmd2",
                                 "kcm", "Never", "/etc/kcm", "/opt/bin",
                                 "4", "2")
    expected_err_msg = ('KCM command should be one of '
                        '[\'init\', \'discover\', \'install\', \'reconcile\']')
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "fakecmd1, init",
                                 "kcm", "Never", "/etc/kcm", "/opt/bin",
                                 "4", "2")
    expected_err_msg = ('KCM command should be one of '
                        '[\'init\', \'discover\', \'install\', \'reconcile\']')
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure3():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init, fakecmd1, install",
                                 "kcm", "Never", "/etc/kcm", "/opt/bin",
                                 "4", "2")
    expected_err_msg = ('KCM command should be one of '
                        '[\'init\', \'discover\', \'install\', \'reconcile\']')
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure4():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "discover, init",
                                 "kcm", "Never", "/etc/kcm", "/opt/bin",
                                 "4", "2")
    expected_err_msg = "init command should be run and listed first."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_image_pol():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "fakepol1",
                                 "/etc/kcm", "/opt/bin", "4", "2")
    expected_err_msg = ('Image pull policy should be one of '
                        '[\'Never\', \'IfNotPresent\', \'Always\']')
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_dp_cores_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "Never",
                                 "/etc/kcm", "/opt/bin", "-1", "2")
    expected_err_msg = "num_dp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_dp_cores_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "Never",
                                 "/etc/kcm", "/opt/bin", "3.5", "2")
    expected_err_msg = "num_dp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cp_cores_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "Never",
                                 "/etc/kcm", "/opt/bin", "1", "2.5")
    expected_err_msg = "num_cp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cp_cores_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "Never",
                                 "/etc/kcm", "/opt/bin", "1", "10.5")
    expected_err_msg = "num_cp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


class FakeHTTPResponse:
    def __init__(self, status=None, reason=None, data=None):
        self.status = status
        self.reason = reason
        self.data = data

    def getheaders(self):
        return {"fakekey": "fakeval"}


def test_clusterinit_run_cmd_pods_init_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.clusterinit.create_k8s_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods("init", "fake_img", "Never", "fake-conf-dir",
                                 "fake-install-dir", "2", "2", ["fakenode"])
        exp_log_err = """Exception when creating init pod: (500)
Reason: fake reason
HTTP response headers: {'fakekey': 'fakeval'}
HTTP response body: fake body
"""
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_discover_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.clusterinit.create_k8s_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods("discover", "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"])
        exp_log_err = """Exception when creating discover pod: (500)
Reason: fake reason
HTTP response headers: {'fakekey': 'fakeval'}
HTTP response body: fake body
"""
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_install_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.clusterinit.create_k8s_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods("install", "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"])
        exp_log_err = """Exception when creating install pod: (500)
Reason: fake reason
HTTP response headers: {'fakekey': 'fakeval'}
HTTP response body: fake body
"""
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_reconcile_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.clusterinit.create_k8s_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods("reconcile", "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"])
        exp_log_err = """Exception when creating reconcile pod: (500)
Reason: fake reason
HTTP response headers: {'fakekey': 'fakeval'}
HTTP response body: fake body
"""
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_wait_for_pod_phase_error():
    fake_pod_list_resp = {}
    fake_pod_list_resp["items"] = [
            {"metadata": {"name": "fakepod1"}, "status": {"phase": "Failed"}},
            {"metadata": {"name": "fakepod2"}, "status": {"phase": "Running"}},
            {"metadata": {"name": "fakepod3"}, "status": {"phase": "Failed"}}
        ]
    with patch('intel.clusterinit.get_k8s_pod_list',
               MagicMock(return_value=fake_pod_list_resp)):
        with pytest.raises(RuntimeError) as err:
            clusterinit.wait_for_pod_phase("fakepod1", "Running")
        expected_err_msg = "The Pod fakepod1 went into Failed state"
        assert err.value.args[0] == expected_err_msg

        with pytest.raises(RuntimeError) as err:
            clusterinit.wait_for_pod_phase("fakepod3", "Running")
        expected_err_msg = "The Pod fakepod3 went into Failed state"
        assert err.value.args[0] == expected_err_msg


def test_clusterinit_node_list_all():
    fake_node_list_resp = {}
    fake_node_list_resp["items"] = [
                {"metadata": {"name": "fakenode1"}},
                {"metadata": {"name": "fakenode2"}},
                {"metadata": {"name": "fakenode3"}}
        ]
    with patch('intel.clusterinit.get_k8s_node_list',
               MagicMock(return_value=fake_node_list_resp)):
        node_list = clusterinit.get_kcm_node_list(None, True)
        assert node_list == ["fakenode1", "fakenode2", "fakenode3"]


def test_clusterinit_node_list_host_list():
    fake_node_list = "fakenode1, fakenode2, fakenode3"
    node_list = clusterinit.get_kcm_node_list(fake_node_list, False)
    assert node_list == ["fakenode1", "fakenode2", "fakenode3"]
