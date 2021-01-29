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

from . import config, k8s, topology, discover, sst_bf as sst, sst_cp as cp
import logging
import sys
import os


def init(num_exclusive_cores, num_shared_cores,
         exclusive_allocation_mode, shared_allocation_mode,
         excl_non_isolcpus, namespace):
    check_hugepages()

    logging.info("Requested exclusive cores = {}.".format(num_exclusive_cores))
    logging.info("Requested shared cores = {}.".format(num_shared_cores))

    platform = configure(num_exclusive_cores, num_shared_cores,
                         exclusive_allocation_mode, shared_allocation_mode,
                         excl_non_isolcpus)

    # Use the pod's name to get which node this pod is running on. Use the
    # node name to create the configmap for this node. The configmap holds
    # the CPU configuration that CMK uses for bookkeeping. The node name
    # is used to make the configmap's name unique - it takes the form of
    # 'cmk-config-<node_name>
    pod_name = os.environ["HOSTNAME"]
    node_name = k8s.get_node_from_pod(None, pod_name)
    configmap_name = "cmk-config-{}".format(node_name)
    config.new(platform, excl_non_isolcpus, configmap_name, namespace)


def configure(num_exclusive_cores, num_shared_cores,
              exclusive_allocation_mode, shared_allocation_mode,
              excl_non_isolcpus):
    sst_bf = False
    try:
        sst_bf = discover.get_node_label(sst.NFD_LABEL) in ["true", "True"]
    except Exception as err:
        logging.info("Could not read SST-BF label from the node metadata: {}"
                     .format(err))

    sst_cp = False
    try:
        sst_cp = discover.get_node_label(cp.NFD_LABEL) in ["true", "True"]
    except Exception as err:
        logging.info("Could not read SST-CP label from the node metadata: {}"
                     .format(err))

    platform = topology.discover(sst_bf)

    # List of intel.topology.Core objects.
    cores = platform.get_cores()

    check_isolated_cores(platform, num_exclusive_cores, num_shared_cores)

    if sst_cp and platform.has_isolated_cores():
        epp_order = cp.get_epp_order(platform)

        if len(epp_order) > 3:
            logging.error("There must not be more than 3 EPP values "
                          "among the cores. EPP values present: {}"
                          .format(", ".join(epp_order)))
            sys.exit(1)

        check_sst_cp_isolated_cores(platform, num_exclusive_cores,
                                    num_shared_cores, epp_order)
        logging.info("EPP order: {}".format(", ".join(epp_order)))

        if len(epp_order) == 3:
            sst_cp_exclusive_cores = platform.get_epp_cores(
                 epp_order[0], num_exclusive_cores)
            sst_cp_shared_cores = platform.get_epp_cores(
                 epp_order[1], num_shared_cores)
            sst_cp_infra_cores = platform.get_epp_cores_no_limit(
                 epp_order[2])

            logging.info("Isolated SST-CP exclusive cores (EPP value:"
                         " {}): {}".format(epp_order[0], ",".join(
                          [str(c.core_id) for c in sst_cp_exclusive_cores])))
            logging.info("Isolated SST-CP shared cores (EPP value: {}"
                         "): {}".format(epp_order[1], ",".join(
                          [str(c.core_id) for c in sst_cp_shared_cores])))
            logging.info("SST-CP infra cores (EPP value: {}): {}"
                         .format(epp_order[2], ",".join([str(c.core_id)
                                 for c in sst_cp_infra_cores])))
        elif len(epp_order) == 2:
            logging.info("Only two EPP values set; exclusive and "
                         "shared pools will take all of the cores "
                         "of the highest EPP value")
            sst_cp_exclusive_cores = platform.get_epp_cores(
                 epp_order[0], num_exclusive_cores)
            sst_cp_shared_cores = platform.get_epp_cores(
                 epp_order[0], num_shared_cores, sst_cp_exclusive_cores)
            sst_cp_infra_cores = platform.get_epp_cores_no_limit(
                 epp_order[1])

            logging.info("Isolated SST-CP exclusive cores (EPP value: {}): {}"
                         .format(epp_order[0], ",".join([str(c.core_id)
                                 for c in sst_cp_exclusive_cores])))
            logging.info("Isolated SST-CP shared cores (EPP value: {}): {}"
                         .format(epp_order[0], ",".join([str(c.core_id)
                                 for c in sst_cp_shared_cores])))
            logging.info("SST-CP infra cores (EPP value {}): {}"
                         .format(epp_order[1], ",".join([str(c.core_id)
                                 for c in sst_cp_infra_cores])))
        else:
            logging.error("There must be either 2 or 3 EPP values set among "
                          "the cores. EPP values present: {}".format(
                              ", ".join(epp_order)))
            sys.exit(1)

        assign(sst_cp_exclusive_cores, "exclusive",
               count=num_exclusive_cores)
        assign(sst_cp_shared_cores, "shared",
               count=num_shared_cores)
        check_excl_non_isolcpus(excl_non_isolcpus, platform)
        assign(sst_cp_infra_cores, "infra")

    elif sst_bf and platform.has_isolated_sst_bf_cores():
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
        check_excl_non_isolcpus(excl_non_isolcpus, platform)
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
        check_excl_non_isolcpus(excl_non_isolcpus, platform)
        assign(infra_cores, "infra")
    else:
        logging.info("No isolated physical cores detected: allocating "
                     "shared and exclusive cores from full core list")

        cores_exclusive = platform.get_cores(mode=exclusive_allocation_mode)
        cores_shared = platform.get_cores(mode=shared_allocation_mode)

        assign(cores_exclusive, "exclusive", count=num_exclusive_cores)
        assign(cores_shared, "shared", count=num_shared_cores)
        assign(cores, "infra")

    return platform


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


