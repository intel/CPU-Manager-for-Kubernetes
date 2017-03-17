# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the "Software"), without modification,
# provided the following conditions are met:
#
# * Neither the name of Intel nor the names of its suppliers may be used to
#   endorse or promote products derived from this Software without specific
#   prior written permission.
# * No reverse engineering, decompilation, or disassembly of this Software
#   is permitted.
#
# Limited patent license.  Intel grants you a world-wide, royalty-free,
# non-exclusive license under patents it now or hereafter owns or controls to
# make, have made, use, import, offer to sell and sell ("Utilize") this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  "Third Party Programs" are the files
# listed in the "third-party-programs.txt" text file that is included with the
# Software and may include Intel programs under separate license terms. Third
# Party Programs, even if included with the distribution of the Materials, are
# governed by separate license terms and those license terms solely govern your
# use of those programs.
#
# DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
# DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS
# OR APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR
# DEATH.
#
# LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO
# INDEMNIFIY AND HOLD INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING
# FROM YOUR USE OR UNAUTHORIZED USE OF THE SOFTWARE.
#
# No support.  Intel may make changes to the Software, at any time without
# notice, and is not obligated to support, update or provide training for the
# Software.
#
# Termination. Intel may terminate your right to use the Software in the event
# of your breach of this Agreement and you fail to cure the breach within a
# reasonable period of time.
#
# Feedback.  Should you provide Intel with comments, modifications,
# corrections, enhancements or other input ("Feedback") related to the Software
# Intel will be free to use, disclose, reproduce, license or otherwise
# distribute or exploit the Feedback in its sole discretion without any
# obligations or restrictions of any kind, including without limitation,
# intellectual property rights or licensing obligations.
#
# Compliance with laws.  You agree to comply with all relevant laws and
# regulations governing your use, transfer, import or export (or prohibition
# thereof) of the Software.
#
# Governing law.  All disputes will be governed by the laws of the United
# States of America and the State of Delaware without reference to conflict of
# law principles and subject to the exclusive jurisdiction of the state or
# federal courts sitting in the State of Delaware, and each party agrees that
# it submits to the personal jurisdiction and venue of those courts and waives
# any objections. The United Nations Convention on Contracts for the
# International Sale of Goods (1980) is specifically excluded and will not
# apply to the Software.
import json
import pytest

from intel import clusterinit
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException as K8sApiException
from kubernetes import client as k8sclient


def test_clusterinit_invalid_cmd_list_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "fakecmd1, fakecmd2",
                                 "kcm", "Never", "/etc/kcm", "/opt/bin",
                                 "4", "2", "")
    expected_err_msg = ("KCM command should be one of "
                        "['init', 'discover', 'install', 'reconcile', "
                        "'nodereport']")
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "fakecmd1, init",
                                 "kcm", "Never", "/etc/kcm", "/opt/bin",
                                 "4", "2", "")
    expected_err_msg = ("KCM command should be one of "
                        "['init', 'discover', 'install', 'reconcile', "
                        "'nodereport']")
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure3():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init, fakecmd1, install",
                                 "kcm", "Never", "/etc/kcm", "/opt/bin",
                                 "4", "2", "")
    expected_err_msg = ("KCM command should be one of "
                        "['init', 'discover', 'install', 'reconcile', "
                        "'nodereport']")
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cmd_list_failure4():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "discover, init",
                                 "kcm", "Never", "/etc/kcm", "/opt/bin",
                                 "4", "2", "")
    expected_err_msg = "init command should be run and listed first."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_image_pol():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "fakepol1",
                                 "/etc/kcm", "/opt/bin", "4", "2", "")
    expected_err_msg = ('Image pull policy should be one of '
                        '[\'Never\', \'IfNotPresent\', \'Always\']')
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_dp_cores_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "Never",
                                 "/etc/kcm", "/opt/bin", "-1", "2", "")
    expected_err_msg = "num_dp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_dp_cores_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "Never",
                                 "/etc/kcm", "/opt/bin", "3.5", "2", "")
    expected_err_msg = "num_dp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cp_cores_failure1():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "Never",
                                 "/etc/kcm", "/opt/bin", "1", "2.5", "")
    expected_err_msg = "num_cp_cores cores should be a positive integer."
    assert err.value.args[0] == expected_err_msg


