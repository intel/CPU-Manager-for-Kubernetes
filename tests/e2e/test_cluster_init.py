from . import driver
import os


def test_cluster_init(caplog):
    kube_api_server = os.environ["KCM_E2E_APISERVER"]
    driver.Driver(kube_api_server)
