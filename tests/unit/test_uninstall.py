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
from intel import custom_resource, proc, uninstall, third_party
from kubernetes.client.rest import ApiException as K8sApiException
import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock


class FakeHTTPResponse:
    def __init__(self, status=None, reason=None, data=None):
        self.status = status
        self.reason = reason
        self.data = data

    def getheaders(self):
        return {"fakekey": "fakeval"}


def get_expected_log_error(err_msg, http_response):
    return "{}: ({})\n" \
          "Reason: {}\n" \
          "HTTP response headers: {}\n" \
          "HTTP response body: {}\n".format(
            err_msg,
            str(http_response.status),
            http_response.reason,
            str(http_response.getheaders()),
            http_response.data)


def test_uninstall_remove_node_cmk_oir_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason",
                                      "{\"message\":\"fake message\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            uninstall.remove_node_cmk_oir()
        patch_path = "/status/capacity/" \
                     "pod.alpha.kubernetes.io~1opaque-int-resource-cmk"
        exp_err = "Aborting uninstall: " \
                  "Exception when removing OIR \"{}\"".format(patch_path)
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        caplog_tuple = caplog.record_tuples

        assert caplog_tuple[-1][2] == exp_log_err


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.6.3"))
def test_remove_all_report_tpr_success(caplog):
    mock = MagicMock()
    mock.remove.return_value = 0

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)), \
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(third_party.ThirdPartyResourceType,
                         'create',
                         MagicMock(return_value=mock)):
        uninstall.remove_all_report()
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == "\"Reconcilereport\" for node \"{}\" " \
                                      "removed.".format(os.getenv("NODE_NAME"))
        assert caplog_tuple[-3][2] == "\"Nodereport\" for node \"{}\" " \
                                      "removed.".format(os.getenv("NODE_NAME"))


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.7.4"))
def test_remove_all_report_crd_success(caplog):
    mock = MagicMock()
    mock.remove.return_value = 0

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)), \
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(custom_resource.CustomResourceDefinitionType,
                         'create',
                         MagicMock(return_value=mock)):
        uninstall.remove_all_report()
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == "\"cmk-reconcilereport\" for node " \
                                      "\"{}\" removed."\
            .format(os.getenv("NODE_NAME"))
        assert caplog_tuple[-3][2] == "\"cmk-nodereport\" for node \"{}\" " \
                                      "removed.".format(os.getenv("NODE_NAME"))


def test_remove_report_tpr_success(caplog):
    fake_tpr_report = MagicMock()
    fake_tpr_report.remove.return_value = 0

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)),\
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(third_party.ThirdPartyResourceType, 'create',
                         MagicMock(return_value=fake_tpr_report)):
        uninstall.remove_report_tpr("NodeReport")
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == "\"NodeReport\" for node \"{}\" " \
                                      "removed.".format(os.getenv("NODE_NAME"))


# Remove success due to not existing report
def test_remove_report_tpr_success2(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"message\":\"fake message\"}",
                                      "{\"reason\":\"NotFound\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    fake_tpr_report = MagicMock()
    fake_tpr_report.remove.side_effect = fake_api_exception

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)),\
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(third_party.ThirdPartyResourceType, 'create',
                         MagicMock(return_value=fake_tpr_report)):

        uninstall.remove_report_tpr("NodeReport")
        caplog_tuple = caplog.record_tuples
        assert \
            caplog_tuple[-2][2] == "\"NodeReport\" for node \"{}\" does" \
                                   " not exist.".format(os.getenv("NODE_NAME"))
        assert \
            caplog_tuple[-1][2] == "\"NodeReport\" for node \"{}\" " \
                                   "removed.".format(os.getenv("NODE_NAME"))


def test_remove_report_tpr_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"message\":\"fake message\"}",
                                      "{\"reason\":\"WrongReason\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    fake_tpr_report = MagicMock()
    fake_tpr_report.remove.side_effect = fake_api_exception

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)),\
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(third_party.ThirdPartyResourceType, 'create',
                         MagicMock(return_value=fake_tpr_report)):
        with pytest.raises(SystemExit):
            uninstall.remove_report_tpr("NodeReport")
        caplog_tuple = caplog.record_tuples
        exp_err = "Aborting uninstall: " \
                  "Exception when removing third party resource \"NodeReport\""
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        assert caplog_tuple[-1][2] == exp_log_err


