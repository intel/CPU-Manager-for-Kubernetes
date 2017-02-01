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
