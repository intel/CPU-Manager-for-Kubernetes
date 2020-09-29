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

from . import config, k8s
import json
import os


def describe():
    pod_name = os.environ["HOSTNAME"]
    node_name = k8s.get_node_from_pod(None, pod_name)
    configmap_name = "cmk-config-{}".format(node_name)
    c = config.Config(configmap_name, pod_name)
    c.lock()
    print(json.dumps(c.c_data.as_dict(), sort_keys=True, indent=2))
    c.unlock()
