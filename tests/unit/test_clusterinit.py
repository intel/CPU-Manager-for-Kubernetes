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
import json
import pytest

from intel import clusterinit
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException as K8sApiException
from kubernetes import client as k8sclient


def test_clusterinit_invalid_cmd_list_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "fakecmd1, fakecmd2",
                                 "cmk", "Never", "/etc/cmk", "/opt/bin",
                                 "4", "2", "", "", "vertical", "vertical")
    expected_err_msg = ("CMK command should be one of "
                        "['init', 'discover', 'install', 'reconcile', "
                        "'nodereport']")
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "fakecmd1, init",
                                 "cmk", "Never", "/etc/cmk", "/opt/bin",
                                 "4", "2", "", "", "vertical", "vertical")
    expected_err_msg = ("CMK command should be one of "
                        "['init', 'discover', 'install', 'reconcile', "
                        "'nodereport']")
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure3():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init, fakecmd1, install",
                                 "cmk", "Never", "/etc/cmk", "/opt/bin",
                                 "4", "2", "", "", "vertical", "vertical")
    expected_err_msg = ("CMK command should be one of "
                        "['init', 'discover', 'install', 'reconcile', "
                        "'nodereport']")
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure4():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "discover, init",
                                 "cmk", "Never", "/etc/cmk", "/opt/bin",
                                 "4", "2", "", "", "vertical", "vertical")
    expected_err_msg = "init command should be run and listed first."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_image_pol():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "cmk", "fakepol1",
                                 "/etc/cmk", "/opt/bin", "4", "2", "", "",
                                 "vertical", "vertical")
    expected_err_msg = ('Image pull policy should be one of '
                        '[\'Never\', \'IfNotPresent\', \'Always\']')
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_dp_cores_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "cmk", "Never",
                                 "/etc/cmk", "/opt/bin", "-1", "2", "", "",
                                 "vertical", "vertical")
    expected_err_msg = "num_dp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_dp_cores_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "cmk", "Never",
                                 "/etc/cmk", "/opt/bin", "3.5", "2", "", "",
                                 "vertical", "vertical")
    expected_err_msg = "num_dp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cp_cores_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "cmk", "Never",
                                 "/etc/cmk", "/opt/bin", "1", "2.5", "", "",
                                 "vertical", "vertical")
    expected_err_msg = "num_cp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cp_cores_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "cmk", "Never",
                                 "/etc/cmk", "/opt/bin", "1", "10.5", "", "",
                                 "vertical", "vertical")
    expected_err_msg = "num_cp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


class FakeHTTPResponse:
    def __init__(self, status=None, reason=None, data=None):
        self.status = status
        self.reason = reason
        self.data = data

    def getheaders(self):
        return {"fakekey": "fakeval"}


def get_expected_log_error(err_msg):
    exp_log_err = err_msg + """: (500)
Reason: fake reason
HTTP response headers: {'fakekey': 'fakeval'}
HTTP response body: fake body
"""
    return exp_log_err


def test_clusterinit_run_cmd_pods_init_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.k8s.create_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods(None, ["init"], "fake_img",
                                 "Never", "fake-conf-dir", "fake-install-dir",
                                 "2", "2", ["fakenode"], "", "", "vertical",
                                 "vertical")
        exp_err = "Exception when creating pod for ['init'] command(s)"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_discover_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.k8s.create_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods(None, ["discover"], "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"], "", "", "vertical",
                                 "vertical")
        exp_err = "Exception when creating pod for ['discover'] command(s)"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_install_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.k8s.create_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods(None, ["install"], "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"], "", "", "vertical",
                                 "vertical")
        exp_err = "Exception when creating pod for ['install'] command(s)"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_reconcile_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.k8s.create_ds',
               MagicMock(side_effect=fake_api_exception)), \
            patch('intel.k8s.get_kubelet_version',
                  MagicMock(return_value=(1, 5))):
        with pytest.raises(SystemExit):
            clusterinit.run_pods(["reconcile"], None, "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"], "", "", "vertical",
                                 "vertical")
        exp_err = "Exception when creating pod for ['reconcile'] command(s)"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_nodereport_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.k8s.create_ds',
               MagicMock(side_effect=fake_api_exception)), \
            patch('intel.k8s.get_kubelet_version',
                  MagicMock(return_value=(1, 5))):
        with pytest.raises(SystemExit):
            clusterinit.run_pods(["nodereport"], None, "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"], "", "", "vertical",
                                 "vertical")
        exp_err = "Exception when creating pod for ['nodereport'] command(s)"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_wait_for_pod_phase_error():
    fake_pod_list_resp = {}
    fake_pod_list_resp["items"] = [
        {"metadata": {"name": "fakepod1"}, "status": {"phase": "Failed"}},
        {"metadata": {"name": "fakepod2"}, "status": {"phase": "Running"}},
        {"metadata": {"name": "fakepod3"}, "status": {"phase": "Failed"}}
    ]
    with patch('intel.k8s.get_pod_list',
               MagicMock(return_value=fake_pod_list_resp)):
        with pytest.raises(RuntimeError) as err:
            clusterinit.wait_for_pod_phase("fakepod1", "Running")
        expected_err_msg = "The Pod fakepod1 went into Failed state"
        assert err.value.args[0] == expected_err_msg

        with pytest.raises(RuntimeError) as err:
            clusterinit.wait_for_pod_phase("fakepod3", "Running")
        expected_err_msg = "The Pod fakepod3 went into Failed state"
        assert err.value.args[0] == expected_err_msg


