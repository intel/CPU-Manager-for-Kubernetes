<!--
Copyright (c) 2017 Intel Corporation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# The `cmk` configuration directory

CMK checkpoints state in a [Kubernetes ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/). The checkpoint
describes all configured "pools" and their options, the "CPU lists" for
those pools, and the "tasks" currently assigned to each CPU list. The
directory format is described below.

## CMK configmap configuration format

_Example:_

```
data:
  config: |
    exclusive:
      0:
        4,12: []
        5,13: []
        6,14: []
        7,15: []
      1: {}
    infra:
      0:
        0-2,8-10:
        - '48624'
      1: {}
    shared:
      0:
        3,11: []
      1: {}
```

_Example with extra exclusive-non-isolcpus pool configured:_

```       
data:
  config: |
    exclusive:
      0:
        4,12: []
        5,13: []
      1: {}
    infra:
      0:
        0-2,8-10:
        - '48624'
      1: {}
    shared:
      0:
        3,11: []
      1: {}
    exclusive-non-isolcpus:
      0: 
        6,14: []
        7,15: []
```

_Where:_

| Path                                    | Meaning |
| :-------------------------------------- | :------ |
| `data -> config -> <pool>`                 | The name of the pool acting as a key, one per pool. |
| `data -> config -> <pool> -> <cpulist>`       | The name of the CPU list in the pool conforming to the Linux cpuset [CPU list format](cpu-list). |
| `data -> config -> <pool> -> <cpulist> -> <tasks>` | A comma-separated list of the root Linux process IDs of containers to which the CPUset has been allocated. |

## Creating a new configuration

CMK can set up its own initial state. See [`cmk init`][cmk-init] doc for more
information.

## Configuration changes over time

`cmk` updates the configuration as follows:

- The operator creates the initial configuration on each host, either manually
  or by using the [`cmk init`][cmk-init] helper program.
- When tasks are launched via [`cmk isolate`][cmk-isolate], an available
  CPU list for the requested pool is chosen. That CPU list's `tasks`
  list is updated to include the [`cmk isolate`][cmk-isolate] process ID.
- After a task launched via [`cmk isolate`][cmk-isolate] dies, the
  associated CPU list's `tasks` list is updated to remove the
  [`cmk isolate`][cmk-isolate] process ID.
- [`cmk reconcile`][cmk-reconcile] asks the operating system about all
  process IDs in all pools. Process IDs that are no longer valid are removed
  from the `tasks` list. [`cmk reconcile`][cmk-reconcile] should be configured to execute
  periodically on each host).

[cpu-list]: http://man7.org/linux/man-pages/man7/cpuset.7.html#FORMATS
[cmk-init]: cli.md#cmk-init
[cmk-isolate]: cli.md#cmk-isolate
[cmk-reconcile]: cli.md#cmk-reconcile
