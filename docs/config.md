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

CMK checkpoints state in a directory structure on disk. The checkpoint
describes all configured "pools" and their options, the "CPU lists" for
those pools, and the "tasks" currently assigned to each CPU list. The
directory format is described below.

## CMK filesystem configuration format

_Example:_

```
etc
└── cmk
    ├── lock
    └── pools
        ├── controlplane
        │   ├── 3,11
        │   │   └── tasks
        │   └── exclusive
        ├── dataplane
        │   ├── 4,12
        │   │   └── tasks
        │   ├── 5,13
        │   │   └── tasks
        │   ├── 6,14
        │   │   └── tasks
        │   ├── 7,15
        │   │   └── tasks
        │   └── exclusive
        └── infra
            ├── 0-2,8-10
            │   └── tasks
            └── exclusive
```

_Where:_

| Path                                    | Meaning |
| :-------------------------------------- | :------ |
| `/etc/cmk/lock`                         | A lock file to protect against conflicting concurrent modification. |
| `/etc/cmk/pools/<pool>`                 | Directories, one per pool. |
| `/etc/cmk/pools/<pool>/exclusive`       | Determines whether each CPU list in the pool can be shared (value 0) or not (value 1). Shared CPU lists can accomodate multiple tasks simultaneously, while exclusive CPU lists may only be allocated to one task at a time. |
| `/etc/cmk/pools/<pool>/<cpulist>`       | Directories whose names conform to the Linux cpuset [CPU list format](cpu-list). |
| `/etc/cmk/pools/<pool>/<cpulist>/tasks` | A file containing a comma-separated list of the root Linux process IDs of containers to which the CPUset has been allocated. |

## Creating a new configuration

CMK can set up its own initial state. See [`cmk init`][cmk-init] doc for more
information.

## Configuration changes over time

`cmk` updates the configuration as follows:

- The operator creates the initial configuration on each host, either manually
  or by using the [`cmk init`][cmk-init] helper program.
- When tasks are launched via [`cmk isolate`][cmk-isolate], an available
  CPU list for the requested pool is chosen. That CPU list's `tasks`
  file is updated to include the [`cmk isolate`][cmk-isolate] process ID.
- After a task launched via [`cmk isolate`][cmk-isolate] dies, the
  associated CPU list's `tasks` file is updated to remove the
  [`cmk isolate`][cmk-isolate] process ID.
- [`cmk reconcile`][cmk-reconcile] asks the operating system about all
  process IDs in all pools. Process IDs that are no longer valid are removed
  from the `tasks` file. [`cmk reconcile`][cmk-reconcile] should be configured to execute
  periodically on each host).

[cpu-list]: http://man7.org/linux/man-pages/man7/cpuset.7.html#FORMATS
[cmk-init]: cli.md#cmk-init
[cmk-isolate]: cli.md#cmk-isolate
[cmk-reconcile]: cli.md#cmk-reconcile
