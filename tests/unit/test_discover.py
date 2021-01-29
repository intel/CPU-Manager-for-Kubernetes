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

from intel import discover, config
from kubernetes.client.rest import ApiException as K8sApiException
import pytest
from unittest.mock import patch, MagicMock


class MockConfig(config.Config):

    def __init__(self, conf):
        self.cm_name = "fake-name"
        self.owner = "fake-owner"
        self.c_data = conf

    def lock(self):
        return

    def unlock(self):
        return


def get_bad_config():
    conf = config.Conf()
    for pool in ["shared", "infra"]:
        if pool == "exclusive":
            conf.add_pool(True, pool)
        else:
            conf.add_pool(False, pool)
        for socket in ["0", "1"]:
            conf.pools[pool].add_socket(socket)
            for core_list in ["0,16", "1,17"]:
                conf.pools[pool].sockets[socket].add_core_list(core_list)
                for task in ["1234"]:
                    s = conf.pools[pool].sockets[socket]
                    s.core_lists[core_list].add_task(task)

    return conf


def get_fake_config():
    conf = config.Conf()
    for pool in ["exclusive", "shared", "infra"]:
        if pool == "exclusive":
            conf.add_pool(True, pool)
        else:
            conf.add_pool(False, pool)
        for socket in ["0", "1"]:
            conf.pools[pool].add_socket(socket)
            for core_list in ["0,16", "1,17"]:
                conf.pools[pool].sockets[socket].add_core_list(core_list)
                for task in ["1234"]:
                    s = conf.pools[pool].sockets[socket]
                    s.core_lists[core_list].add_task(task)

    return conf


@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_discover_no_exclusive():
    c = MockConfig(get_bad_config())
    with patch('intel.config.Config', MagicMock(return_value=c)):
        with pytest.raises(KeyError) as err:
            discover.add_node_oir("fake-namespace")
        expected_msg = "Exclusive pool does not exist"
        assert err.value.args[0] == expected_msg


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


@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_discover_oir_update_failure(caplog):
    c = MockConfig(get_fake_config())
    with patch('intel.config.Config', MagicMock(return_value=c)):
        fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
        fake_api_exception = K8sApiException(http_resp=fake_http_resp)
        with patch('intel.discover.patch_k8s_node_status',
                   MagicMock(side_effect=fake_api_exception)):
            with pytest.raises(SystemExit):
                discover.add_node_oir("fake-namespace")
            exp_err = "Exception when patching node with OIR"
            exp_log_err = get_expected_log_error(exp_err)
            caplog_tuple = caplog.record_tuples
            assert caplog_tuple[0][2] == exp_log_err


def test_discover_add_label_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.discover.patch_k8s_node',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            discover.add_node_label()
        exp_err = "Exception when labeling the node"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[0][2] == exp_log_err


def test_discover_add_taint_failure1(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.discover.get_k8s_node',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            discover.add_node_taint()
        exp_err = "Exception when getting the node obj"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[0][2] == exp_log_err


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.5.2"))
def test_discover_add_taint_failure2(caplog):
    fake_node_resp = {
            "metadata": {
                "annotations": {
                }
            }
        }
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.discover.get_k8s_node',
               MagicMock(return_value=fake_node_resp)), \
            patch('intel.discover.patch_k8s_node',
                  MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            discover.add_node_taint()
        exp_err = "Exception when tainting the node"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[0][2] == exp_log_err


@patch('os.environ', MagicMock(return_value="fake-pod"))
@patch('intel.k8s.get_node_from_pod',
       MagicMock(return_value="fake-node"))
def test_add_node_er_failure(caplog):
    c = MockConfig(get_fake_config())
    with patch('intel.config.Config', MagicMock(return_value=c)):
        fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
        fake_api_exception = K8sApiException(http_resp=fake_http_resp)
        with patch('intel.discover.patch_k8s_node_status',
                   MagicMock(side_effect=fake_api_exception)):
            with pytest.raises(SystemExit):
                discover.add_node_er("fake-namespace")
            exp_err = "Exception when patching node with OIR"
            exp_log_err = get_expected_log_error(exp_err)
            caplog_tuple = caplog.record_tuples
            assert caplog_tuple[-2][2] == exp_log_err
            assert caplog_tuple[-1][2] == "Aborting discover ..."


@patch('intel.k8s.get_kube_version', MagicMock(return_value='v1.10.0'))
def test_discover_version_check(caplog):
    with patch('intel.discover.add_node_er') as mock_er, \
            patch('intel.discover.add_node_oir') as mock_oir, \
            patch('intel.discover.add_node_label') as mock_label, \
            patch('intel.discover.add_node_taint') as mock_taint:

        discover.discover("fake-namespace")

        assert mock_er.called
        assert not mock_oir.called
        assert mock_label.called
        assert mock_taint.called


@patch('intel.k8s.get_kube_version', MagicMock(return_value='v1.6.0'))
def test_discover_version_check2(caplog):
    with patch('intel.discover.add_node_er') as mock_er, \
            patch('intel.discover.add_node_oir') as mock_oir, \
            patch('intel.discover.add_node_label') as mock_label, \
            patch('intel.discover.add_node_taint') as mock_taint:

        discover.discover("fake-namespace")

        assert not mock_er.called
        assert mock_oir.called
        assert mock_label.called
        assert mock_taint.called


@patch('intel.k8s.get_kube_version', MagicMock(return_value='v1.8.0'))
def test_discover_version_check3(caplog):
    with patch('intel.discover.add_node_er') as mock_er, \
            patch('intel.discover.add_node_oir') as mock_oir, \
            patch('intel.discover.add_node_label') as mock_label, \
            patch('intel.discover.add_node_taint') as mock_taint:

        with pytest.raises(SystemExit):
            discover.discover("fake-namespace")

        # no resources should be created on unsupported cluster
        assert not mock_er.called
        assert not mock_oir.called
        assert not mock_label.called
        assert not mock_taint.called