def test_remove_report_crd_success(caplog):
    fake_crd_report = MagicMock()
    fake_crd_report.remove.return_value = 0

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)),\
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(custom_resource.CustomResourceDefinitionType,
                         'create',
                         MagicMock(return_value=fake_crd_report)):
        uninstall.remove_report_crd("cmk-nodereport", ["cmk-nr"])
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == "\"cmk-nodereport\" for node \"{}\" " \
                                      "removed.".format(os.getenv("NODE_NAME"))


# Remove success due to not existing report
def test_remove_report_crd_success2(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"message\":\"fake message\"}",
                                      "{\"reason\":\"NotFound\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    fake_crd_report = MagicMock()
    fake_crd_report.remove.side_effect = fake_api_exception

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)),\
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(custom_resource.CustomResourceDefinitionType,
                         'create',
                         MagicMock(return_value=fake_crd_report)):

        uninstall.remove_report_crd("cmk-nodereport", ["cmk-nr"])
        caplog_tuple = caplog.record_tuples
        assert \
            caplog_tuple[-2][2] == "\"cmk-nodereport\" for node \"{}\" does "\
                                   "not exist.".format(os.getenv("NODE_NAME"))
        assert \
            caplog_tuple[-1][2] == "\"cmk-nodereport\" for node \"{}\" " \
                                   "removed.".format(os.getenv("NODE_NAME"))


def test_remove_report_crd_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"message\":\"fake message\"}",
                                      "{\"reason\":\"WrongReason\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    fake_crd_report = MagicMock()
    fake_crd_report.remove.side_effect = fake_api_exception

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)),\
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(custom_resource.CustomResourceDefinitionType,
                         'create',
                         MagicMock(return_value=fake_crd_report)):
        with pytest.raises(SystemExit):
            uninstall.remove_report_crd("cmk-nodereport", ["cmk-nr"])
        caplog_tuple = caplog.record_tuples
        exp_err = "Aborting uninstall: " \
                  "Exception when removing custom resource definition " \
                  "\"cmk-nodereport\""
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        assert caplog_tuple[-1][2] == exp_log_err


def test_uninstall_remove_node_taint_failure1(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason", "fake body")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    node_name = os.getenv("NODE_NAME")

    with patch('intel.discover.get_k8s_node',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            uninstall.remove_node_taint()
        exp_err = "Aborting uninstall: Exception when getting the " \
                  "node \"{}\" obj".format(node_name)
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        caplog_tuple = caplog.record_tuples

        assert caplog_tuple[-1][2] == exp_log_err


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.5.1"))
def test_uninstall_remove_node_taint_failure2(caplog):
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
            uninstall.remove_node_taint()
        patch_path = '/metadata/annotations/' \
                     'scheduler.alpha.kubernetes.io~1taints'
        exp_err = "Aborting uninstall: " \
                  "Exception when removing taint \"{}\"".format(patch_path)
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        caplog_tuple = caplog.record_tuples

        assert caplog_tuple[-1][2] == exp_log_err


# Test removing non existing label
def test_uninstall_remove_node_label_success(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason",
                                      "{\"message\":\"nonexistant\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    with patch('intel.discover.patch_k8s_node',
               MagicMock(side_effect=fake_api_exception)):
        uninstall.remove_node_label()
        caplog_tuple = caplog.record_tuples
        patch_path = '/metadata/labels/cmk.intel.com~1cmk-node'
        exp_str = "Removed node label \"{}\".".format(patch_path)
        exp_str2 = "Label \"{}\" does not exist.".format(patch_path)
        assert caplog_tuple[-2][2] == exp_str2
        assert caplog_tuple[-1][2] == exp_str


# Test removing existing label
def test_uninstall_remove_node_label_success2(caplog):
    with patch('intel.discover.patch_k8s_node',
               MagicMock(return_value=0)):
        uninstall.remove_node_label()
        caplog_tuple = caplog.record_tuples
        patch_path = '/metadata/labels/cmk.intel.com~1cmk-node'
        exp_str = "Removed node label \"{}\".".format(patch_path)
        assert caplog_tuple[-1][2] == exp_str


def test_uninstall_remove_node_label_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason",
                                      "{\"message\":\"fake message\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    with patch('intel.discover.patch_k8s_node',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            uninstall.remove_node_label()
        patch_path = '/metadata/labels/cmk.intel.com~1cmk-node'
        exp_err = "Aborting uninstall: Exception when removing node label" \
                  " \"{}\"".format(patch_path)
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        caplog_tuple = caplog.record_tuples

        assert caplog_tuple[-1][2] == exp_log_err


# Test removing non existing oir
def test_uninstall_remove_node_oir_success(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason",
                                      "{\"message\":\"nonexistant\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(side_effect=fake_api_exception)):
        uninstall.remove_node_cmk_oir()
        caplog_tuple = caplog.record_tuples
        patch_path = '/status/capacity/pod.alpha.kubernetes.' \
                     'io~1opaque-int-resource-cmk'
        assert \
            caplog_tuple[-2][2] == "CMK oir \"{}\" does not " \
                                   "exist.".format(patch_path)
        assert \
            caplog_tuple[-1][2] == "Removed node oir " \
                                   "\"{}\".".format(patch_path)


# Test removing existing oir
def test_uninstall_remove_node_oir_success2(caplog):
    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(return_value=0)):
        uninstall.remove_node_cmk_oir()
        caplog_tuple = caplog.record_tuples
        patch_path = '/status/capacity/pod.alpha.kubernetes.' \
                     'io~1opaque-int-resource-cmk'
        assert \
            caplog_tuple[-1][2] == "Removed node oir " \
                                   "\"{}\".".format(patch_path)


def test_check_remove_lock_file_success(monkeypatch, caplog):
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "ok")
    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )
    # Pid in below path is not in cmk conf dir
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok"))
    uninstall.check_remove_conf_dir(conf_dir)
    caplog_tuple = caplog.record_tuples

    lock_file = os.path.join(conf_dir, "lock")

    with pytest.raises(Exception):
        helpers.execute("stat", ["{}".format(lock_file)])
    assert caplog_tuple[-1][2] == "\"{}\" removed".format(lock_file)


