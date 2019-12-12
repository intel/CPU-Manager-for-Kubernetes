CPU_EPP_PATH = "/sys/devices/system/cpu/cpu{}/cpufreq\
/energy_performance_preference"

NFD_LABEL = "feature.node.kubernetes.io/cpu-power.sst_cp.enabled"


def get_epp_order(platform):
    epp_order = ["performance", "balance_performance",
                 "balance_power", "power"]
    epp_values_present = []
    current_epp_conf = []

    for c in platform.get_cores():
        with open(CPU_EPP_PATH.format(c.core_id)) as f:
            core_epp_value = f.read().split("\n")[0]
            if core_epp_value not in epp_values_present:
                epp_values_present.append(core_epp_value)

    for epp_value in epp_order:
        if epp_value in epp_values_present:
            current_epp_conf.append(epp_value)

    return current_epp_conf


def get_epp_cores(platform, epp_value, num_required, unavailable_cores):
    cores = []
    unavailable_core_ids = [c.core_id for c in unavailable_cores]
    for socket in platform.sockets.values():
        for core_id in socket.cores.keys():
            if core_id not in unavailable_core_ids:
                with open(CPU_EPP_PATH.format(core_id)) as f:
                    if f.read().split("\n")[0] == epp_value:
                        cores.append(socket.cores[core_id])
                        if len(cores) == num_required:
                            return cores


def get_epp_cores_no_limit(platform, epp_value):
    cores = []
    for socket in platform.sockets.values():
        for core_id in socket.cores.keys():
            with open(CPU_EPP_PATH.format(core_id)) as f:
                if f.read().split("\n")[0] == epp_value:
                    cores.append(socket.cores[core_id])

    return cores
