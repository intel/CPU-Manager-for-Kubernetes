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
        node_list = clusterinit.get_cmk_node_list(None, True)
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

    with patch('intel.k8s.core_client_from_config',
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

    with patch('intel.k8s.core_client_from_config',
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

    with patch('intel.k8s.core_client_from_config',
               MagicMock(return_value=mock)):
        k8s.create_namespace(None, "test_namespace")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "create_namespace"
        params = called_methods[0][1]
        assert params[0].metadata["name"] == "test_namespace"


def test_k8s_delete_namespace():
    mock = MagicMock()

    with patch('intel.k8s.core_client_from_config',
               MagicMock(return_value=mock)):
        k8s.delete_namespace(None, "test_namespace")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "delete_namespace"
        params = called_methods[0][1]
        assert params[0] == "test_namespace"


def test_k8s_delete_pod():
    mock = MagicMock()

    with patch('intel.k8s.core_client_from_config',
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

    with patch('intel.k8s.core_client_from_config',
               MagicMock(return_value=mock)):
        k8s.get_pod_list(None)
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "list_pod_for_all_namespaces"


def test_k8s_pod_list():
    mock = MagicMock()

    with patch('intel.k8s.core_client_from_config',
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
    with patch('intel.k8s.core_client_from_config',
               MagicMock(return_value=mock)):
        k8s.get_node_list(None, label_selector="some_label")
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "list_node"
        kargs = called_methods[0][2]
        assert kargs["label_selector"] == "some_label"


def test_k8s_node_list_wo_label_selector():
    mock = MagicMock()
    with patch('intel.k8s.core_client_from_config',
               MagicMock(return_value=mock)):
        k8s.get_node_list(None)
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "list_node"
        kargs = called_methods[0][2]
        assert "label_selector" not in kargs


def test_k8s_get_namespaces():
    mock = MagicMock()
    with patch('intel.k8s.core_client_from_config',
               MagicMock(return_value=mock)):
        k8s.get_namespaces(None)
        called_methods = mock.method_calls
        assert len(called_methods) == 1
        assert called_methods[0][0] == "list_namespace"
        assert len(called_methods[0][1]) == 0
        assert len(called_methods[0][2]) == 0


def test_k8s_core_client_from_config():
    with pytest.raises(ConfigException) as err:
        k8s.core_client_from_config(None)
        # Client from in-cluster configuration should throws error if it's not
        # executed within pod in Kubernetes cluster.
        assert err is not None

    # If we use valid configuration for Kubernetes client, it should be
    # created.
    config = k8sclient.Configuration()
    config.host = "https://somenonexistedlocation.com:443"
    client = k8s.core_client_from_config(config)
    with pytest.raises(MaxRetryError) as err:
        # It should when we will use it to call Kubernetes API.
        client.list_node()
        assert err is not None
