import fcntl

import os


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
            return [int(pid.strip()) for pid in f.read().split(",")]

    def as_dict(self):
        result = {}
        result["cpus"] = self.cpus()
        result["tasks"] = self.tasks()
        return result


class Lock:
    def __init__(self, fd):
        self.fd = fd

    # Context guard
    def __enter__(self):
        # acquire file lock
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    # Context guard
    def __exit__(self, type, value, traceback):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
