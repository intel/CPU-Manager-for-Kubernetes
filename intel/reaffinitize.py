from . import k8s
from kubernetes.client.rest import ApiException as K8sApiException
import logging
import psutil
import sys
import yaml


def reaffinitize(node_name, namespace):

    configmap_name = "cmk-reconfigure-{}".format(node_name)
    procs = get_config_from_configmap(configmap_name, namespace)
    reaffinitize_cores(procs)


def get_config_from_configmap(name, namespace):
    try:
        config = k8s.get_config_map(None, name, namespace)
        config = yaml.safe_load(config["config"])
    except K8sApiException as err:
        logging.error("Error while retreiving configmap {}".format(name))
        logging.error(err.reason)
        sys.exit(1)
    return config


def reaffinitize_cores(procs):
    # Reaffinitize works on the assumption that the process that are
    # running the pinned workloads are all children of the main
    # process in the pod. It takes the first process from the /procs
    # directory and works its way down each child process, reassigning
    # the process based on information in the procs parameter

    p = psutil.Process(1)
    while True:
        affin = p.cpu_affinity()
        affin_found = False
        for pid in list(procs.process_map.keys()):
            cl = ",".join(procs.process_map[pid].old_clists)
            correct_clist = [int(c) for c in cl.split(",")]
            if set(correct_clist) == set(affin):
                new_affin = [int(c) for c in
                             procs.process_map[pid].new_clist.split(",")]
                logging.info("New core alignment: {}"
                             .format(new_affin))
                affin_found = True
                p.cpu_affinity(new_affin)
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
