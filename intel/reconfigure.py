from kubernetes import client as k8sclient
from kubernetes import stream
from kubernetes.client.rest import ApiException as K8sApiException
from . import k8s, config, topology, init, clusterinit, util, discover
import logging
import os
import sys
import yaml


class Procs():

    def __init__(self):
        self.process_map = dict()

    def add_proc(self, pid, clist):
        try:
            self.process_map[pid].add_old_clist(clist)
        except KeyError:
            p = Pid()
            p.add_old_clist(clist)
            self.process_map[pid] = p


class ProcessInfo():

    def __init__(self, pool, socket, sockets, clist, pid):
        self.pool = pool
        self.socket = socket
        self.sockets = sockets
        self.old_clist = clist
        self.pid = pid


class Pid():

    def __init__(self):
        self.old_clists = []
        self.new_clist = ""

    def add_old_clist(self, clist):
        self.old_clists.append(clist)

    def add_new_clist(self, clist):
        if self.new_clist == "":
            self.new_clist += "{}".format(clist)
        else:
            self.new_clist += ",{}".format(clist)


def reconfigure(node_name, num_exclusive_cores, num_shared_cores,
                excl_non_isolcpus, exclusive_mode,
                shared_mode, install_dir, namespace):
    # Build the current CMK confurations from the config directory
    pod_name = os.environ["HOSTNAME"]
    node_name = k8s.get_node_from_pod(None, pod_name)
    config_cm = "cmk-config-{}".format(node_name)

    conf = config.Config(config_cm, pod_name)
    num_exclusive_cores = int(num_exclusive_cores)
    num_shared_cores = int(num_shared_cores)

    conf.lock()
    try:
        built_proc_info = build_proc_info(conf.c_data)
        proc_info = built_proc_info[0]
        procs = built_proc_info[1]

        num_excl_non_isols = len(topology.
                                 parse_cpus_str(excl_non_isolcpus.
                                                split(",")))
        check_processes(proc_info, num_exclusive_cores, num_excl_non_isols)

        # Maybe can remove config_cm var and conf.c_data
        conf.c_data = reconfigure_directory(conf.c_data, num_exclusive_cores,
                                            num_shared_cores, exclusive_mode,
                                            shared_mode, excl_non_isolcpus,
                                            proc_info, procs, config_cm)

        configmap_name = "cmk-reconfigure-{}".format(node_name)
        set_config_map(configmap_name, namespace, procs)

        # Run the re-affinitization command in each of the pods on the node
        all_pods = get_pods()
        logging.info("Pods in node {}:".format(node_name))
        logging.info(all_pods)

        execute_reconfigure(install_dir, node_name, all_pods, namespace)

    finally:
        conf.unlock()

        delete_config_map(configmap_name, namespace)


def check_processes(proc_info, num_exclusive_cores, num_excl_non_isols):
    # Check to see if there will be enough cores in the pool to house
    # all processes in the current config

    error_occured = False

    num_exclusive_procs = 0
    num_exclusive_non_isol_procs = 0

    for proc in proc_info:
        if proc.pool == "exclusive":
            num_exclusive_procs += 1
        elif proc.pool == "exclusive-non-isolcpus":
            num_exclusive_non_isol_procs += 1

    if num_exclusive_procs > num_exclusive_cores:
        logging.error("Not enough exclusive cores in new configuration: {}"
                      " processes, {} cores".format(num_exclusive_procs,
                                                    num_exclusive_cores))
        error_occured = True

    if num_exclusive_non_isol_procs > num_excl_non_isols:
        logging.error("Not enough exclusive-non-isolcpus cores in new"
                      " configuration: {} processes, {} cores"
                      .format(num_exclusive_non_isol_procs,
                              num_excl_non_isols))
        error_occured = True

    if error_occured:
        logging.error("Aborting reconfigure...")
        sys.exit(1)


