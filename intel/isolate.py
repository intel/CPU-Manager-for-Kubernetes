from . import config, proc
import logging
import random
import psutil
import signal
import subprocess


def isolate(conf_dir, pool_name, command, args):
    c = config.Config(conf_dir)
    with c.lock():
        pools = c.pools()
        if pool_name not in pools:
            raise KeyError("Requested pool {} does not exist"
                           .format(pool_name))
        pool = pools[pool_name]
        if pool.exclusive():
            for cl in pool.cpu_lists().values():
                if len(cl.tasks()) == 0:
                    clist = cl
                    break
        else:
            # NOTE(CD): This allocation algorithm is probably an
            # oversimplification, however for known use cases the non-exclusive
            # pools should never have more than one cpu list anyhow.
            # If that ceases to hold in the future, we could explore population
            # or load-based spreading. Keeping it simple for now.
            clist = random.choice(list(pool.cpu_lists().values()))
        if not clist:
            raise SystemError("No free cpu lists in pool {}".format(pool_name))
        clist.add_task(proc.getpid())
    # NOTE: we spawn the child process after exiting the config lock context.
    try:
        # We use psutil here (instead of the kcm provided
        # process abstraction) as we need to change the affinity of the current
        # process. This, in turn, is done through a system call which does
        # not allow us to reference host PIDs. In this case, it is OK to
        # operate within the PID namespace as we are changing our own affinity
        # and count on the child processes inheriting the affinity settings.
        p = psutil.Process()
        cpu_list = proc.unfold_cpu_list(clist.cpus())
        p.cpu_affinity(cpu_list)

        logging.debug("Setting affinity to %s", cpu_list)

        child = subprocess.Popen("{} {}".format(command,
                                 " ".join(args)),
                                 shell=True)

        # Register a signal handler for TERM so that we can attempt to leave
        # things in a consistent state. As a good POSIX citizen, we propagate
        # the TERM signal to the child so that it also has a chance to clean
        # up if it needs to. For reference on POSIX systems:
        # - `subprocess.Popen.terminate()` sends TERM
        # - `subprocess.Popen.kill()` sends KILL
        signal.signal(signal.SIGTERM, child.terminate)

        # Block waiting for the child process to exit.
        child.wait()

    finally:
        with c.lock():
            clist.remove_task(proc.getpid())
