import os
import struct
import re
import logging


def get_cpu_count():
    dirs = os.listdir("/sys/devices/system/cpu")
    return len([c for c in dirs if re.search(r"^cpu[0-9]+$", c)])


def read_msr(msr, cpu=0):
    try:
        with open("/dev/cpu/{}/msr".format(cpu), "rb") as f:
            f.seek(msr)
            raw = f.read(8)
            val = struct.unpack("BBBBBBBB", raw)
            return val
    except IOError as err:
        logging.error("Could not read MSR: {}".format(err))
        raise err


def get_cpu_base_frequency():
    b = read_msr(0xCE)  # MSR_PLATFORM_INFO
    # Byte 1 contains the max non-turbo frequecy
    base_freq = b[1] * 100
    return base_freq


def cpus():
    cpus = []
    try:
        p1 = get_cpu_base_frequency()
    except Exception as err:
        logging.error("Could not read base freq from MSR: {}".format(err))
        try:
            p1 = get_cpu_base_frequency_no_msr()
        except Exception as err:
            logging.error("Could not read base freq from sys fs: {}"
                          .format(err))
            return cpus

    for c in range(0, get_cpu_count()):
        try:
            base = read_cpu_base_freq(c)
            if base > p1:
                cpus.append(c)
        except IOError:
            logging.warning(
                "Could not read base frequency of CPU {}, skipping".format(c))
    return cpus


# reads base frequencies for each core and returns the lowest value
def get_cpu_base_frequency_no_msr():
    freqs = []

    for c in range(0, get_cpu_count()):
        try:
            freqs.append(read_cpu_base_freq(c))
        except IOError:
            logging.warning(
                "Could not read base frequency of CPU {}, skipping".format(c))
    return min(freqs)


def read_cpu_base_freq(cpu):
    base_freq = 0
    base_freq_template = "/sys/devices/system/cpu/cpu{}/cpufreq/base_frequency"
    base_file_path = base_freq_template.format(cpu)
    with open(base_file_path, "r") as f:
        # base_frequency reports cores frequency in kHz
        base_freq = int(f.readline().rstrip()) / 1000
    return base_freq
