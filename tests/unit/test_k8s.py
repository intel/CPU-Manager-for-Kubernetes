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
from unittest.mock import patch, MagicMock

import pytest
from kubernetes import client as k8sclient
from kubernetes.config import ConfigException
from urllib3.util.retry import MaxRetryError

from intel import clusterinit, k8s


def test_k8s_node_list_all():
    fake_node_list_resp = [
        {"metadata": {"name": "fakenode1"}, "spec": {}},
        {"metadata": {"name": "fakenode2"}, "spec": {}},
        {"metadata": {"name": "fakenode3"}, "spec": {}}
    ]
    with patch('intel.k8s.get_node_list',
               MagicMock(return_value=fake_node_list_resp)):
        node_list = clusterinit.get_kcm_node_list(None, True)
        assert node_list == ["fakenode1", "fakenode2", "fakenode3"]


def test_k8s_get_compute_nodes():
    fake_node_list = [
        {"metadata": {"name": "fakenode1"}, "spec": {"unschedulable": True}},
        {"metadata": {"name": "fakenode2"}, "spec": {"unschedulable": False}},
        {"metadata": {"name": "fakenode3"}, "spec": {}}
    ]
    with patch('intel.k8s.get_node_list',
               MagicMock(return_value=fake_node_list)):
        node_list = k8s.get_compute_nodes(None)
        resv_list = list(map(lambda node: node["metadata"]["name"], node_list))
        assert resv_list == ["fakenode2", "fakenode3"]


def test_k8s_set_label():
    mock = MagicMock()

    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.set_node_label(None, "fakenode1", "foo", "bar")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "patch_node"
        params = called_methods[0][1]
        assert params[0] == "fakenode1"
        assert params[1][0]["op"] == "add"
        assert params[1][0]["path"] == "/metadata/labels/foo"
        assert params[1][0]["value"] == "bar"


def test_k8s_unset_label():
    mock = MagicMock()

    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.unset_node_label(None, "fakenode1", "foo")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "patch_node"
        params = called_methods[0][1]
        assert params[0] == "fakenode1"
        assert params[1][0]["op"] == "remove"
        assert params[1][0]["path"] == "/metadata/labels/foo"


def test_k8s_create_namespace():
    mock = MagicMock()

    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.create_namespace(None, "test_namespace")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "create_namespace"
        params = called_methods[0][1]
        assert params[0].metadata["name"] == "test_namespace"


def test_k8s_delete_namespace():
    mock = MagicMock()

    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.delete_namespace(None, "test_namespace")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "delete_namespace"
        params = called_methods[0][1]
        assert params[0] == "test_namespace"


def test_k8s_delete_pod():
    mock = MagicMock()

    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.delete_pod(None, "test_pod", ns_name="test_namespace")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "delete_namespaced_pod"
        params = called_methods[0][1]
        assert params[0] == "test_pod"
        assert params[1] == "test_namespace"


def test_k8s_create_pod():
    mock = MagicMock()

    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.get_pod_list(None)
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "list_pod_for_all_namespaces"


def test_k8s_pod_list():
    mock = MagicMock()

    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.create_pod(None, "pod_spec", ns_name="test_namespace")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "create_namespaced_pod"
        params = called_methods[0][1]
        assert params[0] == "test_namespace"
        assert params[1] == "pod_spec"


def test_k8s_node_list_with_label_selector():
    mock = MagicMock()
    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.get_node_list(None, label_selector="some_label")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "list_node"
        kargs = called_methods[0][2]
        assert kargs["label_selector"] == "some_label"


def test_k8s_node_list_wo_label_selector():
    mock = MagicMock()
    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.get_node_list(None)
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "list_node"
        kargs = called_methods[0][2]
        assert "label_selector" not in kargs


def test_k8s_get_namespaces():
    mock = MagicMock()
    with patch('intel.k8s.client_from_config',
               MagicMock(return_value=mock)):
        k8s.get_namespaces(None)
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "list_namespace"
        assert len(called_methods[0][1]) == 0
        assert len(called_methods[0][2]) == 0


def test_k8s_core_client_from_config():
    with pytest.raises(ConfigException) as err:
        k8s.client_from_config(None)
        # Client from in-cluster configuration should throws error if it's not
        # executed within pod in Kubernetes cluster.
        assert err is not None

    # If we use valid configuration for Kubernetes client, it should be
    # created.
    config = k8sclient.Configuration()
    config.host = "https://somenonexistedlocation.com:443"
    client = k8s.client_from_config(config)
    with pytest.raises(MaxRetryError) as err:
        # It should when we will use it to call Kubernetes API.
        client.list_node()
        assert err is not None
