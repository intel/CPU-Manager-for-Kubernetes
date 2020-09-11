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

from intel import third_party, k8s
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException as K8sApiException
import pytest
from http import client

K8S_EXTENSIONS_CLIENT = 'intel.k8s.extensions_client_from_config'
FAKE_REASON = "fake reason"
FAKE_BODY = "fake body"
THIRD_PARTY_RESOURCE_CREATE = 'intel.third_party.ThirdPartyResource.create'


class FakeHTTPResponse:
    def __init__(self, status=None, reason=None, data=None):
        self.status = status
        self.reason = reason
        self.data = data

    def getheaders(self):
        return {"fakekey": "fakeval"}


class FakeTPR:
    @staticmethod
    def generate_tpr_type():
        v1beta = k8s.extensions_client_from_config()
        return third_party.ThirdPartyResourceType(v1beta, "fake_url",
                                                  "fake_name", "v1")

    @staticmethod
    def generate_tpr():
        v1beta = k8s.extensions_client_from_config()
        fake_type = FakeTPR.generate_tpr_type()
        return third_party.ThirdPartyResource(v1beta, fake_type, "default",
                                              "fake-tpr")


def test_third_party_resource_type_save_success():
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_type = FakeTPR.generate_tpr_type()
        with patch('intel.third_party.ThirdPartyResourceType.exists',
                   MagicMock(side_effect=[False, True])):
            fake_type.save()
        assert mock.method_calls[0][0] == 'create_third_party_resource'


def test_third_party_resource_type_save_failure():
    fake_http_resp = FakeHTTPResponse(500, FAKE_REASON, FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        mock.create_third_party_resource = \
                MagicMock(side_effect=fake_api_exception)
        fake_type = FakeTPR.generate_tpr_type()
        with pytest.raises(K8sApiException):
            fake_type.save()


def test_third_party_resource_type_exists_success():
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_type = FakeTPR.generate_tpr_type()
        mock.api_client.call_api = MagicMock()
        exists = fake_type.exists()
        assert exists


def test_third_party_resource_type_exists_success2():
    fake_http_resp = FakeHTTPResponse(client.NOT_FOUND, FAKE_REASON,
                                      FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    assert fake_api_exception.status == client.NOT_FOUND
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_type = FakeTPR.generate_tpr_type()
        mock.api_client.call_api = MagicMock(side_effect=fake_api_exception)
        exists = fake_type.exists()
        assert not exists


def test_third_party_resource_type_exists_failure():
    fake_http_resp = FakeHTTPResponse(500, FAKE_REASON, FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_type = FakeTPR.generate_tpr_type()
        mock.api_client.call_api = MagicMock(side_effect=fake_api_exception)
        with pytest.raises(K8sApiException):
            fake_type.exists()


def test_third_party_resource_type_create_success():
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_type = FakeTPR.generate_tpr_type()
        v1beta = k8s.extensions_client_from_config()
        expected_tpr = third_party.ThirdPartyResource(v1beta, fake_type,
                                                      "default", "fake-tpr")
        with patch('intel.third_party.ThirdPartyResourceType.exists',
                   MagicMock(side_effect=[False, True])):
            result = fake_type.create("fake-tpr", namespace="default")
            assert vars(result) == vars(expected_tpr)


def test_third_party_resource_create_success():
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_tpr = FakeTPR.generate_tpr()
        fake_tpr.create()
        assert mock.method_calls[0][0] == 'api_client.call_api'
        assert 'POST' in mock.method_calls[0][1]


def test_third_party_resource_remove_success():
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_tpr = FakeTPR.generate_tpr()
        fake_tpr.remove()
        assert mock.method_calls[0][0] == 'api_client.call_api'
        assert 'DELETE' in mock.method_calls[0][1]


def test_third_party_resource_save_success():
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_tpr = FakeTPR.generate_tpr()
        mock_create = MagicMock()
        with patch(THIRD_PARTY_RESOURCE_CREATE, mock_create):
            fake_tpr.save()
        assert mock_create.called


def test_third_party_resource_save_tpr_not_ready_failure(caplog):
    fake_http_resp = FakeHTTPResponse(client.NOT_FOUND, FAKE_REASON,
                                      FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_tpr = FakeTPR.generate_tpr()
        mock_create = MagicMock(side_effect=fake_api_exception)
        with patch(THIRD_PARTY_RESOURCE_CREATE, mock_create):
            fake_tpr.save()
        assert mock_create.called
        exp_log_err = ("Third Party Resource is not ready yet. "
                       "Report will be skipped")
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == exp_log_err


def test_third_party_resource_save_api_blocked_failure(caplog):
    fake_http_resp = FakeHTTPResponse(client.METHOD_NOT_ALLOWED, FAKE_REASON,
                                      FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_tpr = FakeTPR.generate_tpr()
        mock_create = MagicMock(side_effect=fake_api_exception)
        with patch(THIRD_PARTY_RESOURCE_CREATE, mock_create):
            fake_tpr.save()
        assert mock_create.called
        exp_log_err = "API is blocked. Report will be skipped"
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == exp_log_err


def test_third_party_resource_save_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, FAKE_REASON, FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_tpr = FakeTPR.generate_tpr()
        mock_create = MagicMock(side_effect=fake_api_exception)
        with patch(THIRD_PARTY_RESOURCE_CREATE, mock_create):
            with pytest.raises(K8sApiException):
                fake_tpr.save()
        assert mock_create.called


def test_third_party_resource_save_recreate_failure(caplog):
    fake_http_resp = FakeHTTPResponse(500, FAKE_REASON, FAKE_BODY)
    fake_api_exception = K8sApiException(http_resp=fake_http_resp)
    fake_http_conflict_resp = FakeHTTPResponse(client.CONFLICT, FAKE_REASON,
                                               FAKE_BODY)
    fake_api_conflict_exception = K8sApiException(
                                            http_resp=fake_http_conflict_resp)
    mock = MagicMock()
    with patch(K8S_EXTENSIONS_CLIENT,
               MagicMock(return_value=mock)):
        fake_tpr = FakeTPR.generate_tpr()
        mock_create = MagicMock(side_effect=fake_api_conflict_exception)
        mock_remove = MagicMock(side_effect=fake_api_exception)
        with patch(THIRD_PARTY_RESOURCE_CREATE,
                   mock_create), \
            patch('intel.third_party.ThirdPartyResource.remove',
                  mock_remove):
            with pytest.raises(K8sApiException):
                fake_tpr.save()
        exp_log_err = "Previous resource has been detected. Recreating..."
        caplog_tuple = caplog.record_tuples
        assert caplog_tuple[-1][2] == exp_log_err
        assert mock_create.called
        assert mock_remove.called
