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

from intel import util
import copy
import os
import random
import string
import subprocess
from threading import Thread


# Returns the absolute path to the test config directory with the supplied
# name.
def conf_dir(name):
    return os.path.join(util.kcm_root(), "tests", "data", "config", name)


# Returns the absolute path to the test procfs directory with the supplied
# name.
def procfs_dir(name):
    return os.path.join(
        util.kcm_root(), "tests", "data", "sysfs", name, "proc")


def sysfs_dir(name):
    return os.path.join(util.kcm_root(), "tests", "data", "sysfs", name)


def rand_str(length=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for c in range(length))


# Returns resulting stdout buffer from interpreting the supplied command with
# a shell. Raises process errors if the command exits nonzero.
def execute(cmd, args=[], env={}):
    cmd_str = "{} {}".format(cmd, " ".join(args))

    host_env = copy.deepcopy(os.environ)
    host_env.update(env)

    stdout = subprocess.check_output(
        cmd_str, shell=True, stderr=subprocess.STDOUT, env=host_env)
    return stdout


def background(f):
    return BackgroundContext(f)


class BackgroundContext:
    def __init__(self, f):
        self.t = Thread(target=f)

    def __enter__(self):
        self.t.start()
        return self.t

    def __exit__(self, type, value, traceback):
        pass
