from kubernetes import client as k8sclient
from kubernetes import stream
from kubernetes.client.rest import ApiException as K8sApiException
from . import k8s, config, topology, init, clusterinit
import logging
import shutil
import os
import random
import sys
import yaml


def reconfigure(node_name, num_exclusive_cores, num_shared_cores,
                excl_non_isolcpus, conf_dir, exclusive_mode,
                shared_mode, install_dir, namespace):
    # Build the current CMK confurations from the config directory
    c = config.Config(conf_dir)
    num_exclusive_cores = int(num_exclusive_cores)
    num_shared_cores = int(num_shared_cores)

    old_config = set_config_map("old-cmk-config", namespace, conf_dir)

    err = check_processes(old_config, "exclusive", num_exclusive_cores)
    if err != "":
        logging.error("Error while checking processes: {}".format(err))
        sys.exit(1)

    num_excl_non_isols = len(topology.
                             parse_cpus_str(excl_non_isolcpus.split(",")))
    err = check_processes(old_config, "exclusive-non-isolcpus",
                          num_excl_non_isols)
    if err != "":
        logging.error("Error while checking processes: {}".format(err))
        sys.exit(1)

    reconfigure_directory(c, old_config, conf_dir, num_exclusive_cores,
                          num_shared_cores, exclusive_mode, shared_mode,
                          excl_non_isolcpus)

    # Get the new CMK configuration from the config directory
    _ = set_config_map("new-cmk-config", namespace, conf_dir)

    # Run the re-affinitization command in each of the pods on the node
    all_pods = get_pods()
    logging.info("Pods in node {}:".format(node_name))
    logging.info(all_pods)

    execute_reconfigure(install_dir, node_name, all_pods, namespace)

    delete_config_map("old-cmk-config", namespace)
    delete_config_map("new-cmk-config", namespace)


def check_processes(config, pool_name, num_cores):
    # Check to see if there will be enough cores in the pool to house
    # all processes in the current config
    error_msg = ""

    try:
        num_processes = 0
        for socket in config[pool_name].keys():
            for core_list in config[pool_name][socket]:
                if len(config[pool_name][socket][core_list]) > 0:
                    num_processes += 1
        if num_processes > num_cores:
            error_msg = "Not enough {} cores in new configuration: {}"\
                        " processes, {} cores".format(pool_name, num_processes,
                                                      num_cores)
    except KeyError:
        logging.info("{} pool not detected, continuing reconfiguration"
                     .format(pool_name))

    return error_msg


def set_config_map(name, namespace, conf_dir):
    config = build_config_map(conf_dir)
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
    return config


def delete_config_map(name, namespace):
    try:
        k8s.delete_config_map(None, name, namespace)
    except K8sApiException as err:
        logging.error("Exception when removing config map {}".format(name))
        logging.error(err.reason)
        sys.exit(1)


def reconfigure_directory(c, old_config, conf_dir, num_exclusive_cores,
                          num_shared_cores, exclusive_mode, shared_mode,
                          excl_non_isolcpus):

    # Reconfigure the config directory with the updated configuration

    with c.lock():
        shutil.rmtree("{}/pools".format(conf_dir))
        os.makedirs("{}/pools".format(conf_dir))

    init.configure(c, conf_dir, num_exclusive_cores, num_shared_cores,
                   exclusive_mode, shared_mode, excl_non_isolcpus)

    # Get matches for the exclusive pools

    crossovers = dict()
    for pool in old_config.keys():
        if pool in ["exclusive", "exclusive-non-isolcpus"]:
            if pool not in crossovers.keys():
                crossovers[pool] = dict()
            for socket in old_config[pool].keys():
                crossovers[pool][socket] = []
                with c.lock():
                    pools = c.pools()
                    p = pools[pool]
                    new_pool_cores = [cl.cpus() for cl in p.cpu_lists(socket)
                                      .values()]
                crossover_cores = []
                for core_list in old_config[pool][socket]:
                    if core_list in new_pool_cores and\
                       old_config[pool][socket][core_list] != []:
                        crossover_cores = crossover_cores + [core_list]
                crossovers[pool][socket] = crossover_cores

    for pool in crossovers.keys():
        for socket in crossovers[pool].keys():
            for core_list in crossovers[pool][socket]:
                pid = old_config[pool][socket][core_list][0]
                logging.info(pid)
                with c.lock():
                    pools = c.pools()
                    p = pools[pool]
                    clist = p.cpu_list(socket, core_list)
                    clist.add_task(pid)

    excluded = []
    for pool in old_config.keys():
        for socket in old_config[pool].keys():
            try:
                excluded = crossovers[pool][socket]
            except KeyError:
                logging.info("No cores to be excluded in this pool/socket")
            for core in old_config[pool][socket].keys():
                if old_config[pool][socket][core] != [] and\
                   core not in excluded:
                    logging.info("Reassigning PID(s) {} from pool {}"
                                 " socket {}".format(old_config[pool]
                                                     [socket][core],
                                                     pool, socket))
                    for pid in old_config[pool][socket][core]:
                        with c.lock():
                            pools = c.pools()
                            p = pools[pool]
                            if pool not in ["exclusive", "shared",
                                            "exclusive-non-isolcpus"]:
                                socket = None
                            clists = None
                            if p.exclusive():
                                num_cpus = 1
                                available_clists = [cl for cl in
                                                    p.cpu_lists(socket)
                                                    .values() if
                                                    len(cl.tasks()) == 0]
                                if len(available_clists) < num_cpus:
                                    raise SystemError("Not enough free"
                                                      " cpu lists in pool {}"
                                                      .format(pool))

                                clists = available_clists[:num_cpus]
                            else:
                                try:
                                    if pool in ["exclusive", "shared",
                                                "exclusive-non-isolcpus"]:
                                        clists = [random.choice(list(
                                                  p.cpu_lists(socket)
                                                  .values()))]
                                    else:
                                        clists = [random.choice(list(
                                                  p.cpu_lists().values()))]
                                except IndexError:
                                    raise SystemError("No cpu lists in pool {}"
                                                      .format(pool))

                            if not clists:
                                raise SystemError("No free cpu lists in pool"
                                                  " {}".format(pool))

                            for cl in clists:
                                cl.add_task(pid)


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
    cmk_config = dict()
    for d in os.listdir(path):
        cmk_config[d] = dict()
        for socket in os.listdir("{}/{}".format(path, d)):
            if os.path.isdir("{}/{}/{}".format(path, d, socket)):
                cmk_config[d][socket] = dict()
                for core_list in os.listdir("{}/{}/{}"
                                            .format(path, d, socket)):
                    cmk_config[d][socket][core_list] = []
                    with open("{}/{}/{}/{}/tasks"
                              .format(path, d, socket, core_list)) as f:
                        pid = f.read().strip()
                        if pid != '':
                            for item in pid.split(","):
                                cmk_config[d][socket][core_list]\
                                    .append(item)

    for pool in cmk_config.keys():
        if pool not in ["exclusive", "shared", "infra",
                        "exclusive-non-isolcpus"]:
            logging.error("Error while reading configuration"
                          " at {}, incorrect pool {}".format(path, pool))
            sys.exit(1)
    return cmk_config
