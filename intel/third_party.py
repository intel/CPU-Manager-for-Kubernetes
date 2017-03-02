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

import json
from kubernetes.client.rest import ApiException as K8sApiException
import datetime
import logging
import re
import time

# Example usage:
#
# from kubernetes import config as k8sconfig, client as k8sclient
#
# k8sconfig.load_kube_config()
#
# v1beta = k8sclient.ExtensionsV1beta1Api()
#
# apple_type = ThirdPartyResourceType(v1beta, "intel.com", "apple")
#
# apple1 = apple_type.create("apple1")
# apple1.body["count"] = 5
# apple1.save()
#
# apple2 = apple_type.create("apple2")
# apple2.body["count"] = 10
# apple2.save()


class ThirdPartyResourceType():
    def __init__(self, api, url, kind_name, version="v1"):
        assert(api is not None)
        assert(url is not None)
        assert(kind_name is not None)
        assert(version is not None)

        self.api = api
        self.type_url = url
        self.type_name = kind_name.lower()
        self.kind_name = kind_name
        self.type_version = version

    def save(self):
        body = {
            "metadata": {"name": ".".join([self.type_name, self.type_url])},
            "versions": [{"name": self.type_version}]
        }

        try:
            self.api.create_third_party_resource(body)
        except K8sApiException as e:
            if json.loads(e.body)["reason"] != "AlreadyExists":
                raise e

        # Wait until resource type is ready.
        while not self.exists():
            logging.info(
                "waiting 1 second until third party resource is ready")
            time.sleep(1)

    def exists(self, namespace="default"):
        header_params = {
            'Content-Type': "application/json",
            'Accept': "application/json"
        }

        auth_settings = ['BearerToken']

        resource_path = "/".join([
            "/apis",
            self.type_url,
            self.type_version,
            "namespaces", namespace,
            self.type_name + "s"
        ])

        try:
            self.api.api_client.call_api(
                resource_path,
                'GET',
                header_params,
                auth_settings=auth_settings)

        except K8sApiException as e:
            if json.loads(e.body)["reason"] == "NotFound":
                return False
            raise e

        return True

    def create(self, name, namespace="default"):
        self.save()
        return ThirdPartyResource(self.api, self, namespace, name)


class ThirdPartyResource:
    def __init__(self, api, resource_type, namespace, name):
        assert(api is not None)
        assert(resource_type is not None)
        assert(name is not None)
        assert(namespace is not None)

        self.api = api
        self.resource_type = resource_type
        self.name = ldh_convert_check(name)
        self.namespace = namespace

        self.body = {
            "apiVersion": "/".join([
                self.resource_type.type_url,
                self.resource_type.type_version
            ]),
            "kind": self.resource_type.kind_name,
            "metadata": {"name": self.name}
        }

        self.header_params = {
            'Content-Type': "application/json",
            'Accept': "application/json"
        }

        self.auth_settings = ['BearerToken']

    def remove(self):
        resource_path = "/".join([
            "/apis",
            self.resource_type.type_url,
            self.resource_type.type_version,
            "namespaces", self.namespace,
            self.resource_type.type_name + "s",
            self.name
        ])

        self.api.api_client.call_api(
            resource_path,
            'DELETE',
            self.header_params,
            auth_settings=self.auth_settings)

    def create(self):
        resource_path = "/".join([
            "/apis",
            self.resource_type.type_url,
            self.resource_type.type_version,
            "namespaces", self.namespace,
            self.resource_type.type_name + "s"
        ])

        self.body["last_updated"] = datetime.datetime.now().isoformat()

        self.api.api_client.call_api(
            resource_path,
            'POST',
            self.header_params,
            body=self.body,
            auth_settings=self.auth_settings)

    def save(self):
        try:
            self.create()

        except K8sApiException as e:
            if json.loads(e.body)["reason"] != "AlreadyExists":
                raise e

            self.remove()
            self.create()


def ldh_convert_check(name):
    name_con = re.sub(r'[^-a-z0-9]', '-', name.lower())
    logging.info("Converted \"{}\" to \"{}\" for"
                 " TPR name".format(name, name_con))
    if not re.fullmatch('[a-z0-9]([-a-z0-9]*[a-z0-9])?', name_con):
        logging.error("Cant create valid TPR name using "
                      "\"{}\" - must match regex "
                      "[a-z0-9]([-a-z0-9]*[a-z0-9])?".format(name_con))
        exit(1)
    return name_con
