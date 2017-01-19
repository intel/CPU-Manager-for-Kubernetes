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

from .. import helpers
from intel import config, reconcile, proc


def test_set_equals_empty():
    assert reconcile.set_equals([], [])
    assert not reconcile.set_equals([], ["foo"])
    assert not reconcile.set_equals(["foo"], [])


def test_set_equals_same():
    assert reconcile.set_equals(["foo"], ["foo"])
    assert reconcile.set_equals([1, 3, 5], [1, 3, 5])


def test_set_equals_subsets():
    assert reconcile.set_equals(["foo"], ["foo"])
    assert not reconcile.set_equals([1, 2, 3, 4, 5], [1, 3, 5])
    assert not reconcile.set_equals([1, 3, 5], [1, 2, 3, 4, 5])


def test_set_equals_disjoint():
    assert not reconcile.set_equals(["foo", "bar"], ["baz", "buzz"])
    assert not reconcile.set_equals([1, 3, 5], [2, 4, 6])


def test_is_cpuset_mismatch_empty_set(monkeypatch):
    p = proc.Process(1)

    monkeypatch.setattr(p, "cpus_allowed", lambda: [])

    assert(not reconcile.is_cpuset_mismatch(p, []))


def test_is_cpuset_mismatch_equal_sets(monkeypatch):
    p = proc.Process(1)

    # Set with one cpu.
    monkeypatch.setattr(p, "cpus_allowed", lambda: [1])

    assert(not reconcile.is_cpuset_mismatch(p, [1]))

    # Set with two cpus.
    monkeypatch.setattr(p, "cpus_allowed", lambda: [1, 2])

    assert(not reconcile.is_cpuset_mismatch(p, [1, 2]))


def test_is_cpuset_mismatch_subsets(monkeypatch):
    p = proc.Process(1)

    # Current allowed is a subset of desired allowed cpus.
    monkeypatch.setattr(p, "cpus_allowed", lambda: [2, 3, 4])

    assert(reconcile.is_cpuset_mismatch(p, [1, 2, 3, 4, 5]))

    # Desired allowed is a subset of current allowed cpus.
    monkeypatch.setattr(p, "cpus_allowed", lambda: [1, 2, 3, 4, 5])

    assert(reconcile.is_cpuset_mismatch(p, [2, 3, 4]))


def test_generate_report(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("cpuset_mismatch"))
    conf = config.Config(helpers.conf_dir("cpuset_mismatch"))
    report = reconcile.generate_report(conf)

    assert report.reclaimed_cpu_lists() == []

    expected_mismatches = [
        reconcile.Mismatch(1003, "pool2", "4,5", [4, 5, 6]),
        reconcile.Mismatch(1010, "pool3", "9,10", [7, 8]),
        reconcile.Mismatch(1040, "pool3", "9,10", [9, 10, 11, 20]),
        reconcile.Mismatch(1005, "pool3", "7,8", [7])]

    for e in expected_mismatches:
        assert e in report.mismatched_cpu_masks()
