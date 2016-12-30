from . import config
import psutil


def reconcile(conf_dir):
    # TODO: Run reconcile periodically in the background.
    c = config.Config(conf_dir)
    with c.lock():
        for pool_name, pool in c.pools().items():
            for cl in pool.cpu_lists().values():
                for task in cl.tasks():
                    if not psutil.pid_exists(task):
                        cl.remove_task(task)
