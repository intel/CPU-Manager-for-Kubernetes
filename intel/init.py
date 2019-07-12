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

from . import config, topology, discover, sst_bf as sst
import logging
import sys


def init(conf_dir, num_exclusive_cores, num_shared_cores,
         exclusive_allocation_mode, shared_allocation_mode):
    check_hugepages()

    logging.info("Writing config to {}.".format(conf_dir))
    logging.info("Requested exclusive cores = {}.".format(num_exclusive_cores))
    logging.info("Requested shared cores = {}.".format(num_shared_cores))

    try:
        c = config.new(conf_dir)
    except FileExistsError:
        logging.info("Configuration directory already exists.")
        check_assignment(conf_dir, num_exclusive_cores, num_shared_cores)
        return

    sst_bf = False
    try:
        sst_bf = discover.get_node_label(sst.NFD_LABEL) in ["true", "True"]
    except Exception as err:
        logging.info("Could not read SST-BF label from the node metadata: {}"
                     .format(err))

    platform = topology.discover(sst_bf)

    # List of intel.topology.Core objects.
    cores = platform.get_cores()

    check_isolated_cores(platform, num_exclusive_cores, num_shared_cores)

    if sst_bf and platform.has_isolated_sst_bf_cores():
        sst_bf_cores = [str(c.core_id) for c
                        in platform.get_isolated_sst_bf_cores()]
        logging.info("Isolated SST-BF physical cores: {}".format(
                     ",".join(sst_bf_cores)))

        # Isolated SST_BF cores will always land in the exclusive pool.
        isolated_sst_bf_cores_exclusive = \
            platform.get_isolated_sst_bf_cores(mode=exclusive_allocation_mode)

        isolated_cores_shared = \
            platform.get_isolated_cores(mode=shared_allocation_mode)
        infra_cores = platform.get_shared_cores()

        assign(isolated_sst_bf_cores_exclusive, "exclusive",
               count=num_exclusive_cores)
        assign(isolated_cores_shared, "shared", count=num_shared_cores)
        assign(infra_cores, "infra")

    elif platform.has_isolated_cores():
        logging.info("Isolated physical cores: {}".format(
            ",".join([str(c.core_id) for c in platform.get_isolated_cores()])))

        '''
        Following core lists depends on selected policies. If operator sets
        same policies for exclusive and shared pools those lists will
        be the same.
        '''
        isolated_cores_exclusive = platform.get_isolated_cores(
            mode=exclusive_allocation_mode)
        isolated_cores_shared = platform.get_isolated_cores(
            mode=shared_allocation_mode)

        infra_cores = platform.get_shared_cores()

        assign(isolated_cores_exclusive, "exclusive",
               count=num_exclusive_cores)
        assign(isolated_cores_shared, "shared", count=num_shared_cores)
        assign(infra_cores, "infra")
    else:
        logging.info("No isolated physical cores detected: allocating "
                     "shared and exclusive cores from full core list")

        cores_exclusive = platform.get_cores(mode=exclusive_allocation_mode)
        cores_shared = platform.get_cores(mode=shared_allocation_mode)

        assign(cores_exclusive, "exclusive", count=num_exclusive_cores)
        assign(cores_shared, "shared", count=num_shared_cores)
        assign(cores, "infra")

    with c.lock():
        write_exclusive_pool("exclusive", platform, c)
        write_shared_pool("shared", platform, c)
        write_shared_pool("infra", platform, c)


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


def check_assignment(conf_dir, num_exclusive_cores, num_shared_cores):
    c = config.Config(conf_dir)

    num_exclusive_lists = len(c.pool("exclusive").cpu_lists())
    num_shared_lists = len(c.pool("shared").cpu_lists())

    alloc_error = None

    if num_exclusive_lists is not num_exclusive_cores:
        alloc_error = True
        logging.error("{} exclusive cores ({} requested)".format(
            num_exclusive_lists, num_exclusive_cores))
    if num_shared_lists is not num_shared_cores:
        alloc_error = True
        logging.error("{} shared cores ({} requested)".format(
            num_shared_lists, num_shared_cores))

    if alloc_error:
        sys.exit(1)


def check_isolated_cores(platform, num_exclusive_cores, num_shared_cores):
    isolated_cores = platform.get_isolated_cores()
    cores = platform.get_cores()
    num_isolated_cores = len(isolated_cores)

    for core in cores:
        for cpu in core.cpus.values():
            if cpu.isolated and not core.is_isolated():
                logging.warning(
                    "Physical core {} is partially isolated: {}".format(
                        core.core_id, core.as_dict()))
                break

    if num_isolated_cores > 0:
        required_isolated_cores = (num_exclusive_cores + num_shared_cores)

        if num_isolated_cores < required_isolated_cores:
            logging.error(
                "Cannot use isolated cores for exclusive and shared "
                "cores: not enough isolated cores %d compared to requested %d"
                % (num_isolated_cores, required_isolated_cores))
            sys.exit(1)

        if num_isolated_cores != required_isolated_cores:
            logging.warning(
                "Not all isolated cores will be used by exclusive and "
                "shared pools. %d isolated but only %d used" %
                (num_isolated_cores, required_isolated_cores))


def assign(cores, pool, count=None):
    free_cores = [c for c in cores if c.pool is None]

    # always prioritize free SST_BF cores, even if there may be none
    # move up SST_BF cores AND keep order (spread or packet) among
    # SST_BF cores and among non-SST_BF cores
    free_cores.sort(key=lambda c: -c.is_sst_bf(), reverse=False)

    if not free_cores:
        raise RuntimeError(
            "No more free cores left to assign for {}".format(pool))

    if count and len(free_cores) < count:
        raise RuntimeError("%d cores requested for %s. "
                           "Only %d cores available" %
                           (count, pool, len(free_cores)))

    assigned = free_cores
    if count is not None:
        assigned = free_cores[:count]

    for c in assigned:
        c.pool = pool


def write_exclusive_pool(pool_name, platform, config):
    logging.info("Adding %s pool." % pool_name)
    pool = config.add_pool(pool_name, True)

    sockets = platform.sockets.values()
    for socket in sockets:
        pool.add_socket(str(socket.socket_id))
        cores = socket.get_cores_from_pool(pool_name)
        for core in cores:
            cpu_ids_str = ",".join([str(c) for c in core.cpu_ids()])
            pool.add_cpu_list(str(socket.socket_id), cpu_ids_str)
            logging.info("Adding cpu list %s from socket %s to %s pool." %
                         (cpu_ids_str, socket.socket_id, pool_name))


def write_shared_pool(pool_name, platform, config):
    logging.info("Adding %s pool." % pool_name)
    pool = config.add_pool(pool_name, False)

    sockets = platform.sockets.values()
    for socket in sockets:
        pool.add_socket(str(socket.socket_id))
        cores = socket.get_cores_from_pool(pool_name)
        cpu_ids = []
        for core in cores:
            cpu_ids.extend(core.cpu_ids())

        if not cpu_ids:
            continue

        cpu_ids_str = ",".join([str(c) for c in cpu_ids])
        pool.add_cpu_list(str(socket.socket_id), cpu_ids_str)
        logging.info("Adding cpu list %s to %s pool." %
                     (cpu_ids_str, pool_name))
