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

from . import config, topology
import logging
import sys


def init(conf_dir, num_dp_cores, num_cp_cores):
    check_hugepages()

    logging.info("Writing config to {}.".format(conf_dir))
    logging.info("Requested data plane cores = {}.".format(num_dp_cores))
    logging.info("Requested control plane cores = {}.".format(num_cp_cores))

    try:
        c = config.new(conf_dir)
    except FileExistsError:
        logging.info("Configuration directory already exists.")
        check_assignment(conf_dir, num_dp_cores, num_cp_cores)
        return

    sockets = topology.discover()

    # List of intel.topology.Core objects.
    cores = []
    for _, socket in sockets.items():
        cores = list(socket.cores.values())

    check_isolated_cores(cores, num_dp_cores, num_cp_cores)

    # Align dp+cp cores to isolated cores if possible
    isolated_cores = [c for c in cores if c.is_isolated()]
    shared_cores = [c for c in cores if not c.is_isolated()]

    if isolated_cores:
        logging.info("Isolated physical cores: {}".format(
            ",".join([str(c.core_id) for c in isolated_cores])))
        assign(isolated_cores, "dataplane", count=num_dp_cores)
        assign(isolated_cores, "controlplane", count=num_cp_cores)
        assign(shared_cores, "infra")
    else:
        logging.info("No isolated physical cores detected: allocating "
                     "control plane and data plane from full core list")
        assign(cores, "dataplane", count=num_dp_cores)
        assign(cores, "controlplane", count=num_cp_cores)
        assign(cores, "infra")

    with c.lock():
        write_exclusive_pool("dataplane", cores, c)
        write_shared_pool("controlplane", cores, c)
        write_shared_pool("infra", cores, c)


def check_hugepages():
    meminfo_path = "/proc/meminfo"
    try:
        with open(meminfo_path, "r") as fd:
            content = fd.read()
            lines = content.split("\n")
            for line in lines:
                if line.startswith("HugePages_Free"):
                    parts = line.split()
                    num_free = int(parts[1])
                    if num_free == 0:
                        logging.warning("No hugepages are free")
                        return

    except FileNotFoundError:
        logging.info("meminfo file '%s' not found: skipping huge pages check" %
                     meminfo_path)


def check_assignment(conf_dir, num_dp_cores, num_cp_cores):
    c = config.Config(conf_dir)

    num_dp_lists = len(c.pool("dataplane").cpu_lists())
    num_cp_lists = len(c.pool("controlplane").cpu_lists())

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


def check_isolated_cores(cores, num_dp_cores, num_cp_cores):
    isolated_cores = [c for c in cores if c.is_isolated()]
    num_isolated_cores = len(isolated_cores)

    for core in cores:
        for cpu in core.cpus.values():
            if cpu.isolated and not core.is_isolated():
                logging.warning(
                    "Physical core {} is partially isolated: {}".format(
                        core.core_id, core.as_dict()))
                break

    if num_isolated_cores > 0:
        required_isolated_cores = (num_dp_cores + num_cp_cores)

        if num_isolated_cores < required_isolated_cores:
            logging.error(
                "Cannot use isolated cores for data plane and control plane "
                "cores: not enough isolated cores %d compared to requested %d"
                % (num_isolated_cores, required_isolated_cores))
            sys.exit(1)

        if num_isolated_cores != required_isolated_cores:
            logging.warning(
                "Not all isolated cores will be used by data and "
                "control plane. %d isolated but only %d used" %
                (num_isolated_cores, required_isolated_cores))


def assign(cores, pool, count=None):
    free_cores = [c for c in cores if c.pool is None]

    if not free_cores:
        raise RuntimeError(
            "No more free cores left to assign for {}".format(pool))

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
        logging.info("Adding cpu list %s to %s pool." %
                     (cpu_ids_str, pool_name))


def write_shared_pool(pool_name, cores, config):
    logging.info("Adding %s pool." % pool_name)
    pool = config.add_pool(pool_name, False)

    cores = [c for c in cores if c.pool == pool_name]

    cpu_ids = []
    for core in cores:
        cpu_ids.extend(core.cpu_ids())

    cpu_ids_str = ",".join([str(c) for c in cpu_ids])
    pool.add_cpu_list(cpu_ids_str)
    logging.info("Adding cpu list %s to %s pool." %
                 (cpu_ids_str, pool_name))