def test_check_remove_conf_dir_failure(monkeypatch, caplog):
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "ok")
    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("ok"),
         "{}".format(conf_dir)]
    )
    # Pid in below path is present in cmk conf dir
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("ok_1_running"))
    with pytest.raises(SystemExit):
        uninstall.check_remove_conf_dir(conf_dir)
    helpers.execute(
        "stat",
        ["{}".format(conf_dir)]
    )
    caplog_tuple = caplog.record_tuples
    exp_str = "Aborting uninstall: Exception when removing \"{}\": There " \
              "are running tasks, check pools in \"{}\"."\
        .format(conf_dir, conf_dir)
    assert caplog_tuple[-1][2] == exp_str


def test_remove_binary_sucess(caplog):
    temp_dir = tempfile.mkdtemp()
    fake_binary_path = os.path.join(temp_dir, "cmk")
    helpers.execute(
        "touch",
        [fake_binary_path]
    )
    uninstall.remove_binary(temp_dir)
    with pytest.raises(Exception):
        helpers.execute(
            "stat",
            [fake_binary_path]
        )
    caplog_tuple = caplog.record_tuples
    exp_log = "cmk binary from \"{}\" removed successfully.".format(
        temp_dir)
    assert caplog_tuple[-1][2] == exp_log


def test_remove_binary_failure(caplog):
    temp_dir = tempfile.mkdtemp()
    fake_binary_path = os.path.join(temp_dir, "cmk_wrong_name")
    helpers.execute(
        "touch",
        [fake_binary_path]
    )
    uninstall.remove_binary(temp_dir)

    caplog_tuple = caplog.record_tuples
    exp_log = "Could not found cmk binary in \"{}\"."\
        .format(temp_dir)

    exp_log2 = "Wrong path or file has already been removed."
    assert caplog_tuple[-2][2] == exp_log
    assert caplog_tuple[-1][2] == exp_log2


