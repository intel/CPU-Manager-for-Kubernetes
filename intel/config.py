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

from collections import OrderedDict
import fcntl
import logging
import os
import threading
import _thread


# KCM_LOCK_TIMEOUT is interpreted as seconds.
ENV_LOCK_TIMEOUT = "KCM_LOCK_TIMEOUT"
DEFAULT_LOCK_TIMEOUT = 30


def max_lock_seconds():
    return float(os.getenv(ENV_LOCK_TIMEOUT, DEFAULT_LOCK_TIMEOUT))


# Returns a new config at the supplied path.
def new(path):
    if os.path.isdir(path) and len(os.listdir(path)) > 0:
        raise FileExistsError(
            "Config directory {} already initialized".format(path))
    os.makedirs(os.path.join(path, "pools"))
    open(os.path.join(path, "lock"), "w+")
    return Config(path)


class Config:
    def __init__(self, path):
        self.path = os.path.normpath(path)

    def lock(self):
        fd = os.open(os.path.join(self.path, "lock"), os.O_RDWR)
        return Lock(fd)

    def pools(self):
        pools = OrderedDict()
        pool_dir = os.path.join(self.path, "pools")
        for f in sorted(os.listdir(pool_dir)):
            pd = os.path.join(pool_dir, f)
            if os.path.isdir(pd):
                p = Pool(pd)
                pools[p.name()] = p
        return pools

    def pool(self, name):
        return self.pools()[name]

    # Writes a new pool to disk and returns the corresponding pool object.
    def add_pool(self, name, exclusive):
        if name in self.pools():
            raise KeyError("Pool {} already exists".format(name))
        os.makedirs(os.path.join(self.path, "pools", name))
        ex_file = os.path.join(self.path, "pools", name, "exclusive")
        with open(ex_file, "w+") as excl:
            if exclusive:
                excl.write("1")
            else:
                excl.write("0")
            excl.flush()
            os.fsync(excl)
        return self.pool(name)

    def as_dict(self):
        result = {}
        result["path"] = self.path
        pools = {}
        for _, p in self.pools().items():
            pools[p.name()] = p.as_dict()
        result["pools"] = pools
        return result


class Pool:
    def __init__(self, path):
        self.path = os.path.normpath(path)

    def name(self):
        return os.path.basename(self.path)

    def exclusive(self):
        f = os.path.join(self.path, "exclusive")
        with open(os.path.join(self.path, "exclusive")) as f:
            c = f.read(1)
            if c == "1":
                return True
            return False

    def cpu_lists(self):
        result = OrderedDict()
        for f in sorted(os.listdir(self.path)):
            d = os.path.join(self.path, f)
            if os.path.isdir(d):
                clist = CPUList(d)
                result[clist.cpus()] = clist
        return result

    def cpu_list(self, name):
        return self.cpu_lists()[name]

    # Writes a new cpu list to disk and returns the corresponding
    # CPUList object.
    def add_cpu_list(self, cpus):
        if cpus in self.cpu_lists():
            raise KeyError("CPU list {} already exists".format(cpus))
        os.makedirs(os.path.join(self.path, cpus))
        open(os.path.join(self.path, cpus, "tasks"), "w+")
        return self.cpu_list(cpus)

    def as_dict(self):
        result = {}
        result["exclusive"] = self.exclusive()
        result["name"] = self.name()
        clists = {}
        for _, c in self.cpu_lists().items():
            clists[c.cpus()] = c.as_dict()
        result["cpuLists"] = clists
        return result


class CPUList:
    def __init__(self, path):
        self.path = os.path.normpath(path)

    def cpus(self):
        return os.path.basename(self.path)

    def tasks(self):
        with open(os.path.join(self.path, "tasks")) as f:
            return [int(pid.strip())
                    for pid in f.read().split(",")
                    if pid != ""]

    def __write_tasks(self, tasks):
        # Mode "w+" truncates the file prior to writing new content.
        with open(os.path.join(self.path, "tasks"), "w+") as f:
            f.write(",".join([str(t) for t in tasks]))
            f.flush()
            os.fsync(f)

    # Writes the supplied pid to disk for this cpu list.
    def add_task(self, pid):
        tasks = self.tasks()
        tasks.append(pid)
        self.__write_tasks(tasks)

    # Removes the supplied pid from disk for this cpu list.
    def remove_task(self, pid):
        self.__write_tasks([t for t in self.tasks() if t != pid])

    def as_dict(self):
        result = {}
        result["cpus"] = self.cpus()
        result["tasks"] = self.tasks()
        return result


class Lock:
    def __init__(self, fd):
        self.fd = fd
        self.timer = None

    # Context guard
    def __enter__(self):
        self.__acquire()
        return self

    # Context guard
    def __exit__(self, type, value, traceback):
        self.__release()

    def __acquire(self):
        max_lock = max_lock_seconds()

        def timed_out():
            logging.error("Lock timed out after {} seconds".format(max_lock))
            # NOTE(CD):
            #
            # Bail and rely on the operating system to close the open lock
            # file descriptor. They are closed on our behalf according to
            # the POSIX standard. See https://linux.die.net/man/2/exit
            #
            # We emulate Ctrl-C instead of raising SystemExit via sys.exit()
            # since exceptions are per-thread. SystemExit causes the
            # interpreter to exit if unhandled. This is the only
            # reliable way to trigger an exception in the main thread
            # to make this testable. Open to improvements.
            #
            # The interpreter exits with status 1.
            #
            # See https://goo.gl/RXsXEs
            _thread.interrupt_main()

        self.timer = threading.Timer(max_lock, timed_out)
        self.timer.start()
        # acquire file lock
        fcntl.flock(self.fd, fcntl.LOCK_EX)

    def __release(self):
        self.timer.cancel()
        self.timer = None
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
