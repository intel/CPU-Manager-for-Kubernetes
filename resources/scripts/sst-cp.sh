#!/bin/bash

declare -A EPP_VALUES=()

CPUS=$(ls /sys/bus/cpu/devices/)

# Check if the first CPU has file that holds epp value
output=$(cat /sys/bus/cpu/devices/cpu0/cpufreq/energy_performance_preference 2>&1)

if [[ $output ]]
then
        for FILE in $CPUS
        do
                VAR=$(cat /sys/bus/cpu/devices/"$FILE"/cpufreq/energy_performance_preference)
                EPP_VALUES[$VAR]=0
        done
fi

# If there is more than one epp value present, SST-CP is enabled
if [[ ${#EPP_VALUES[@]} -gt 1 ]]
then
        # Write into this file so the node is labeled correctly
        echo "power.sst_cp.enabled" > /etc/kubernetes/node-feature-discovery/features.d/cpu
else
        echo "" > /etc/kubernetes/node-feature-discovery/features.d/cpu
fi