def test_clusterinit_invalid_cp_cores_failure2():
    with pytest.raises(RuntimeError) as err:
        clusterinit.cluster_init("fakenode1", False, "init", "kcm", "Never",
                                 "/etc/kcm", "/opt/bin", "1", "10.5", "")
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
                                 "2", "2", ["fakenode"], "")
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
                                 "2", ["fakenode"], "")
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
                                 "2", ["fakenode"], "")
        exp_err = "Exception when creating pod for ['install'] command(s)"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_reconcile_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.k8s.create_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods(["reconcile"], None, "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"], "")
        exp_err = "Exception when creating pod for ['reconcile'] command(s)"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[1][2] == exp_log_err


def test_clusterinit_run_cmd_pods_nodereport_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.k8s.create_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            clusterinit.run_pods(["nodereport"], None, "fake_img", "Never",
                                 "fake-conf-dir", "fake-install-dir", "2",
                                 "2", ["fakenode"], "")
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
    node_list = clusterinit.get_kcm_node_list(fake_node_list, False)
    assert node_list == ["fakenode1", "fakenode2", "fakenode3"]


def test_clusterinit_pass_pull_secrets():
    mock = MagicMock()
    with patch('intel.k8s.client_from_config', MagicMock(return_value=mock)):
        with patch('intel.clusterinit.wait_for_pod_phase',
                   MagicMock(return_value=True)):
            clusterinit.cluster_init("fakenode1", False,
                                     "init, discover, install",
                                     "kcm", "Never", "/etc/kcm", "/opt/bin",
                                     "4", "2", "supersecret")
            called_methods = mock.method_calls
            params = called_methods[0][1]
            pod_spec = params[1]
            assert "imagePullSecrets" in pod_spec["spec"]
            secrets = pod_spec["spec"]["imagePullSecrets"]
            assert len(secrets) == 1
            assert secrets[0]["name"] == "supersecret"


def test_clusterinit_dont_pass_pull_secrets():
    mock = MagicMock()
    with patch('intel.k8s.client_from_config', MagicMock(return_value=mock)):
        with patch('intel.clusterinit.wait_for_pod_phase',
                   MagicMock(return_value=True)):
            clusterinit.cluster_init("fakenode1", False,
                                     "init, discover, install",
                                     "kcm", "Never", "/etc/kcm", "/opt/bin",
                                     "4", "2", "")
            called_methods = mock.method_calls
            params = called_methods[0][1]
            pod_spec = params[1]
            assert "imagePullSecrets" not in pod_spec["spec"]


def test_clusterinit_update_pod_with_init_container():
    pod_passed = k8sclient.V1Pod(
        metadata=k8sclient.V1ObjectMeta(annotations={}),
        spec=k8sclient.V1PodSpec(),
        status=k8sclient.V1PodStatus()).to_dict()
    cmd = "cmd"
    kcm_img = "kcm_img"
    kcm_img_pol = "policy"
    args = "argument"
    clusterinit.update_pod_with_init_container(pod_passed, cmd, kcm_img,
                                               kcm_img_pol,
                                               args)
    pods = json.loads(pod_passed["metadata"]["annotations"][
                          "pod.beta.kubernetes.io/init-containers"])
    assert len(pods) == 1
    assert pods[0]["name"] == cmd
    assert pods[0]["image"] == kcm_img
    assert pods[0]["imagePullPolicy"] == kcm_img_pol
    assert args in pods[0]["args"]

    second_cmd = "cmd2"
    second_img = kcm_img
    second_img_pol = "Always"
    second_args = ["arg1", "arg2"]
    clusterinit.update_pod_with_init_container(pod_passed, second_cmd,
                                               second_img,
                                               second_img_pol,
                                               second_args)

    pods = json.loads(pod_passed["metadata"]["annotations"][
                          "pod.beta.kubernetes.io/init-containers"])
    assert len(pods) == 2
