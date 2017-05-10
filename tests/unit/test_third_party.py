# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from intel import third_party
import pytest


def test_ldh_parser_success():

    original_node_names = [
        "node-123",
        "node-123.45",
        "Node.Master-89",
        "123-master-NODE",
        "192.167-100-2.NODE",
        "MINION.1@10.12.56.78",
        "MINION.1@.#10.12.56.78",
        "Compute---1@10.12.56.78"
    ]

    expected_node_names = [
        "node-123",
        "node-123-45",
        "node-master-89",
        "123-master-node",
        "192-167-100-2-node",
        "minion-1-10-12-56-78",
        "minion-1---10-12-56-78",
        "compute---1-10-12-56-78"
    ]

    retrieved_node_names = []

    for name in original_node_names:
        retrieved_node_names.append(third_party.ldh_convert_check(name))

    assert expected_node_names == retrieved_node_names


def test_ldh_parser_fail():

    original_invalid_node_names = [
        "node-123-",
        "node-123.45@",
        "$Node.Master-89",
        ".123-master-NODE",
        "@192.167-100-2-NODE",
    ]

    for name in original_invalid_node_names:
        with pytest.raises(SystemExit):
            third_party.ldh_convert_check(name)
