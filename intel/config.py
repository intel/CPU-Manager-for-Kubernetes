import fcntl
import logging
import os
import threading
import _thread


# KCM_LOCK_TIMEOUT is interpreted as seconds.
ENV_LOCK_TIMEOUT = "KCM_LOCK_TIMEOUT"
DEFAULT_LOCK_TIMEOUT = 30


def max_lock_seconds():
    return float(os.getenv(ENV_LOCK_TIMEOUT, DEFAULT_LOCK_TIMEOUT))


# Returns a new config at the supplied path.
def new(path):
    if os.path.isdir(path) and len(os.listdir(path)) > 0:
        raise FileExistsError(
            "Config directory {} already initialized".format(path))
    os.makedirs(os.path.join(path, "pools"))
    open(os.path.join(path, "lock"), "w+")
    return Config(path)


class Config:
    def __init__(self, path):
        self.path = os.path.normpath(path)

    def lock(self):
        fd = os.open(os.path.join(self.path, "lock"), os.O_RDWR)
        return Lock(fd)

    def pools(self):
        pools = {}
        pool_dir = os.path.join(self.path, "pools")
        for f in os.listdir(pool_dir):
            pd = os.path.join(pool_dir, f)
            if os.path.isdir(pd):
                p = Pool(pd)
                pools[p.name()] = p
        return pools

    # Writes a new pool to disk and returns the corresponding pool object.
    def add_pool(self, name, exclusive):
        if name in self.pools():
            raise KeyError("Pool {} already exists".format(name))
        os.makedirs(os.path.join(self.path, "pools", name))
        ex_file = os.path.join(self.path, "pools", name, "exclusive")
        with open(ex_file, "w+") as excl:
            if exclusive:
                excl.write("1")
            else:
                excl.write("0")
            excl.flush()
            os.fsync(excl)
        return self.pools()[name]

    def as_dict(self):
        result = {}
        result["path"] = self.path
        pools = {}
        for _, p in self.pools().items():
            pools[p.name()] = p.as_dict()
        result["pools"] = pools
        return result


class Pool:
    def __init__(self, path):
        self.path = os.path.normpath(path)

    def name(self):
        return os.path.basename(self.path)

    def exclusive(self):
        f = os.path.join(self.path, "exclusive")
        with open(os.path.join(self.path, "exclusive")) as f:
            c = f.read(1)
            if c == "1":
                return True
            return False

    def cpu_lists(self):
        result = {}
        for f in os.listdir(self.path):
            d = os.path.join(self.path, f)
            if os.path.isdir(d):
                clist = CPUList(d)
                result[clist.cpus()] = clist
        return result

    # Writes a new cpu list to disk and returns the corresponding
    # CPUList object.
    def add_cpu_list(self, cpus):
        if cpus in self.cpu_lists():
            raise KeyError("CPU list {} already exists".format(cpus))
        os.makedirs(os.path.join(self.path, cpus))
        open(os.path.join(self.path, cpus, "tasks"), "w+")
        return self.cpu_lists()[cpus]

    def as_dict(self):
        result = {}
        result["exclusive"] = self.exclusive()
        result["name"] = self.name()
        clists = {}
        for _, c in self.cpu_lists().items():
            clists[c.cpus()] = c.as_dict()
        result["cpuLists"] = clists
        return result


class CPUList:
    def __init__(self, path):
        self.path = os.path.normpath(path)

    def cpus(self):
        return os.path.basename(self.path)

    def tasks(self):
        with open(os.path.join(self.path, "tasks")) as f:
            return [int(pid.strip())
                    for pid in f.read().split(",")
                    if pid != ""]

    def __write_tasks(self, tasks):
        # Mode "w+" truncates the file prior to writing new content.
        with open(os.path.join(self.path, "tasks"), "w+") as f:
            f.write(",".join([str(t) for t in tasks]))
            f.flush()
            os.fsync(f)

    # Writes the supplied pid to disk for this cpu list.
    def add_task(self, pid):
        tasks = self.tasks()
        tasks.append(pid)
        self.__write_tasks(tasks)

    # Removes the supplied pid from disk for this cpu list.
    def remove_task(self, pid):
        self.__write_tasks([t for t in self.tasks() if t != pid])

    def as_dict(self):
        result = {}
        result["cpus"] = self.cpus()
        result["tasks"] = self.tasks()
        return result


class Lock:
    def __init__(self, fd):
        self.fd = fd
        self.timer = None

    # Context guard
    def __enter__(self):
        self.__acquire()
        return self

    # Context guard
    def __exit__(self, type, value, traceback):
        self.__release()

    def __acquire(self):
        max_lock = max_lock_seconds()

        def timed_out():
            logging.error("Lock timed out after {} seconds".format(max_lock))
            # NOTE(CD):
            #
            # Bail and rely on the operating system to close the open lock
            # file descriptor. They are closed on our behalf according to
            # the POSIX standard. See https://linux.die.net/man/2/exit
            #
            # We emulate Ctrl-C instead of raising SystemExit via sys.exit()
            # since exceptions are per-thread. SystemExit causes the
            # interpreter to exit if unhandled. This is the only
            # reliable way to trigger an exception in the main thread
            # to make this testable. Open to improvements.
            #
            # The interpreter exits with status 1.
            #
            # See https://goo.gl/RXsXEs
            _thread.interrupt_main()

        self.timer = threading.Timer(max_lock, timed_out)
        self.timer.start()
        # acquire file lock
        fcntl.flock(self.fd, fcntl.LOCK_EX)

    def __release(self):
        self.timer.cancel()
        self.timer = None
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
