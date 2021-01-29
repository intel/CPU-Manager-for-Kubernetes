from . import clusterinit, k8s
from kubernetes import client as k8sclient
from kubernetes.client.rest import ApiException as K8sApiException
import logging
import sys
import yaml
import time
import random


exclusivity = {
    "exclusive": True,
    "exclusive-non-isolcpus": True,
    "shared": False,
    "infra": False
}


class Config:

    def __init__(self, cm_name, owner, cm_namespace):
        self.c = None
        self.c_data = None
        self.cm_name = cm_name
        self.owner = owner
        self.cm_namespace = cm_namespace

    def lock(self):
        # The lock function is used to avoid two isolate
        # commands simultaneously making updates to the
        # CMK configuration configmap that is associated
        # with the appropriate node. It does so by updating
        # the configmap's 'owner' annotation with the name of the
        # pod updating it. If the the 'owner' annotation is not
        # an empty string then the configmap is considered
        # 'locked'

        # The sleep is added in case multiple pods are created at
        # the same time so they don't try and claim the configmap at
        # the same time
        time.sleep(random.random())
        while True:
            try:
                c = k8s.get_config_map(None, self.cm_name, self.cm_namespace)
                owner = c.metadata.annotations["Owner"]
                if owner != "":
                    time.sleep(1)
                    continue
                else:
                    c.metadata.annotations["Owner"] = self.owner
                    try:
                        k8s.patch_config_map(None, self.cm_name,
                                             c, self.cm_namespace)
                    except K8sApiException as err:
                        logging.error("Error while retreiving configmap {}"
                                      .format(self.cm_name))
                        logging.error(err.reason)
                        sys.exit(1)

                self.c = c
                self.c_data = build_config(yaml.safe_load(c.data["config"]))
                break
            except K8sApiException as err:
                logging.error("Error while retreiving configmap {}"
                              .format(self.cm_name))
                logging.error(err.reason)
                sys.exit(1)

    def unlock(self):
        self.c.metadata.annotations["Owner"] = ""
        config = build_configmap(self.c_data)
        configmap = k8sclient.V1ConfigMap()
        data = {
            "config": yaml.dump(config)
        }
        clusterinit.update_configmap(configmap, self.cm_name, data)
        try:
            k8s.patch_config_map(None, self.cm_name,
                                 configmap, self.cm_namespace)
        except K8sApiException as err:
            logging.error("Error while retreiving configmap {}"
                          .format(self.cm_name))
            logging.error(err.reason)
            sys.exit(1)
        self.c = None
        self.c_data = None

    def add_pool(self, exclusive, name):
        self.c_data.add_pool(exclusive, name)

    def get_pool(self, name):
        return self.c_data.get_pool(name)

    def get_pools(self):
        return self.c_data.get_pools()

    def as_dict(self):
        return self.c_data.as_dict()


class Conf:

    def __init__(self):
        self.pools = dict()

    def add_pool(self, exclusive, name):
        p = Pool(exclusive, name)
        self.pools[name] = p

    def get_pool(self, name):
        return self.pools[name]

    def get_pools(self):
        return self.pools.keys()

    def as_dict(self):
        result = {}
        pools = {}
        for pool in self.get_pools():
            pools[pool] = self.get_pool(pool).as_dict()
        result["pools"] = pools
        return result


class Pool:

    def __init__(self, exclusive, name):
        self.exclusive = exclusive
        self.name = name
        self.sockets = dict()

    def is_exclusive(self):
        return self.exclusive

    def add_socket(self, socket_id):
        s = Socket(socket_id)
        self.sockets[socket_id] = s

    def get_socket(self, socket_id):
        return self.sockets[socket_id]

    def get_sockets(self):
        return self.sockets.keys()

    def get_core_lists(self, socket_id=None):
        if socket_id:
            return self.get_socket_clists(socket_id)

        cores = []
        for socket in self.get_sockets():
            s = self.get_socket(socket)
            cores += [s.get_core_list(cl)
                      for cl in s.get_core_lists()]
        return cores

    def get_socket_clists(self, socket_id):
        s = self.get_socket(socket_id)
        return [s.get_core_list(cl) for cl in s.get_core_lists()]

    def get_core_list(self, cl, socket_id=None):
        if socket_id:
            return self.get_socket(socket_id).get_core_list(cl)

        for socket in self.get_sockets():
            try:
                return self.get_socket(socket).get_core_list(cl)
            except KeyError:
                continue

    def update_clist(self, cl, pid):
        for socket in self.get_sockets():
            try:
                core_list = self.get_socket(socket).get_core_list(cl)
                core_list.add_task(pid)
                return
            except KeyError:
                continue

    def remove_task(self, cl, pid):
        for socket in self.get_sockets():
            try:
                core_list = self.get_socket(socket).get_core_list(cl)
                core_list.remove_task(pid)
                return
            except KeyError:
                continue

    def as_dict(self):
        result = {}
        result["exclusive"] = self.is_exclusive()
        result["name"] = self.name
        clists = {}
        for cl in self.get_core_lists():
            clists[cl.core_id] = cl.as_dict()
        result["cpuLists"] = clists
        return result


