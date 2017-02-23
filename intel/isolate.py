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

from . import config, proc
import logging
import os
import random
import psutil
import signal
import subprocess

ENV_CPUS_ASSIGNED = "KCM_CPUS_ASSIGNED"


def isolate(conf_dir, pool_name, no_affinity, command, args):
    c = config.Config(conf_dir)
    with c.lock():
        pools = c.pools()
        if pool_name not in pools:
            raise KeyError("Requested pool {} does not exist"
                           .format(pool_name))
        pool = pools[pool_name]

        clist = None
        if pool.exclusive():
            for cl in pool.cpu_lists().values():
                if len(cl.tasks()) == 0:
                    clist = cl
                    break
        else:
            # NOTE(CD): This allocation algorithm is probably an
            # oversimplification, however for known use cases the non-exclusive
            # pools should never have more than one cpu list anyhow.
            # If that ceases to hold in the future, we could explore population
            # or load-based spreading. Keeping it simple for now.
            clist = random.choice(list(pool.cpu_lists().values()))

        if not clist:
            raise SystemError("No free cpu lists in pool {}".format(pool_name))

        clist.add_task(proc.getpid())

    # NOTE: we spawn the child process after exiting the config lock context.
    try:
        # Advertise assigned CPU IDs in the environment.
        os.environ[ENV_CPUS_ASSIGNED] = clist.cpus()

        # We use psutil here (instead of the kcm provided
        # process abstraction) as we need to change the affinity of the current
        # process. This, in turn, is done through a system call which does
        # not allow us to reference host PIDs. In this case, it is OK to
        # operate within the PID namespace as we are changing our own affinity
        # and count on the child processes inheriting the affinity settings.
        p = psutil.Process()

        if no_affinity:
            logging.info("""Not setting CPU affinity before forking the child\
command because the --no-affinity flag was supplied""")

        else:
            cpu_list = proc.unfold_cpu_list(clist.cpus())
            logging.debug("Setting CPU affinity to %s", cpu_list)
            p.cpu_affinity(cpu_list)

        child = subprocess.Popen("{} {}".format(command,
                                 " ".join(args)),
                                 shell=True)

        # Register a signal handler for TERM so that we can attempt to leave
        # things in a consistent state. As a good POSIX citizen, we propagate
        # the TERM signal to the child so that it also has a chance to clean
        # up if it needs to. For reference on POSIX systems:
        # - `subprocess.Popen.terminate()` sends TERM
        # - `subprocess.Popen.kill()` sends KILL
        signal.signal(signal.SIGTERM, child.terminate)

        # Block waiting for the child process to exit.
        child.wait()

    finally:
        with c.lock():
            clist.remove_task(proc.getpid())
