import os
import sys
import logging

ENV_PROC_FS = "KCM_PROC_FS"


def procfs():
    proc_fs_path = os.getenv(ENV_PROC_FS)
    if proc_fs_path is None:
        logging.error("environment variable %s is not set: cannot get host process information", ENV_PROC_FS)  # noqa: E501
        sys.exit(1)

    return proc_fs_path


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
