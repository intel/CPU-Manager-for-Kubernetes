# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the “Software”), without modification,
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
# make, have made, use, import, offer to sell and sell (“Utilize”) this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  “Third Party Programs” are the files
# listed in the “third-party-programs.txt” text file that is included with the
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
# corrections, enhancements or other input (“Feedback”) related to the Software
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

from .. import helpers
from intel import proc, uninstall, third_party
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


def test_uninstall_remove_node_kcm_oir_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, "fake reason",
                                      "{\"message\":\"fake message\"}")
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)

    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(side_effect=fake_api_exception)):
        with pytest.raises(SystemExit):
            uninstall.remove_node_kcm_oir()
        patch_path = "/status/capacity/" \
                     "pod.alpha.kubernetes.io~1opaque-int-resource-kcm"
        exp_err = "Aborting uninstall: " \
                  "Exception when removing OIR \"{}\"".format(patch_path)
        exp_log_err = get_expected_log_error(exp_err, fake_http_resp)
        caplog_tuple = caplog.record_tuples

        assert caplog_tuple[-1][2] == exp_log_err


def test_remove_report_success(caplog):
    fake_tpr_report = MagicMock()
    fake_tpr_report.remove.return_value = 0

    with patch('kubernetes.config.load_incluster_config',
               MagicMock(return_value=0)),\
            patch('kubernetes.client.ExtensionsV1beta1Api',
                  MagicMock(return_value=0)), \
            patch.object(third_party.ThirdPartyResourceType, 'create',
                         MagicMock(return_value=fake_tpr_report)):
        uninstall.remove_report("NodeReport")
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == "\"NodeReport\" for node \"{}\" " \
                                      "removed.".format(os.getenv("NODE_NAME"))


# Remove success due to not existing report
def test_remove_report_success2(caplog):
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

        uninstall.remove_report("NodeReport")
        caplog_tuple = caplog.record_tuples
        assert \
            caplog_tuple[-2][2] == "\"NodeReport\" for node \"{}\" does" \
                                   " not exist.".format(os.getenv("NODE_NAME"))
        assert \
            caplog_tuple[-1][2] == "\"NodeReport\" for node \"{}\" " \
                                   "removed.".format(os.getenv("NODE_NAME"))


def test_remove_report_failure(caplog):
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
            uninstall.remove_report("NodeReport")
        caplog_tuple = caplog.record_tuples
        exp_err = "Aborting uninstall: " \
                  "Exception when removing third party resource \"NodeReport\""
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
        patch_path = '/metadata/labels/kcm.intel.com~1kcm-node'
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
        patch_path = '/metadata/labels/kcm.intel.com~1kcm-node'
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
        patch_path = '/metadata/labels/kcm.intel.com~1kcm-node'
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
        uninstall.remove_node_kcm_oir()
        caplog_tuple = caplog.record_tuples
        patch_path = '/status/capacity/pod.alpha.kubernetes.' \
                     'io~1opaque-int-resource-kcm'
        assert \
            caplog_tuple[-2][2] == "KCM oir \"{}\" does not " \
                                   "exist.".format(patch_path)
        assert \
            caplog_tuple[-1][2] == "Removed node oir " \
                                   "\"{}\".".format(patch_path)


# Test removing existing oir
def test_uninstall_remove_node_oir_success2(caplog):
    with patch('intel.discover.patch_k8s_node_status',
               MagicMock(return_value=0)):
        uninstall.remove_node_kcm_oir()
        caplog_tuple = caplog.record_tuples
        patch_path = '/status/capacity/pod.alpha.kubernetes.' \
                     'io~1opaque-int-resource-kcm'
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
    # Pid in below path is not in kcm conf dir
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
    # Pid in below path is present in kcm conf dir
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
    fake_binary_path = os.path.join(temp_dir, "kcm")
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
    exp_log = "kcm binary from \"{}\" removed successfully.".format(
        temp_dir)
    assert caplog_tuple[-1][2] == exp_log


def test_remove_binary_failure(caplog):
    temp_dir = tempfile.mkdtemp()
    fake_binary_path = os.path.join(temp_dir, "kcm_wrong_name")
    helpers.execute(
        "touch",
        [fake_binary_path]
    )
    with pytest.raises(SystemExit):
        uninstall.remove_binary(temp_dir)

    caplog_tuple = caplog.record_tuples
    exp_log = "Could not found kcm binary in \"{}\"."\
        .format(temp_dir)

    exp_log2 = "Wrong path or file has already been removed."
    assert caplog_tuple[-2][2] == exp_log
    assert caplog_tuple[-1][2] == exp_log2
