from . import config, proc
import logging
import sys


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
                        # Verify that CPU affinity is correct.
                        current_allowed = set(p.cpus_allowed())
                        desired_allowed = set(proc.unfold_cpu_list(cl.cpus()))

                        if not (desired_allowed.issubset(current_allowed) and
                           current_allowed.issubset(desired_allowed)):
                            cpusset_mismatch = True

                            logging.error(
                                "mismatch in actual cpu set for pid %d and "
                                "desired cpu set: %s is not %s" %
                                (task,
                                 str(current_allowed),
                                 str(desired_allowed)))

        if cpusset_mismatch:
            logging.error("exiting due to cpuset mismatch")
            sys.exit(1)
