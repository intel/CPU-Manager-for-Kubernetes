import os


ENV_PROC_FS = "KCM_PROC_FS"
DEFAULT_PROC_FS = "/proc"


def procfs():
    return os.getenv(ENV_PROC_FS, DEFAULT_PROC_FS)


def getpid():
    # The pid is the first field in <procfs>/self/stat
    # See http://man7.org/linux/man-pages/man5/proc.5.html
    with open(os.path.join(procfs(), "self", "stat")) as stat:
        contents = stat.read().split(maxsplit=1)
        pid = int(contents[0])
        return pid


class Process:
    def __init__(self, pid):
        self.pid = int(pid)

    def task_dir(self):
        return os.path.join(procfs(), str(self.pid))

    def exists(self):
        return os.path.exists(self.task_dir())
