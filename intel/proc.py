import os
import logging

ENV_PROC_FS = "KCM_PROC_FS"


def procfs():
    proc_fs_path = os.getenv(ENV_PROC_FS)
    if proc_fs_path is None:
        logging.error("environment variable %s is not set: cannot get host process information", ENV_PROC_FS)  # noqa: E501
        raise SystemExit(1)

    return proc_fs_path


def getpid():
    # The pid is the first field in <procfs>/self/stat
    # See http://man7.org/linux/man-pages/man5/proc.5.html
    with open(os.path.join(procfs(), "self", "stat")) as stat:
        contents = stat.read().split(maxsplit=1)
        pid = int(contents[0])
        return pid


def unfold_cpu_list(list):
    cpu_list = []
    for cpu_range in list.split(','):
        cpu_range_boundaries = cpu_range.split('-')
        num_cpu_range_boundaries = len(cpu_range_boundaries)

        if num_cpu_range_boundaries == 1:
            cpu_list.append(int(cpu_range_boundaries[0]))

        elif num_cpu_range_boundaries == 2:
            start = int(cpu_range_boundaries[0])
            end = int(cpu_range_boundaries[1])
            cpu_list.extend(range(start, end + 1))

    return cpu_list


class Process:
    def __init__(self, pid):
        self.pid = int(pid)

    def task_dir(self):
        return os.path.join(procfs(), str(self.pid))

    def exists(self):
        return os.path.exists(self.task_dir())

    def cpus_allowed(self):
        with open(os.path.join(procfs(), str(self.pid), "status")) as status:
            for line in status:
                fields = line.split(":")
                if len(fields) is not 2:
                    continue

                first = fields[0].strip()
                second = fields[1].strip()

                if first == "Cpus_allowed_list":
                    return unfold_cpu_list(second)

        return []