def set_config_map(name, namespace, config):
    configmap = k8sclient.V1ConfigMap()
    data = {
        "config": yaml.dump(config)
    }
    clusterinit.update_configmap(configmap, name, data)
    try:
        k8s.create_config_map(None, configmap, namespace)
    except K8sApiException as err:
        logging.error("Exception when creating config map {}".format(name))
        logging.error(err.reason)
        sys.exit(1)


def delete_config_map(name, namespace):
    try:
        k8s.delete_config_map(None, name, namespace)
    except K8sApiException as err:
        logging.error("Exception when removing config map {}".format(name))
        logging.error(err.reason)
        sys.exit(1)


def reconfigure_directory(c, num_exclusive_cores, num_shared_cores,
                          exclusive_mode, shared_mode, excl_non_isolcpus,
                          proc_info, procs, config_cm):
    platform = init.configure(num_exclusive_cores, num_shared_cores,
                              exclusive_mode, shared_mode,
                              excl_non_isolcpus)

    conf = dict()
    conf = config.update_configmap_exclusive("exclusive", platform, conf)
    conf = config.update_configmap_shared("shared", platform, conf)
    if excl_non_isolcpus != "-1" and platform.has_isolated_cores():
        conf = config.update_configmap_exclusive("exclusive-non-isolcpus",
                                                 platform, conf)
    conf = config.update_configmap_shared("infra", platform, conf)
    conf = config.build_config(conf)

    # Repatch the nodes with ERs/OIRs
    version = util.parse_version(k8s.get_kube_version(None))
    if version == util.parse_version("v1.8.0"):
        logging.fatal("K8s 1.8.0 is not supported. Update K8s to "
                      "version >=1.8.1 or rollback to previous versions")
        sys.exit(1)

    if version >= util.parse_version("v1.8.1"):
        # Patch the node with the appropriate CMK ER.
        logging.debug("Patching the node with the appropriate CMK ER.")
        discover.add_node_er()
    else:
        # Patch the node with the appropriate CMK OIR.
        logging.debug("Patching the node with the appropriate CMK OIR.")
        discover.add_node_oir()

    # How this function works, is it takes the new configuration (after
    # init.configure()) and compares it againts the objects in procs. If
    # it finds that the core list for a process in the previous configuration
    # is also in the  new configuration, it will prioritize giving the process
    # the same core list. If it can't find a core list match, it checks for
    # other cores on the same socket. Again if it can't find another core list
    # on the same socket, it has to move to the next socket until eventually it
    # finds a new core list for the process. There is guaranteed to be an
    # available core list in the new configuration, determined by a previous
    # call to check_processes()

    # This is a way of keeping track of which sokcets we've already tried
    # to assign to the process. The sockets variable takes the form
    # [Bool, Bool, ...] and a False means the socket has failed to
    # satisfy the process' criteria
    def update_sockets(proc):
        proc.sockets[int(proc.socket)] = False
        index = 0
        proc.socket = str(index)
        while not proc.sockets[index]:
            logging.info(index)
            index += 1
            proc.socket = str(index)

    # Get matches for the exclusive pools
    socket_mismatch = []
    clist_mismatch = []
    for proc in proc_info:
        new_pool = conf.get_pool(proc.pool)
        try:
            clists = [cl.core_id for cl in
                      new_pool.get_socket_clists(proc.socket)]
            if len(clists) == 0:
                logging.info("Cannot satisfy socket requirement pool {}"
                             " socket {} clist {}"
                             .format(proc.pool, proc.socket,
                                     proc.old_clist))
                update_sockets(proc)
                socket_mismatch.append(proc)
                continue
            if proc.old_clist in clists:
                cl = new_pool.get_core_list(proc.old_clist, proc.socket)
                logging.info("Core list requirement satisfied pool {}"
                             " socket {} clist {}".format(proc.pool,
                                                          proc.socket,
                                                          proc.old_clist))

                cl.tasks = proc.pid
                for pid in proc.pid:
                    procs.process_map[pid].add_new_clist(cl.core_id)
            else:
                logging.info("Cannot satisfy clist requirement pool {}"
                             " socket {} clist {}".format(proc.pool,
                                                          proc.socket,
                                                          proc.old_clist))
                clist_mismatch.append(proc)
        except FileNotFoundError:
            logging.info("Cannot satisfy socket requirement pool {}"
                         " socket {} clist {}"
                         .format(proc.pool, proc.socket,
                                 proc.old_clist))
            update_sockets(proc)
            socket_mismatch.append(proc)

    # Try to find a match in the same socket first
    for proc in clist_mismatch:
        new_pool = conf.get_pool(proc.pool)
        satisfied = False
        for cl in new_pool.get_socket_clists(proc.socket):
            if len(cl.get_tasks()) == 0:
                cl.tasks = proc.pid
                for pid in proc.pid:
                    procs.process_map[pid].add_new_clist(cl.core_id)
                satisfied = True
                break

        if not satisfied:
            socket_mismatch.append(proc)

    # Move on to other sockets
    for proc in socket_mismatch:
        new_pool = conf.get_pool(proc.pool)
        satisfied = False
        while not satisfied:
            for cl in new_pool.get_socket_clists(proc.socket):
                if len(cl.get_tasks()) == 0:
                    cl.tasks = proc.pid
                    for pid in proc.pid:
                        procs.process_map[pid].add_new_clist(cl.cpus())
                    satisfied = True
                    break

            if not satisfied:
                logging.info("Cannot satisfy socket requirement pool {}"
                             " socket {} clist {}"
                             .format(proc.pool, proc.socket,
                                     proc.old_clist))
                update_sockets(proc)

    return conf


