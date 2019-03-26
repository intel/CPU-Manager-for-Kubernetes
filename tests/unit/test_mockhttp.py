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

from .. import helpers, mockhttp
import requests


def test_mockhttp_server():
    def http_client():
        assert 200 == requests.get(server.url).status_code

    with mockhttp.Server() as server:
        with server.next_request() as f:
            with helpers.background(http_client) as thread:
                # Wait up to 5 seconds for a result
                (method, handler) = f.result(5)
                assert method == "GET"
                handler.send_response(200, "OK")
                handler.end_headers()
        thread.join()
