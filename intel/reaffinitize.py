from . import k8s
from kubernetes.client.rest import ApiException as K8sApiException
import logging
import psutil
import sys
import yaml


def reaffinitize(node_name, namespace):

    old_config = get_config_from_configmap("old-cmk-config", namespace)
    logging.info("Old CMK config:")
    logging.info(old_config)

    new_config = get_config_from_configmap("new-cmk-config", namespace)
    logging.info("New CMK config:")
    logging.info(new_config)

    core_alignment = get_core_alignment(old_config, new_config)
    logging.info("Core alignment:")
    logging.info(core_alignment)
    reaffinitize_cores(core_alignment)


def get_config_from_configmap(name, namespace):
    try:
        config = k8s.get_config_map(None, name, namespace)
        config = yaml.load(config["config"], Loader=yaml.FullLoader)
    except K8sApiException as err:
        logging.error("Error while retreiving configmap {}".format(name))
        logging.error(err.reason)
        sys.exit(1)
    return config


def get_core_alignment(old_config, new_config):
    core_alignment = dict()
    for pool in old_config.keys():
        for socket in old_config[pool].keys():
            for core_list in old_config[pool][socket].keys():
                if old_config[pool][socket][core_list] != []:
                    for pool2 in new_config.keys():
                        for socket2 in new_config[pool2].keys():
                            for core_list2 in new_config[pool2][socket2]\
                                              .keys():
                                if new_config[pool2][socket2][core_list2]\
                                   == old_config[pool][socket][core_list]:
                                    core_alignment[core_list] = core_list2
    return core_alignment


def reaffinitize_cores(core_alignment):
    p = psutil.Process(1)
    while True:
        affin = p.cpu_affinity()
        affin_found = False
        for core_list in core_alignment.keys():
            # Have to correct core_list syntax because CMK holds the CPU
            # numbers differently to how cpu_affinity returns them
            correct_core_list = [int(c) for c in core_list.split(",")]
            # Use set() here so we don't have to worry about the
            # ordering of the cores
            if set(correct_core_list) == set(affin):
                new_alignment = [int(c) for c in core_alignment[core_list]
                                 .split(",")]
                logging.info("New core alignment: {}"
                             .format(core_alignment[core_list]))
                affin_found = True
                p.cpu_affinity(new_alignment)
                break
        if not affin_found:
            # If the process's affinity doesn't match any of the
            # ones in core_alignment we can just ignore it and
            # move onto its child process.
            logging.info("No affinity found, leaving as old value {}"
                         .format(affin))
        try:
            p = p.children()[0]
        except IndexError:
            break
