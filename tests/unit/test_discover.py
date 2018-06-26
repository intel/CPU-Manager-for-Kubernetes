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

from .. import helpers
from intel import discover
from kubernetes.client.rest import ApiException as K8sApiException
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock


def test_discover_no_dp():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "discover")

    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )
    helpers.execute(
        "rm",
        ["-r",
         "{}".format(os.path.join(conf_dir, "pools", "dataplane"))]
    )

    with pytest.raises(KeyError) as err:
        discover.add_node_oir(conf_dir)
    expected_msg = "Dataplane pool does not exist"
    assert err.value.args[0] == expected_msg


def test_discover_no_cldp():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "discover")

    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )
    helpers.execute(
        "rm",
        ["-r",
         "{}".format(os.path.join(conf_dir, "pools",
                                  "dataplane", "*"))]
    )

    with pytest.raises(KeyError) as err:
        discover.add_node_oir(conf_dir)
    expected_msg = "No CPU list in dataplane pool"
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


def test_discover_oir_update_failure(caplog):
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "discover")

    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )

    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            discover.add_node_oir(conf_dir)
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


@patch('intel.k8s.get_kubelet_version', MagicMock(return_value="v1.5.1"))
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


def test_add_node_er_failure(caplog):
    conf_dir = helpers.conf_dir("ok")
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            discover.add_node_er(conf_dir)
        exp_err = "Exception when patching node with OIR"
        exp_log_err = get_expected_log_error(exp_err)
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-2][2] == exp_log_err
        assert caplog_tuple[-1][2] == "Aborting discover ..."


@patch('intel.k8s.get_kubelet_version', MagicMock(return_value='v1.10.0'))
def test_discover_version_check(caplog):
    conf_dir = helpers.conf_dir("ok")
    with patch('intel.discover.add_node_er') as mock_er, \
            patch('intel.discover.add_node_oir') as mock_oir, \
            patch('intel.discover.add_node_label') as mock_label, \
            patch('intel.discover.add_node_taint') as mock_taint:

        discover.discover(conf_dir)

        assert mock_er.called
        assert not mock_oir.called
        assert mock_label.called
        assert mock_taint.called


@patch('intel.k8s.get_kubelet_version', MagicMock(return_value='v1.6.0'))
def test_discover_version_check2(caplog):
    conf_dir = helpers.conf_dir("ok")
    with patch('intel.discover.add_node_er') as mock_er, \
            patch('intel.discover.add_node_oir') as mock_oir, \
            patch('intel.discover.add_node_label') as mock_label, \
            patch('intel.discover.add_node_taint') as mock_taint:

        discover.discover(conf_dir)

        assert not mock_er.called
        assert mock_oir.called
        assert mock_label.called
        assert mock_taint.called


@patch('intel.k8s.get_kubelet_version', MagicMock(return_value='v1.8.0'))
def test_discover_version_check3(caplog):
    conf_dir = helpers.conf_dir("ok")
    with patch('intel.discover.add_node_er') as mock_er, \
            patch('intel.discover.add_node_oir') as mock_oir, \
            patch('intel.discover.add_node_label') as mock_label, \
            patch('intel.discover.add_node_taint') as mock_taint:

        with pytest.raises(SystemExit):
            discover.discover(conf_dir)

        # no resources should be created on unsupported cluster
        assert not mock_er.called
        assert not mock_oir.called
        assert not mock_label.called
        assert not mock_taint.called


def test_discover_add_node_er_no_dp_pool_failure():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "discover")

    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )
    helpers.execute(
        "rm",
        ["-r",
         "{}".format(os.path.join(conf_dir, "pools", "dataplane"))]
    )

    with pytest.raises(KeyError, message="Dataplane pool does not exist"):
        discover.add_node_er(conf_dir)


def test_discover_add_node_er_no_dp_cores_failure():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "discover")

    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )
    helpers.execute(
        "rm",
        ["-r",
         "{}".format(os.path.join(conf_dir, "pools", "dataplane", "0"))]
    )

    with pytest.raises(KeyError, message="No CPU list in dataplane pool"):
        discover.add_node_er(conf_dir)
