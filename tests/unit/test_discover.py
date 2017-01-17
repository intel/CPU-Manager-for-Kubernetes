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