def test_delete_cmk_pod_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"message\":\"fake message\"}",
                                      "{\"reason\":\"WrongReason\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    pod_base_name = "cmk-some-cmd-pod"
    with patch('intel.k8s.delete_pod',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            uninstall.delete_cmk_pod(pod_base_name,
                                     postfix=str(os.getenv("NODE_NAME")),
                                     namespace="default")
        caplog_tuple = caplog.record_tuples
        exp_err = "Aborting uninstall: " \
                  "Exception when removing pod \"{}-{}\""\
            .format(pod_base_name, str(os.getenv("NODE_NAME")))
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        assert caplog_tuple[-1][2] == exp_log_err


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.8.0"))
def test_delete_cmk_pod_failure2(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"message\":\"fake message\"}",
                                      "{\"reason\":\"WrongReason\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    pod_base_name = "cmk-some-cmd-ds"
    with patch('intel.k8s.delete_ds',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            uninstall.delete_cmk_pod(pod_base_name,
                                     postfix=str(os.getenv("NODE_NAME")),
                                     namespace="default")
        caplog_tuple = caplog.record_tuples
        exp_err = "Aborting uninstall: " \
                  "Exception when removing pod \"{}-{}\""\
            .format(pod_base_name, str(os.getenv("NODE_NAME")))
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        assert caplog_tuple[-1][2] == exp_log_err


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.8.0"))
def test_delete_cmk_pod_success(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"message\":\"fake message\"}",
                                      "{\"reason\":\"NotFound\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    pod_base_name = "cmk-some-cmd-ds"
    with patch('intel.k8s.delete_ds',
               MagicMock(side_effect=fake_api_exception)):
        uninstall.delete_cmk_pod(pod_base_name,
                                 postfix=str(os.getenv("NODE_NAME")),
                                 namespace="default")
        caplog_tuple = caplog.record_tuples
        assert \
            caplog_tuple[-2][2] == "\"{}-{}\" does not exist".format(
                pod_base_name, str(os.getenv("NODE_NAME")))
        assert \
            caplog_tuple[-1][2] == "\"{}-{}\" deleted".format(
                pod_base_name, str(os.getenv("NODE_NAME")))


def test_delete_cmk_pod_success2(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"message\":\"fake message\"}",
                                      "{\"reason\":\"NotFound\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    pod_base_name = "cmk-some-cmd-pod"
    with patch('intel.k8s.delete_pod',
               MagicMock(side_effect=fake_api_exception)):
        uninstall.delete_cmk_pod(pod_base_name,
                                 postfix=str(os.getenv("NODE_NAME")),
                                 namespace="default")
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-2][2] == "\"{}-{}\" does not exist".format(
                pod_base_name, str(os.getenv("NODE_NAME")))
        assert caplog_tuple[-1][2] == "\"{}-{}\" deleted".format(
                pod_base_name, str(os.getenv("NODE_NAME")))


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.10.0"))
def test_remove_resource_tracking_er_removed(caplog):
    mock = MagicMock()
    with patch('intel.uninstall.remove_node_cmk_er', mock):
        uninstall.remove_resource_tracking()
        assert mock.called


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.6.0"))
def test_remove_resource_tracking_oir_removed(caplog):
    mock = MagicMock()
    with patch('intel.uninstall.remove_node_cmk_oir', mock):
        uninstall.remove_resource_tracking()
        assert mock.called


@patch('intel.k8s.get_kube_version', MagicMock(return_value="v1.8.0"))
def test_remove_resource_tracking_unsupported(caplog):
    uninstall.remove_resource_tracking()
    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == "Unsupported Kubernetes version"


def test_remove_node_cmk_er_success(caplog):
    with patch('intel.discover.patch_k8s_node_status', MagicMock()):
        uninstall.remove_node_cmk_er()
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == "Removed node ERs"


def test_remove_node_cmk_er_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"reason\":\"fake reason\"}",
                                      "{\"message\":\"nonexistant\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(side_effect=fake_api_exception)):
        uninstall.remove_node_cmk_er()
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-2][2] == "CMK ER does not exist."
        assert caplog_tuple[-1][2] == "Removed node ERs"


def test_remove_node_cmk_er_failure2(caplog):
    fake_http_resp = FakeHTTPResponse(500, "{\"reason\":\"fake reason\"}",
                                      "{\"message\":\"fake message\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            uninstall.remove_node_cmk_er()
        caplog_tuple = caplog.record_tuples
        exp_err = "Aborting uninstall: Exception when removing ER: " \
                  "{}".format(fake_api_exception)
        assert caplog_tuple[-1][2] == exp_err


def test_check_remove_conf_dir_failure2(caplog):
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "ok")
    fake_exception = Exception('fake')
    with patch('intel.config.Config', MagicMock(side_effect=fake_exception)):
        with pytest.raises(SystemExit):
            uninstall.check_remove_conf_dir(conf_dir)
        caplog_tuple = caplog.record_tuples
        exp_err = "Aborting uninstall: Unable to read the CMK configuration " \
                  "directory at \"{}\": {}.".format(conf_dir, fake_exception)
        assert caplog_tuple[-1][2] == exp_err
