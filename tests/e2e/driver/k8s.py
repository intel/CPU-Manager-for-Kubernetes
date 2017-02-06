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
import logging
import time
import uuid

from kubernetes import client, config
from kubernetes.client import V1DeleteOptions

from intel import k8s


class Driver(object):
    active = False
    configuration = None
    ns_name = ""
    nodes = []
    num_nodes = None
    timeout = -1

    # Driver constructor is reserving nodes for test(s) and creates
    # namespace.
    def __init__(self,
                 num_nodes=1,
                 timeout=60,
                 config_file_location=None,
                 host='https://localhost:443',
                 api_cert_file='/etc/kubernetes/ssl/ca.pem',
                 user_cert_file='/etc/kubernetes/ssl/admin.pem',
                 user_key_file='/etc/kubernetes/ssl/admin-key.pem'):
        """
        Driver constructor is reserving nodes for test(s) and creates namespace. # noqa: E501
        :param num_nodes: Requested number of nodes from cluster(int; default=1) # noqa: E501
        :param timeout: Timeout on waiting for resource arability in seconds(int; default=60) # noqa: E501
        :param config_file_location: Path to kubernetes client configuration(string, default=None) # noqa: E501
        :param host: (if config_file_location is not set) URL to API-server(string, default="https://localhost:443") # noqa: E501
        :param api_cert_file: (if config_file_location is not set) Path to API server cert(string, default="/etc/kubernetes/ssl/ca.pem") # noqa: E501
        :param user_cert_file: (if config_file_location is not set) Path to user cert(string, default="/etc/kubernetes/ssl/admin.pem") # noqa: E501
        :param user_key_file: (if config_file_location is not set) Path to user key(string, default="/etc/kubernetes/ssl/admin-key.pem") # noqa: E501
        """

        self.num_nodes = num_nodes
        self.timeout = timeout

        if config_file_location is None:
            self.configuration = client.Configuration()
            self.configuration.host = host
            self.configuration.ssl_ca_cert = api_cert_file
            self.configuration.cert_file = user_cert_file
            self.configuration.key_file = user_key_file
        else:
            self.configuration = config.load_kube_config(
                config_file=config_file_location)

        # check if cluster is able to reserve requested number of nodes.
        cluster_size = len(k8s.get_compute_nodes(config=self.configuration))
        if cluster_size < self.num_nodes:
            raise Exception("Cluster doesn't have requested number of nodes."
                            "Requested {}. Available {}."
                            .format(self.num_nodes, cluster_size))

        # generate random namespace name.
        self.ns_name = "namespace-%s" % str(uuid.uuid4())[:5]

        # wait for nodes until timeout.
        timeout_destination = int(time.time()) + self.timeout
        while len(self._get_list_unassigned_nodes(
                self.configuration)) < self.num_nodes:
            if int(time.time()) >= timeout_destination:
                raise Exception("Timeout after {} ".format(self.timeout) +
                                "seconds on waiting for resources avability")

            logging.debug("Waiting for resources...")
            time.sleep(1)

        # add the label to the node.
        unassigned_nodes = self._get_list_unassigned_nodes(self.configuration)
        self.nodes = unassigned_nodes[:self.num_nodes]

        for node in self.nodes:
            k8s.set_node_label(self.configuration, node, "namespace",
                               self.ns_name)

        # create namespace
        k8s.create_namespace(self.configuration, self.ns_name)
        self.active = True

    # Get schedule-able nodes w/o label "namespace".
    def _get_list_unassigned_nodes(self, config):
        compute_nodes = k8s.get_compute_nodes(config,
                                              label_selector='!namespace')
        return list(
            map(lambda node: node["spec"]["external_id"], compute_nodes))

    # Create pod inside random generated namespace.
    def create_pod(self, name, containers):
        """
        :param name: pod name(string)
        :param containers: containers specification
        (list[kubernetes.client.models.V1Container])
        :return: API response
        """
        if self.active is not True:
            raise Exception("Namespace has been removed")
        pod = k8s.get_pod_template()
        pod["metadata"]["name"] = name
        pod["spec"]["nodeName"] = None
        pod["spec"]["nodeSelector"] = {"namespace": self.ns_name}
        pod["spec"]["containers"] = containers
        k8s.create_pod(self.configuration, pod, self.ns_name)

    # Delete pod from random generated namespace.
    def delete_pod(self, name, body=V1DeleteOptions()):
        if self.active is not True:
            raise Exception("Namespace has been removed")
        k8s.delete_pod(self.configuration, name, self.ns_name, body)

    # Cleanup removes nodes from namespace and delete used namespace.
    # All created pods in namespace should be removed during deleting parent
    # namespace.
    def cleanup(self):
        if self.active is False:
            return
        self.active = False
        # TODO: run kcm uninstallation here, when it's ready.
        # https://github.com/intelsdi-x/kubernetes-comms-mvp/pull/81
        for node in self.nodes:
            k8s.unset_node_label(self.configuration, node, "namespace")

        self.nodes = []
        k8s.delete_namespace(self.configuration, self.ns_name)

        timeout_destination = int(time.time()) + self.timeout
        while True:
            if int(time.time()) >= timeout_destination:
                raise Exception("Timeout after {} ".format(self.timeout) +
                                "seconds on waiting removing namespace.")

            namespaces = k8s.get_namespaces(self.configuration)["items"]
            namespaces_list = list(map(lambda ns: ns["metadata"]["name"],
                                       namespaces))

            if self.ns_name not in namespaces_list:
                break
            time.sleep(1)
