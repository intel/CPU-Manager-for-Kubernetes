<!--
Intel License for KCM (version January 2017)

Copyright (c) 2017 Intel Corporation.

Use.  You may use the software (the “Software”), without modification, provided
the following conditions are met:

* Neither the name of Intel nor the names of its suppliers may be used to
  endorse or promote products derived from this Software without specific
  prior written permission.
* No reverse engineering, decompilation, or disassembly of this Software
  is permitted.

Limited patent license.  Intel grants you a world-wide, royalty-free,
non-exclusive license under patents it now or hereafter owns or controls to
make, have made, use, import, offer to sell and sell (“Utilize”) this Software,
but solely to the extent that any such patent is necessary to Utilize the
Software alone. The patent license shall not apply to any combinations which
include this software.  No hardware per se is licensed hereunder.

Third party and other Intel programs.  “Third Party Programs” are the files
listed in the “third-party-programs.txt” text file that is included with the
Software and may include Intel programs under separate license terms. Third
Party Programs, even if included with the distribution of the Materials, are
governed by separate license terms and those license terms solely govern your
use of those programs.

DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS OR
APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR DEATH.

LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO INDEMNIFIY AND HOLD
INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING FROM YOUR USE OR
UNAUTHORIZED USE OF THE SOFTWARE.

No support.  Intel may make changes to the Software, at any time without
notice, and is not obligated to support, update or provide training for the
Software.

Termination. Intel may terminate your right to use the Software in the event of
your breach of this Agreement and you fail to cure the breach within a
reasonable period of time.

Feedback.  Should you provide Intel with comments, modifications, corrections,
enhancements or other input (“Feedback”) related to the Software Intel will be
free to use, disclose, reproduce, license or otherwise distribute or exploit
the Feedback in its sole discretion without any obligations or restrictions of
any kind, including without limitation, intellectual property rights or
licensing obligations.

Compliance with laws.  You agree to comply with all relevant laws and
regulations governing your use, transfer, import or export (or prohibition
thereof) of the Software.

Governing law.  All disputes will be governed by the laws of the United States
of America and the State of Delaware without reference to conflict of law
principles and subject to the exclusive jurisdiction of the state or federal
courts sitting in the State of Delaware, and each party agrees that it submits
to the personal jurisdiction and venue of those courts and waives any
objections. The United Nations Convention on Contracts for the International
Sale of Goods (1980) is specifically excluded and will not apply to the
Software.
-->

# The `kcm` configuration directory

KCM checkpoints state in a directory structure on disk. The checkpoint
describes all configured "pools" and their options, the "CPU lists" for
those pools, and the "tasks" currently assigned to each CPU list. The
directory format is described below.

## KCM filesystem configuration format

_Example:_

```
etc
└── kcm
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
| `/etc/kcm/lock`                         | A lock file to protect against conflicting concurrent modification. |
| `/etc/kcm/pools/<pool>`                 | Directories, one per pool. |
| `/etc/kcm/pools/<pool>/exclusive`       | Determines whether each CPU list in the pool can be shared (value 0) or not (value 1). Shared CPU lists can accomodate multiple tasks simultaneously, while exclusive CPU lists may only be allocated to one task at a time. |
| `/etc/kcm/pools/<pool>/<cpulist>`       | Directories whose names conform to the Linux cpuset [CPU list format](cpu-list). |
| `/etc/kcm/pools/<pool>/<cpulist>/tasks` | A file containing a comma-separated list of the root Linux process IDs of containers to which the CPUset has been allocated. |

## Creating a new configuration

KCM can set up its own initial state. See [`kcm init`][kcm-init] doc for more
information.

## Configuration changes over time

`kcm` updates the configuration as follows:

- The operator creates the initial configuration on each host, either manually
  or by using the [`kcm init`][kcm-init] helper program.
- When tasks are launched via [`kcm isolate`][kcm-isolate], an available
  CPU list for the requested pool is chosen. That CPU list's `tasks`
  file is updated to include the [`kcm isolate`][kcm-isolate] process ID.
- After a task launched via [`kcm isolate`][kcm-isolate] dies, the
  associated CPU list's `tasks` file is updated to remove the
  [`kcm isolate`][kcm-isolate] process ID.
- [`kcm reconcile`][kcm-reconcile] asks the operating system about all
  process IDs in all pools. Process IDs that are no longer valid are removed
  from the `tasks` file. [`kcm reconcile`][kcm-reconcile] should be configured to execute
  periodically on each host).

[cpu-list]: http://man7.org/linux/man-pages/man7/cpuset.7.html#FORMATS
[kcm-init]: cli.md#kcm-init
[kcm-isolate]: cli.md#kcm-isolate
[kcm-reconcile]: cli.md#kcm-reconcile
