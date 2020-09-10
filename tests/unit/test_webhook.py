from unittest.mock import patch, MagicMock
import pytest
import os
from yamlreader import YamlReaderError

from intel import webhook, util

MUTATIONS_YAML =  "mutations.yaml"

def get_cmk_container():
    fake_cmk_container = {
        "resources": {
            "requests": {
                webhook.CMK_ER_NAME[0]: "2"
            },
            "limits": {
                webhook.CMK_ER_NAME[0]: "2"
            },
        }
    }
    return fake_cmk_container


def get_cmk_container2():
    fake_cmk_container = {
        "resources": {
            "requests": {
                webhook.CMK_ER_NAME[1]: "2"
            },
            "limits": {
                webhook.CMK_ER_NAME[1]: "2"
            },
        }
    }
    return fake_cmk_container


def get_admission_review():
    admission_review = {
        "request": {
            "kind": {
                "kind": "Pod"
            },
            "uid": "fake_uid",
            "object": {
                "metadata": {},
                "spec": {
                    "containers": [get_cmk_container()]
                }
            }
        }
    }
    return admission_review


def test_webhook_inject_env_add_success():
    container = get_cmk_container()
    key = "fake"
    value = "fake"
    webhook.inject_env(container, key, value)
    assert key == container["env"][-1]["name"]
    assert value == container["env"][-1]["value"]


def test_webhook_inject_env_exists(caplog):
    container = get_cmk_container()
    key = "fake"
    value = "fake"
    webhook.inject_env(container, key, value)
    assert key == container["env"][-1]["name"]
    assert value == container["env"][-1]["value"]

    # try to add again
    webhook.inject_env(container, key, value)
    log = "Environmental variable {} exists. Skipping...".format(key)
    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == log


def test_webhook_generate_patch():
    pod = MagicMock()
    patch = webhook.generate_patch(pod)
    assert patch[0]['op'] == "replace"
    assert patch[0]['path'] == "/metadata"
    assert patch[0]['value'] == pod["metadata"]
    assert patch[1]['op'] == "replace"
    assert patch[1]['path'] == "/spec"
    assert patch[1]['value'] == pod["spec"]


def test_webhook_config_init():
    config = webhook.WebhookServerConfig()
    assert config.server == {}


def test_webhook_container_mutation_required():
    container = get_cmk_container()
    required = webhook.is_container_mutation_required(container)
    assert required

    container["resources"].pop("requests")  # limits still there
    still_required = webhook.is_container_mutation_required(container)
    assert still_required


def test_webhook_container_mutation_required2():
    container = get_cmk_container2()
    required = webhook.is_container_mutation_required(container)
    assert required

    container["resources"].pop("requests")
    still_required = webhook.is_container_mutation_required(container)
    assert still_required


def test_webhook_container_mutation_not_required():
    container = {}
    required = webhook.is_container_mutation_required(container)
    assert not required


def test_webhook_mutation_required():
    pod = {
        "spec": {
            "containers": [get_cmk_container()]
        }
    }
    required = webhook.is_mutation_required(pod)
    assert required


def test_wehbook_mutation_required2():
    pod = {
        "spec": {
            "containers": [get_cmk_container2()]
        }
    }

    required = webhook.is_mutation_required(pod)
    assert required


def test_webhook_mutation_not_required():
    pod = {
        "spec": {
            "containers": [{}]
        }
    }
    with patch('intel.webhook.is_container_mutation_required',
               MagicMock(return_value=False)):
        required = webhook.is_mutation_required(pod)
    assert not required


def test_webhook_load_mutations_success():
    conf_file = os.path.join(util.cmk_root(), "tests", "data",
                             "webhook",MUTATIONS_YAML)
    mutations = webhook.load_mutations(conf_file)
    assert type(mutations) is dict
    assert "perPod" in mutations
    assert "perContainer" in mutations


def test_webhook_load_mutations_fail(caplog):
    filename = "fake"
    with patch('yamlreader.yaml_load', side_effect=YamlReaderError):
        with pytest.raises(SystemExit):
            webhook.load_mutations(filename)
    log = "Error loading mutations from file {}.".format(filename)
    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == log


def test_webhook_mutate_not_a_pod_fail(caplog):
    ar_mock = MagicMock()
    ar_mock['request']['kind']['kind'] = "NotAPod"
    with pytest.raises(webhook.MutationError):
        webhook.mutate(ar_mock, None)
    log = "Resource is not a pod"
    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == log


@patch('intel.webhook.merge', MagicMock())
def test_webhook_mutate_success():
    conf_file = os.path.join(util.cmk_root(), "tests", "data",
                             "webhook",MUTATIONS_YAML)
    ar = get_admission_review()
    request_uid = ar["request"]["uid"]
    webhook.mutate(ar, conf_file)
    assert "response" in ar
    assert "request" not in ar
    assert ar["response"]["uid"] == request_uid
    assert ar["response"]["allowed"]
    assert type(ar["response"]["patch"]) is str


@patch('intel.webhook.merge', MagicMock())
def test_webhook_mutate_not_required(caplog):
    conf_file = os.path.join(util.cmk_root(), "tests", "data",
                             "webhook",MUTATIONS_YAML)
    ar = get_admission_review()
    request_uid = ar["request"]["uid"]
    with patch('intel.webhook.is_mutation_required',
               MagicMock(return_value=False)):
        webhook.mutate(ar, conf_file)

    assert "response" in ar
    assert "request" not in ar
    assert ar["response"]["uid"] == request_uid
    assert ar["response"]["allowed"]
    assert "patch" not in ar["response"]

    log = "Mutation is not required. Skipping..."
    caplog_tuple = caplog.record_tuples
    assert caplog_tuple[-1][2] == log


@patch('intel.webhook.is_mutation_required', MagicMock(return_value=True))
def test_webhook_mutate_pod_merge_fail(caplog):
    conf_file = os.path.join(util.cmk_root(), "tests", "data",
                             "webhook",MUTATIONS_YAML)
    ar = get_admission_review()
    with patch('intel.webhook.merge', MagicMock(side_effect=YamlReaderError)):
        with pytest.raises(webhook.MutationError):
            webhook.mutate(ar, conf_file)


@patch('intel.webhook.is_mutation_required', MagicMock(return_value=True))
def test_webhook_mutate_container_merge_fail(caplog):
    conf_file = os.path.join(util.cmk_root(), "tests", "data",
                             "webhook",MUTATIONS_YAML)
    ar = get_admission_review()
    with patch('intel.webhook.merge',
               MagicMock(side_effect=[None, YamlReaderError])):
        with pytest.raises(webhook.MutationError):
            webhook.mutate(ar, conf_file)
