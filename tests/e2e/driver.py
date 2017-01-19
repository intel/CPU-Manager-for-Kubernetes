from kubernetes import config as k8sconfig, client as k8sclient
import tempfile


class Driver:
    def __init__(self, api_server):
        self.api_server = api_server

        config_file_path = None

        with tempfile.NamedTemporaryFile(delete=False) as config_file:
            config_file.write(bytes("foobar")
            config_file.flush()
            config_file_path = config_file

        if config_file_path is None:
            raise IOError("Kubernetes config file not created")

        k8sconfig.load_kube_config(config_file=config_file_path)

        self.v1_api = k8sclient.CoreV1Api()
