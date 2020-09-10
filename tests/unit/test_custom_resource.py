# Copyright (c) 2018 Intel Corporation
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

import pytest

from intel import custom_resource, k8s
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException as K8sApiException
from http import client


CLIENT_CONFIG = 'intel.k8s.extensions_client_from_config'
CUSTOM_RESOURCE = 'intel.custom_resource.CustomResourceDefinitionType.exists'
CLIENT_API_CALL = 'api_client.call_api'
FAKE_BODY = "fake body"
FAKE_REASON = "fake reason"
CREATED_CUSTOM_RESOURSE = 'intel.custom_resource.CustomResourceDefinition.create'

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


class FakeCRD:
    @staticmethod
    def generate_crd_type():
        v1beta = k8s.extensions_client_from_config()
        fake_type = custom_resource.CustomResourceDefinitionType(
                                     v1beta, "fake_url", "fake_name", ["fake"])
        return fake_type

    @staticmethod
    def generate_crd():
        v1beta = k8s.extensions_client_from_config()
        fake_type = FakeCRD.generate_crd_type()
        fake_crd = custom_resource.CustomResourceDefinition(
                                      v1beta, fake_type, "default", "fake-crd")
        return fake_crd


def test_custom_resource_definition_type_save_success():
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_type = FakeCRD.generate_crd_type()
        with patch(CUSTOM_RESOURCE,
                   MagicMock(side_effect=[False, True])):
            fake_type.save()
        assert mock.method_calls[0][0] == CLIENT_API_CALL
        assert 'POST' in mock.method_calls[0][1]


def test_custom_resource_definition_type_save_failure():
    fake_http_resp = FakeHTTPResponse(500, FAKE_REASON, FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_type = FakeCRD.generate_crd_type()
        mock.api_client.call_api = MagicMock(side_effect=fake_api_exception)
        with pytest.raises(K8sApiException):
            fake_type.save()
        assert mock.method_calls[0][0] == CLIENT_API_CALL
        assert 'POST' in mock.method_calls[0][1]


def test_custom_resource_type_exists_success():
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_type = FakeCRD.generate_crd_type()
        mock.api_client.call_api = MagicMock()
        exists = fake_type.exists()
        assert exists


def test_custom_resource_type_exists_success2():
    fake_http_resp = FakeHTTPResponse(client.NOT_FOUND, FAKE_REASON,
                                      FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    assert fake_api_exception.status == client.NOT_FOUND

    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_type = FakeCRD.generate_crd_type()
        mock.api_client.call_api = MagicMock(side_effect=fake_api_exception)
        exists = fake_type.exists()
        assert not exists


def test_custom_resource_type_exists_failure():
    fake_http_resp = FakeHTTPResponse(500, FAKE_REASON, FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_type = FakeCRD.generate_crd_type()
        mock.api_client.call_api = MagicMock(side_effect=fake_api_exception)
        with pytest.raises(K8sApiException):
            fake_type.exists()


def test_custom_resource_type_create_success():
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_type = FakeCRD.generate_crd_type()
        v1beta = k8s.extensions_client_from_config()
        expected_crd = custom_resource.CustomResourceDefinition(v1beta,
                                                                fake_type,
                                                                "default",
                                                                "fake-crd")
        with patch(CUSTOM_RESOURCE,
                   MagicMock(side_effect=[False, True])):
            result = fake_type.create("fake-crd", namespace="default")
            assert vars(result) == vars(expected_crd)


def test_custom_resource_type_remove_success():
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_type = FakeCRD.generate_crd_type()
        with patch(CUSTOM_RESOURCE,
                   MagicMock(return_value=True)):
            fake_type.remove()
        assert mock.method_calls[0][0] == CLIENT_API_CALL
        assert 'DELETE' in mock.method_calls[0][1]


def test_custom_resource_create_success():
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_crd = FakeCRD.generate_crd()
        fake_crd.create()
        assert mock.method_calls[0][0] == CLIENT_API_CALL
        assert 'POST' in mock.method_calls[0][1]


def test_custom_resource_remove_success():
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_crd = FakeCRD.generate_crd()
        fake_crd.remove()
        assert mock.method_calls[0][0] == CLIENT_API_CALL
        assert 'DELETE' in mock.method_calls[0][1]


def test_custom_resource_save_success():
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_crd = FakeCRD.generate_crd()
        mock_create = MagicMock()
        with patch(CREATED_CUSTOM_RESOURSE,
                   mock_create):
            fake_crd.save()
        assert mock_create.called


def test_custom_resource_save_crd_not_ready_failure(caplog):
    fake_http_resp = FakeHTTPResponse(client.NOT_FOUND, FAKE_REASON,
                                      FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_crd = FakeCRD.generate_crd()
        mock_create = MagicMock(side_effect=fake_api_exception)
        with patch(CREATED_CUSTOM_RESOURSE,
                   mock_create):
            fake_crd.save()
        assert mock_create.called
        exp_log_err = ("Custom Resource Definition is not ready yet. "
                       "Report will be skipped")
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == exp_log_err


def test_third_party_resource_save_api_blocked_failure(caplog):
    fake_http_resp = FakeHTTPResponse(client.METHOD_NOT_ALLOWED, FAKE_REASON,
                                      FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_crd = FakeCRD.generate_crd()
        mock_create = MagicMock(side_effect=fake_api_exception)
        with patch(CREATED_CUSTOM_RESOURSE,
                   mock_create):
            fake_crd.save()
        assert mock_create.called
        exp_log_err = "API is blocked. Report will be skipped"
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == exp_log_err


def test_third_party_resource_save_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, FAKE_REASON, FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_crd = FakeCRD.generate_crd()
        mock_create = MagicMock(side_effect=fake_api_exception)
        with patch(CREATED_CUSTOM_RESOURSE,
                   mock_create):
            with pytest.raises(K8sApiException):
                fake_crd.save()
        assert mock_create.called


def test_third_party_resource_save_recreate_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, FAKE_REASON, FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    fake_http_409_resp = FakeHTTPResponse(client.CONFLICT, FAKE_REASON,
                                          FAKE_BODY)
    fake_api_409_exception = K8sApiException(http_resp=fake_http_409_resp)
    mock = MagicMock()
    with patch(CLIENT_CONFIG,
               MagicMock(return_value=mock)):
        fake_crd = FakeCRD.generate_crd()
        mock_create = MagicMock(side_effect=fake_api_409_exception)
        mock_remove = MagicMock(side_effect=fake_api_exception)
        with patch(CREATED_CUSTOM_RESOURSE,
                   mock_create), \
            patch('intel.custom_resource.CustomResourceDefinition.remove',
                  mock_remove):
            with pytest.raises(K8sApiException):
                fake_crd.save()
        exp_log_err = "Previous definition has been detected. Recreating..."
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == exp_log_err
        assert mock_create.called
        assert mock_remove.called