def check_sst_cp_isolated_cores(platform, num_exclusive_cores,
                                num_shared_cores, epp_order):
    error_occured = False

    if len(epp_order) == 3:
        exclusive_cores = platform.get_epp_cores_no_limit(epp_order[0])
        shared_cores = platform.get_epp_cores_no_limit(epp_order[1])

        if num_exclusive_cores != len(exclusive_cores):
            logging.error("Number of requested exclusive cores must"
                          " match the number of cores with EPP value"
                          " %s. Exclusive cores %d compared to requested %d"
                          % (epp_order[0], len(exclusive_cores),
                             num_exclusive_cores))
            error_occured = True

        if num_shared_cores != len(shared_cores):
            logging.error("Number of requested shared cores must"
                          " match the number of cores with EPP value"
                          " %s. Shared cores %d compared to requested %d"
                          % (epp_order[1], len(shared_cores),
                             num_shared_cores))
            error_occured = True
    elif len(epp_order) == 2:
        requested_cores = num_exclusive_cores + num_shared_cores
        cores = platform.get_epp_cores_no_limit(epp_order[0])

        if len(cores) != requested_cores:
            logging.error("Requested number of isolated cores "
                          "should match number of cores with EPP "
                          "value %s. %d cores requested. %d cores available",
                          epp_order[0], requested_cores, len(cores))
            error_occured = True

    if error_occured:
        sys.exit(1)


def check_excl_non_isolcpus(excl_non_isolcpus, platform):

    # Assigns the cores from excl_non_isolcpus to a new pool called
    # exclusive-non-isolcpus. This pool is for cores that need to be
    # isolated from other user containers but are not governed by
    # isolcpus

    if excl_non_isolcpus != "-1":
        cpus_str = excl_non_isolcpus.split(",")
        # To get rid of negative numbers
        for cpu_list in cpus_str:
            if len(cpu_list) > 2:
                cpu_list = cpu_list.split("-")
            else:
                cpu_list = [cpu_list]
            for cpu in cpu_list:
                if not cpu.isdigit():
                    raise RuntimeError("Invalid core ID: {}".format(cpu))
        cpus = topology.parse_cpus_str(cpus_str)
        all_cores = platform.get_cores()
        assign_excl_non_isolcpus(all_cores, "exclusive-non-isolcpus",
                                 cpus)


def assign(cores, pool, count=None):
    free_cores = [c for c in cores if c.pool is None]

    # always prioritize free SST_BF cores, even if there may be none
    # move up SST_BF cores AND keep order (spread or packet) among
    # SST_BF cores and among non-SST_BF cores
    free_cores.sort(key=lambda c: -c.is_sst_bf(), reverse=False)

    if count is not None and count > 0 and not free_cores:
        raise RuntimeError(
            "No more free cores left to assign for {}".format(pool))

    if pool == 'infra' and not free_cores:
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


def assign_excl_non_isolcpus(cores, pool, parsed_cpus):

    # Assigns cores provided by the user to an addition pool
    # called 'exclusive-non-isolcpus'. These cores are
    # isolated from other user processes but are not placed
    # in isolcpus

    # Catch all the cores that are not on the system
    # Only looking for physical cores - the logical CPUs on each core
    # will be considered not on the system
    cores_not_on_system = []
    for c in parsed_cpus:
        if c >= len(cores):
            cores_not_on_system.append(c)
    if len(cores_not_on_system) > 0:
        raise RuntimeError("Following physical cores not on system: {};"
                           " you may be including logical CPUs of each core"
                           .format(cores_not_on_system))

    cores_to_assign = [c for c in cores if c.core_id in parsed_cpus]
    cores_already_assigned = []
    for core in cores_to_assign:
        if core.pool is not None:
            cores_already_assigned.append(core)
    if len(cores_already_assigned) > 0:
        raise RuntimeError("Core(s) have already been assigned to pool(s): {}"
                           ", cannot add them to exclusive-non-isolcpus pool"
                           .format([c.core_id for c in
                                   cores_already_assigned]))

    unused_isolated_cores = []
    for core in cores_to_assign:
        if core.is_isolated():
            unused_isolated_cores.append(core)
    if len(unused_isolated_cores) > 0:
        raise RuntimeError("Isolated cores {} cannot be placed in"
                           " exclusive-non-isolcpus pool"
                           .format([c.core_id for c in
                                   unused_isolated_cores]))

    logging.info("Logical cores assigned to exclusive-non-isolcpus"
                 " pool: {}".format((",").join(
                  [str(c.core_id) for c in cores_to_assign])))

    for c in cores_to_assign:
        c.pool = pool
