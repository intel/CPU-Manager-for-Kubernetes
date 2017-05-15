#!/bin/bash
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

curl --header "Content-Type:application/json-patch+json" \
        --request PATCH \
        --data '[{"op": "remove", "path": "/status/capacity/pod.alpha.kubernetes.io~1opaque-int-resource-kcm"}]' \
        http://localhost:8080/api/v1/nodes/$1/status
