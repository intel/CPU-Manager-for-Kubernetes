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

from . import integration
from .. import helpers
import os
import tempfile


def test_cmk_install():
    # Install cmk to a temporary directory.
    install_dir = tempfile.mkdtemp()
    helpers.execute(integration.cmk(),
                    ["install",
                     "--install-dir={}".format(install_dir)])
    installed_cmk = os.path.join(install_dir, "cmk")

    # Check installed cmk executable output against the original script.
    assert (helpers.execute(installed_cmk, ["--help"]) ==
            helpers.execute(integration.cmk(), ["--help"]))
    assert (helpers.execute(installed_cmk, ["--version"]) ==
            helpers.execute(integration.cmk(), ["--version"]))

    helpers.execute("rm", [installed_cmk])
