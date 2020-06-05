from kubernetes import client as k8sclient
from kubernetes import stream
from kubernetes.client.rest import ApiException as K8sApiException
from . import k8s, config, topology, init, clusterinit
import logging
import shutil
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
                excl_non_isolcpus, conf_dir, exclusive_mode,
                shared_mode, install_dir, namespace):
    # Build the current CMK confurations from the config directory

    c = config.Config(conf_dir)
    num_exclusive_cores = int(num_exclusive_cores)
    num_shared_cores = int(num_shared_cores)

    built_config = build_config_map(conf_dir)
    proc_info = built_config[0]
    procs = built_config[1]

    num_excl_non_isols = len(topology.
                             parse_cpus_str(excl_non_isolcpus.split(",")))
    check_processes(proc_info, num_exclusive_cores, num_excl_non_isols)

    reconfigure_directory(c, conf_dir, num_exclusive_cores,
                          num_shared_cores, exclusive_mode, shared_mode,
                          excl_non_isolcpus, proc_info, procs)

    set_config_map("cmk-config", namespace, procs)

    # Run the re-affinitization command in each of the pods on the node
    all_pods = get_pods()
    logging.info("Pods in node {}:".format(node_name))
    logging.info(all_pods)

    execute_reconfigure(install_dir, node_name, all_pods, namespace)

    delete_config_map("cmk-config", namespace)


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


def reconfigure_directory(c, conf_dir, num_exclusive_cores, num_shared_cores,
                          exclusive_mode, shared_mode, excl_non_isolcpus,
                          proc_info, procs):
    # Reconfigure the config directory with the updated configuration

    with c.lock():
        shutil.rmtree("{}/pools".format(conf_dir))
        os.makedirs("{}/pools".format(conf_dir))

    init.configure(c, conf_dir, num_exclusive_cores, num_shared_cores,
                   exclusive_mode, shared_mode, excl_non_isolcpus)

    def update_sockets(proc):
        proc.sockets[int(proc.socket)] = False
        index = 0
        proc.socket = str(index)
        while not proc.sockets[index]:
            index += 1
            proc.socket = str(index)

    # Get matches for the exclusive pools
    socket_mismatch = []
    clist_mismatch = []
    for proc in proc_info:
        with c.lock():
            pools = c.pools()
            p = pools[proc.pool]
            try:
                clists = p.socket_cpu_list(proc.socket)
                if len(clists) == 0:
                    logging.info("Cannot satisfy socket requirement pool {}"
                                 " socket {} clist {}"
                                 .format(proc.pool, proc.socket,
                                         proc.old_clist))
                    update_sockets(proc)
                    socket_mismatch.append(proc)
                    continue
                try:
                    cl = clists[proc.old_clist]
                    logging.info("Core list requirement satisfied pool {}"
                                 " socket {} clist {}".format(proc.pool,
                                                              proc.socket,
                                                              proc.old_clist))
                    cl.add_task(",".join(proc.pid))
                    for pid in proc.pid:
                        procs.process_map[pid].add_new_clist(cl.cpus())
                except KeyError:
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
        with c.lock():
            pools = c.pools()
            p = pools[proc.pool]
            satisfied = False
            for cl in p.socket_cpu_list(proc.socket).values():
                if len(cl.tasks()) == 0:
                    cl.add_task(",".join(proc.pid))
                    for pid in proc.pid:
                        procs.process_map[pid].add_new_clist(cl.cpus())
                    satisfied = True
                    break

            if not satisfied:
                socket_mismatch.append(proc)

    # Move on to other sockets
    for proc in socket_mismatch:
        with c.lock():
            pools = c.pools()
            p = pools[proc.pool]
            clists = p.socket_cpu_list(proc.socket).values()
            satisfied = False
            while not satisfied:
                clists = p.socket_cpu_list(proc.socket).values()
                for cl in p.socket_cpu_list(proc.socket).values():
                    if len(cl.tasks()) == 0:
                        cl.add_task(",".join(proc.pid))
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
    k8s.client_from_config(None)
    c = k8sclient.Configuration()
    c.assert_hostname = False
    k8sclient.Configuration.set_default(c)
    core_v1 = k8sclient.CoreV1Api()

    exec_command = ['{}/cmk'.format(install_dir), 'reaffinitize',
                    '--node-name={}'.format(node_name),
                    '--namespace={}'.format(namespace)]
    for pod in all_pods:
        logging.info("Executing on pod {} in namespace {}"
                     .format(pod["name"], pod["namespace"]))
        try:
            for c in pod["containers"]:
                resp = stream.stream(core_v1.connect_get_namespaced_pod_exec,
                                     pod["name"], pod["namespace"],
                                     command=exec_command, container=c,
                                     stderr=True, stdin=False, stdout=True,
                                     tty=False)
        except K8sApiException as err:
            logging.error("Error occured while executing command in pod: {}"
                          .format(err.reason))
            continue

        logging.info("Response from pod: {}".format(resp))
        logging.info("End of pod response")


def build_config_map(path):
    path = "{}/pools".format(path)
    proc_info = []
    procs = Procs()
    pools = []
    for pool in os.listdir(path):
        pools = pools + [pool]
        for socket in os.listdir("{}/{}".format(path, pool)):
            if os.path.isdir("{}/{}/{}".format(path, pool, socket)):
                for core_list in os.listdir("{}/{}/{}"
                                            .format(path, pool, socket)):
                    with open("{}/{}/{}/{}/tasks"
                              .format(path, pool, socket, core_list)) as f:
                        pid = f.read().strip()
                        if pid != '':
                            sockets = [True for s in
                                       os.listdir("{}/{}".format(path, pool))
                                       if
                                       os.path.isdir("{}/{}/{}"
                                                     .format(path, pool, s))]
                            processes = [p for p in pid.split(",")]
                            p = ProcessInfo(pool, socket, sockets,
                                            core_list, processes)
                            proc_info.append(p)
                            for process in processes:
                                procs.add_proc(process, core_list)

    for p in pools:
        if p not in ["exclusive", "shared", "infra",
                     "exclusive-non-isolcpus"]:
            logging.error("Error while reading configuration"
                          " at {}, incorrect pool {}".format(path, p))
            sys.exit(1)

    return (proc_info, procs)
