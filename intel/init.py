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

from . import config, topology, proc
import logging
import sys
import os


def verify_allocation(conf_dir, num_dp_cores, num_cp_cores):
    c = config.Config(conf_dir)

    num_dp_lists = len(c.pools("dataplane").cpu_lists())
    num_cp_lists = len(c.pools("controlplane").cpu_lists())

    alloc_error = None

    if num_dp_lists is not num_dp_cores:
        alloc_error = True
        logging.error("{} dataplane cores ({} requested)".format(
            num_dp_lists, num_dp_cores))
    if num_cp_lists is not num_cp_cores:
        alloc_error = True
        logging.error("{} controlplane cores ({} requested)".format(
            num_cp_lists, num_cp_cores))

    if alloc_error:
        sys.exit(1)


def verify_isolated_cores(cores, num_dp_cores, num_cp_cores):
    isolated_cores = [c for c in cores if c.is_isolated()]
    num_isolated_cores = len(isolated_cores)

    if num_isolated_cores > 0:
        required_isolated_cores = (num_dp_cores + num_cp_cores)

        if num_isolated_cores < required_isolated_cores:
            logging.error(
                "Cannot use isolated cores for data plane and control plane "
                "cores: not enough isolated cores %d compared to requested %d"
                % num_isolated_cores, required_isolated_cores)
            sys.exit(1)

        if num_isolated_cores != required_isolated_cores:
            logging.warning(
                "Not all isolated cores will be used by data and "
                "control plane. %d isolated but only %d used" %
                (num_isolated_cores, required_isolated_cores))


def assign(cores, pool, count=None):
    free_cores = [c for c in cores if c.pool is None]

    if not free_cores:
        raise RuntimeError("No more free cores left for assignment of %s" %
                           pool)

    if count and len(free_cores) < count:
        raise RuntimeError("%d cores requested for %s. "
                           "Only %d cores available" %
                           (count, pool, len(free_cores)))

    assigned = free_cores
    if count:
        assigned = free_cores[:count]

    for c in assigned:
        c.pool = pool


def write_exclusive_pool(pool_name, cores, config):
    logging.info("Adding %s pool." % pool_name)
    pool = config.add_pool(pool_name, True)

    cores = [c for c in cores if c.pool == pool_name]

    # We write one cpu list per core for exclusive pools/
    for core in cores:
        cpu_ids_str = ",".join([str(c) for c in core.cpu_ids()])
        pool.add_cpu_list(cpu_ids_str)


def write_shared_pool(pool_name, cores, config):
    logging.info("Adding %s pool." % pool_name)
    pool = config.add_pool(pool_name, False)

    cores = [c for c in cores if c.pool == pool_name]

    cpu_ids = []
    for core in cores:
        cpu_ids.extend(core.cpu_ids())

    cpu_ids_str = ",".join([str(c) for c in cpu_ids])
    pool.add_cpu_list(cpu_ids_str)


def init(conf_dir, num_dp_cores, num_cp_cores):
    check_hugepages()

    logging.info("Writing config to {}.".format(conf_dir))
    logging.info("Requested data plane cores = {}.".format(num_dp_cores))
    logging.info("Requested control plane cores = {}.".format(num_cp_cores))

    try:
        c = config.new(conf_dir)
    except FileExistsError:
        logging.info("Configuration directory already exists.")
        verify_allocation(conf_dir, num_dp_cores, num_cp_cores)
        return

    sockets = topology.parse(
        topology.lscpu(),
        topology.isolcpus(os.path.join(proc.procfs(), "cmdline")))

    if len(sockets) != 1:
        logging.error("Only single socket systems are supported for now. "
                      "Found %d sockets" % len(sockets))
        sys.exit(1)

    cores = list(sockets[0].cores.values())

    verify_isolated_cores(cores, num_dp_cores, num_cp_cores)

    # Align dp+cp cores to isolated cores if possible
    isolated_cores = [c for c in cores if c.is_isolated()]
    non_isolated_cores = [c for c in cores if not c.is_isolated()]

    num_isolated_cores = len(isolated_cores)

    if num_isolated_cores == 0:
        dp_pool = cores
        cp_pool = cores
        infra_pool = cores
    elif num_isolated_cores > 0:
        dp_pool = isolated_cores
        cp_pool = isolated_cores
        infra_pool = non_isolated_cores

    assign(dp_pool, "dataplane", count=num_dp_cores)
    assign(cp_pool, "controlplane", count=num_cp_cores)
    assign(infra_pool, "infra")

    with c.lock():
        write_exclusive_pool("dataplane", cores, c)
        write_shared_pool("controlplane", cores, c)
        write_shared_pool("infra", cores, c)


def check_hugepages():
    fd = open("/proc/meminfo", "r")
    content = fd.read()
    lines = content.split("\n")
    for line in lines:
        if line.startswith("HugePages_Free"):
            parts = line.split()
            num_free = int(parts[1])
            if num_free == 0:
                logging.warning("No hugepages are free")
                return