def test_clusterinit_node_list_host_list():
    fake_node_list = "fakenode1, fakenode2, fakenode3"
    node_list = clusterinit.get_cmk_node_list(fake_node_list, False)
    assert node_list == ["fakenode1", "fakenode2", "fakenode3"]


def test_clusterinit_pass_pull_secrets():
    mock = MagicMock()
    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        with patch('intel.clusterinit.wait_for_pod_phase',
                   MagicMock(return_value=True)):
            clusterinit.cluster_init("fakenode1", False,
                                     "init, discover, install",
                                     "cmk", "Never", "/etc/cmk", "/opt/bin",
                                     "4", "2", "supersecret", "", "vertical",
                                     "vertical")
            called_methods = mock.method_calls
            params = called_methods[0][1]
            pod_spec = params[1]
            assert "imagePullSecrets" in pod_spec["spec"]
            secrets = pod_spec["spec"]["imagePullSecrets"]
            assert len(secrets) == 1
            assert secrets[0]["name"] == "supersecret"


def test_clusterinit_dont_pass_pull_secrets():
    mock = MagicMock()
    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        with patch('intel.clusterinit.wait_for_pod_phase',
                   MagicMock(return_value=True)):
            clusterinit.cluster_init("fakenode1", False,
                                     "init, discover, install",
                                     "cmk", "Never", "/etc/cmk", "/opt/bin",
                                     "4", "2", "", "", "vertical", "vertical")
            called_methods = mock.method_calls
            params = called_methods[0][1]
            pod_spec = params[1]
            assert "imagePullSecrets" not in pod_spec["spec"]


def test_clusterinit_pass_serviceaccountname():
    mock = MagicMock()
    serviceaccount_name = "testSAname"
    with patch('intel.k8s.client_from_config', MagicMock(return_value=mock)):
        with patch('intel.clusterinit.wait_for_pod_phase',
                   MagicMock(return_value=True)):
            clusterinit.cluster_init("fakenode1", False,
                                     "init, discover, install",
                                     "cmk", "Never", "/etc/cmk", "/opt/bin",
                                     "4", "2", "", serviceaccount_name,
                                     "vertical", "vertical")
            called_methods = mock.method_calls
            params = called_methods[0][1]
            pod_spec = params[1]
            assert "serviceAccountName" in pod_spec["spec"]
            sa_name_in_spec = pod_spec["spec"]["serviceAccountName"]
            assert sa_name_in_spec == serviceaccount_name


def test_clusterinit_dont_pass_serviceaccountname():
    mock = MagicMock()
    with patch('intel.k8s.client_from_config', MagicMock(return_value=mock)):
        with patch('intel.clusterinit.wait_for_pod_phase',
                   MagicMock(return_value=True)):
            clusterinit.cluster_init("fakenode1", False,
                                     "init, discover, install",
                                     "cmk", "Never", "/etc/cmk", "/opt/bin",
                                     "4", "2", "", "", "vertical", "vertical")
            called_methods = mock.method_calls
            params = called_methods[0][1]
            pod_spec = params[1]
            assert "serviceAccountName" in pod_spec["spec"]
            sa_name_in_spec = pod_spec["spec"]["serviceAccountName"]
            assert sa_name_in_spec == ""


def test_clusterinit_update_pod_with_init_container():
    pod_passed = k8sclient.V1Pod(
        metadata=k8sclient.V1ObjectMeta(annotations={}),
        spec=k8sclient.V1PodSpec(),
        status=k8sclient.V1PodStatus()).to_dict()
    cmd = "cmd"
    cmk_img = "cmk_img"
    cmk_img_pol = "policy"
    args = "argument"
    clusterinit.update_pod_with_init_container(pod_passed, cmd, cmk_img,
                                               cmk_img_pol,
                                               args)
    pods = json.loads(pod_passed["metadata"]["annotations"][
                          "pod.beta.kubernetes.io/init-containers"])
    assert len(pods) == 1
    assert pods[0]["name"] == cmd
    assert pods[0]["image"] == cmk_img
    assert pods[0]["imagePullPolicy"] == cmk_img_pol
    assert args in pods[0]["args"]

    second_cmd = "cmd2"
    second_img = cmk_img
    second_img_pol = "Always"
    second_args = ["arg1", "arg2"]
    clusterinit.update_pod_with_init_container(pod_passed, second_cmd,
                                               second_img,
                                               second_img_pol,
                                               second_args)

    pods = json.loads(pod_passed["metadata"]["annotations"][
                          "pod.beta.kubernetes.io/init-containers"])
    assert len(pods) == 2
