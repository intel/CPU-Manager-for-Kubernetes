# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from . import config, proc
import logging
import os
import random
import psutil
import signal
import subprocess

ENV_CPUS_ASSIGNED = "CMK_CPUS_ASSIGNED"
ENV_CPUS_INFRA = "CMK_CPUS_INFRA"
ENV_NUM_CORES = "CMK_NUM_CORES"


def isolate(conf_dir, pool_name, no_affinity, command, args, socket_id=None):
    c = config.Config(conf_dir)
    with c.lock():
        pools = c.pools()
        if pool_name not in pools:
            raise KeyError("Requested pool {} does not exist"
                           .format(pool_name))
        pool = pools[pool_name]

        socket_aware_pools = ["exclusive", "shared"]
        if socket_id == "-1" or pool_name not in socket_aware_pools:
            selected_socket = None
        else:
            selected_socket = socket_id

        # Read env variable and if unset return 1
        n_cpus = int(os.getenv(ENV_NUM_CORES, 1))

        if n_cpus < 1:
            raise ValueError("Requested numbers of cores "
                             "must be positive integer")

        clists = None
        if pool.exclusive():
            available_clists = [cl for
                                cl in pool.cpu_lists(selected_socket).values()
                                if len(cl.tasks()) == 0]

            if len(available_clists) < n_cpus:
                raise SystemError("Not enough free cpu lists in pool {}"
                                  .format(pool_name))

            clists = available_clists[:n_cpus]
        else:
            # NOTE(CD): This allocation algorithm is probably an
            # oversimplification, however for known use cases the non-exclusive
            # pools should never have more than one cpu list anyhow.
            # If that ceases to hold in the future, we could explore population
            # or load-based spreading. Keeping it simple for now.
            try:
                if pool_name in socket_aware_pools:
                    clists = [random.choice(
                             list(pool.cpu_lists(selected_socket).values()))]
                else:
                    clists = [random.choice(list(pool.cpu_lists().values()))]
            except IndexError:
                raise SystemError("No cpu lists in pool {}".format(pool_name))

        if not clists:
            raise SystemError("No free cpu lists in pool {}".format(pool_name))

        for cl in clists:
            cl.add_task(proc.getpid())

    # NOTE: we spawn the child process after exiting the config lock context.
    try:
        # Advertise assigned CPU IDs in the environment.
        clists.sort(key=lambda cl: cl.cpus())
        cpu_ids = ','.join([cl.cpus() for cl in clists])
        os.environ[ENV_CPUS_ASSIGNED] = cpu_ids

        # Advertise infra pool CPU IDs
        infra_pool = pools.get("infra")
        if infra_pool is not None:
            infra_clists = [cl.cpus()
                            for cl
                            in infra_pool.cpu_lists().values()]
            os.environ[ENV_CPUS_INFRA] = ','.join(infra_clists)

        # We use psutil here (instead of the cmk provided
        # process abstraction) as we need to change the affinity of the current
        # process. This, in turn, is done through a system call which does
        # not allow us to reference host PIDs. In this case, it is OK to
        # operate within the PID namespace as we are changing our own affinity
        # and count on the child processes inheriting the affinity settings.
        p = psutil.Process()

        if no_affinity:
            logging.info("""Not setting CPU affinity before forking the child \
command because the --no-affinity flag was supplied""")

        else:
            cpu_list = proc.unfold_cpu_list(cpu_ids)
            logging.debug("Setting CPU affinity to %s", cpu_list)
            p.cpu_affinity(cpu_list)

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
            for cl in clists:
                cl.remove_task(proc.getpid())
