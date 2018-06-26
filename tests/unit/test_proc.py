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

from intel import proc, util
import pytest
import os


def test_procfs_must_be_set(monkeypatch):
    # Without the environment set for the proc file system, the call should
    # fail.
    with pytest.raises(SystemExit):
        proc.procfs()

    # Setting the variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, "/proc")

    # And calling again, and should not fail.
    proc.procfs()


def test_getpid_success(monkeypatch):
    fake_procfs = os.path.join(util.cmk_root(), "tests", "data", "procfs")
    monkeypatch.setenv(proc.ENV_PROC_FS, fake_procfs)
    assert(1234 == proc.getpid())


def test_process_cpus_allowed_success(monkeypatch):
    fake_procfs = os.path.join(util.cmk_root(), "tests", "data", "procfs",
                               "ok")
    monkeypatch.setenv(proc.ENV_PROC_FS, fake_procfs)
    fake_pid = 1234
    fake_process = proc.Process(fake_pid)
    assert(fake_process.cpus_allowed() == [0, 1, 2, 3])


def test_process_cpus_allowed_failure(monkeypatch):
    fake_procfs = os.path.join(util.cmk_root(), "tests", "data", "procfs",
                               "no_cpus_allowed_list")
    monkeypatch.setenv(proc.ENV_PROC_FS, fake_procfs)
    fake_pid = 1234
    fake_process = proc.Process(fake_pid)
    with pytest.raises(ValueError):
        fake_process.cpus_allowed()


def test_unfold_empty_cpu_list():
    assert(proc.unfold_cpu_list("") == [])


def test_unfold_valid_cpu_lists():
    assert(proc.unfold_cpu_list("0") == [0])
    assert(proc.unfold_cpu_list("0-1") == [0, 1])
    assert(proc.unfold_cpu_list("0-1,4") == [0, 1, 4])
    assert(proc.unfold_cpu_list("0-1,4-6") == [0, 1, 4, 5, 6])
    assert(proc.unfold_cpu_list("0-1,4-6,9") == [0, 1, 4, 5, 6, 9])
    assert(proc.unfold_cpu_list("0-1,4-6,9-10") == [0, 1, 4, 5, 6, 9, 10])
    assert(proc.unfold_cpu_list("0,1,4,5,6,9,10") == [0, 1, 4, 5, 6, 9, 10])


def test_unfold_invalid_cpu_lists():
    with pytest.raises(ValueError):
        proc.unfold_cpu_list(",")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("-")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("0,")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("0,-")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("0,1-")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("0,1-2,")
