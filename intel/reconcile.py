from . import config, proc
import logging
import sys


def is_cpuset_mismatch(process, desired_allowed):
    # Verify that CPU affinity is correct.
    current_allowed = set(process.cpus_allowed())

    if not (desired_allowed.issubset(current_allowed) and
       current_allowed.issubset(desired_allowed)):

        logging.error(
            "mismatch in actual cpu set for pid %d and "
            "desired cpu set: %s is not %s" %
            (process.pid,
             str(current_allowed),
             str(desired_allowed)))

        return True

    return False


def reconcile(conf_dir):
    # TODO: Run reconcile periodically in the background.
    c = config.Config(conf_dir)
    with c.lock():
        cpusset_mismatch = False

        for pool_name, pool in c.pools().items():
            for cl in pool.cpu_lists().values():
                for task in cl.tasks():
                    p = proc.Process(task)

                    if not p.exists():
                        cl.remove_task(task)
                    else:
                        cpusset_mismatch |= is_cpuset_mismatch(
                            p, set(proc.unfold_cpu_list(cl.cpus())))

        if cpusset_mismatch:
            logging.error("exiting due to cpuset mismatch")
            sys.exit(1)