def get_pods():
    all_pods = []
    pods = k8s.get_pod_list(None)
    pod_to_exclude = os.environ["HOSTNAME"]
    for item in pods["items"]:
        if item["status"]["conditions"][0]["reason"] != "PodCompleted"\
           and item["metadata"]["name"] != pod_to_exclude:
            pod = dict()
            pod["name"] = item["metadata"]["name"]
            pod["namespace"] = item["metadata"]["namespace"]
            containers = []
            for c in item["spec"]["containers"]:
                containers.append(c["name"])
            pod["containers"] = containers
            all_pods.append(pod)
    return all_pods


def execute_reconfigure(install_dir, node_name, all_pods, namespace):
    exec_command = ['/opt/bin/cmk', 'reaffinitize',
                    '--node-name={}'.format(node_name),
                    '--namespace={}'.format(namespace)]

    api = k8sclient.CoreV1Api()

    for pod in all_pods:
        logging.info("Executing on pod {} in namespace {}"
                     .format(pod["name"], pod["namespace"]))
        try:
            for c in pod["containers"]:
                resp = stream.stream(api.connect_get_namespaced_pod_exec,
                                     pod["name"], pod["namespace"],
                                     command=exec_command, container=c,
                                     stderr=True, stdin=False, stdout=True,
                                     tty=False, _preload_content=True)
        except K8sApiException as err:
            logging.error("Error occured while executing command in pod: {}"
                          .format(err.reason))
            continue

        logging.info("Response from pod: {}".format(resp))
        logging.info("End of pod response")


def build_proc_info(conf):
    proc_info = []
    procs = Procs()
    pools = []
    for pool in conf.get_pools():
        pools = pools + [pool]
        for socket in conf.get_pool(pool).get_sockets():
            s = conf.get_pool(pool).get_socket(socket)
            for core_list in s.get_core_lists():
                cl = s.get_core_list(core_list)
                pids = cl.get_tasks()
                if len(pids) > 0:
                    p = ProcessInfo(pool, socket, [True, True],
                                    cl.core_id, pids)
                    proc_info.append(p)
                    for process in pids:
                        procs.add_proc(process, cl.core_id)

    for p in pools:
        if p not in ["exclusive", "shared", "infra",
                     "exclusive-non-isolcpus"]:
            logging.error("Error while reading configuration,"
                          " incorrect pool {}".format(p))
            sys.exit(1)

    return (proc_info, procs)