class Socket:

    def __init__(self, socket_id):
        self.socket_id = socket_id
        self.core_lists = dict()

    def add_core_list(self, core_id):
        cl = CoreList(core_id)
        self.core_lists[core_id] = cl

    def get_core_list(self, core_id):
        return self.core_lists[core_id]

    def get_core_lists(self):
        return self.core_lists.keys()


class CoreList:

    def __init__(self, core_id):
        self.core_id = core_id
        self.tasks = []

    def add_task(self, task):
        self.tasks += [task]

    def remove_task(self, task):
        self.tasks = [t for t in self.tasks if t != task]

    def get_tasks(self):
        return self.tasks

    def as_dict(self):
        result = {}
        result["cpus"] = self.core_id
        result["tasks"] = self.get_tasks()
        return result


def new(platform, excl_non_isolcpus, name, namespace):
    # Creates the new CMK configuration for the node. It create a
    # configmap object and POSTs it to the K8s API Server

    config = dict()
    config = update_configmap_exclusive("exclusive", platform, config)
    config = update_configmap_shared("shared", platform, config)
    if excl_non_isolcpus != "-1" and platform.has_isolated_cores():
        config = update_configmap_exclusive("exclusive-non-isolcpus",
                                            platform, config)
    config = update_configmap_shared("infra", platform, config)
    data = {
        "config": yaml.dump(config)
    }

    configmap = k8s.get_config_map(None, name, namespace)

    if configmap is None:
        configmap = k8sclient.V1ConfigMap()
        clusterinit.update_configmap(configmap, name, data)

        try:
            k8s.create_config_map(None, configmap, namespace)
        except K8sApiException as err:
            logging.error("Exception when creating config map {}"
                          .format(name))
            logging.error(err.reason)
            sys.exit(1)
    else:
        clusterinit.update_configmap(configmap, name, data)
        try:
            k8s.patch_config_map(None, name, configmap, namespace)
        except K8sApiException as err:
            logging.error("Error while patching configmap {}"
                          .format(name))
            logging.error(err.reason)
            sys.exit(1)


def update_configmap_exclusive(pool_name, platform, config):
    # Creates the pool 'pool_name' in the config and sets it up
    # to be a exclusive pool

    logging.info("Adding %s pool." % pool_name)
    config[pool_name] = dict()
    sockets = platform.sockets.values()
    for socket in sockets:
        config[pool_name][socket.socket_id] = dict()
        cores = socket.get_cores_from_pool(pool_name)

        for core in cores:
            cpu_ids_str = ",".join([str(c) for c in core.cpu_ids()])
            config[pool_name][socket.socket_id][cpu_ids_str] = []
    return config


def update_configmap_shared(pool_name, platform, config):
    # Creates the pool 'pool_name' in the config and sets it up
    # to be a shared pool

    logging.info("Adding %s pool." % pool_name)
    config[pool_name] = dict()
    sockets = platform.sockets.values()
    for socket in sockets:
        config[pool_name][socket.socket_id] = dict()
        cores = socket.get_cores_from_pool(pool_name)
        cpu_ids = []
        for core in cores:
            cpu_ids.extend(core.cpu_ids())

        if not cpu_ids:
            continue

        cpu_ids_str = ",".join([str(c) for c in cpu_ids])
        config[pool_name][socket.socket_id][cpu_ids_str] = []
    return config


def build_config(c):
    # Builds the CMK configuration from the configmap c. it builds it
    # into the Conf class

    config = Conf()
    for pool in c.keys():
        config.add_pool(exclusivity[pool], pool)
        for socket in c[pool].keys():
            config.pools[pool].add_socket(socket)
            for core_list in c[pool][socket].keys():
                config.pools[pool].sockets[socket].add_core_list(core_list)
                for task in c[pool][socket][core_list]:
                    config.pools[pool].sockets[socket]\
                                 .core_lists[core_list].add_task(task)

    return config


def build_configmap(c):
    config = dict()
    for pool in c.get_pools():
        config[pool] = dict()
        for socket in c.pools[pool].get_sockets():
            config[pool][socket] = dict()
            s = c.pools[pool].get_socket(socket)
            for core_list in s.get_core_lists():
                tasks = s.get_core_list(core_list).tasks
                config[pool][socket][core_list] = tasks

    return config
