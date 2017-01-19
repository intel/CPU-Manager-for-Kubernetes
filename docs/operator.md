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

# `kcm` operator manual

_Related:_

- [Using the kcm command-line tool][doc-cli]

## System requirements
Kubernetes >= v1.5.0

## Setting up the cluster

This section describes the setup required to use the `KCM` software. The recommended way to prepare Kubernetes nodes 
for the `KCM` software is to run `kcm cluster-init` as a Pod as described in these [instructions][cluster-init-op-manual]. 

## Concepts

| Term           | Meaning |
| :------------- | :------ |
| `KCM` nodes    | The operator can choose any number of nodes in the kubernetes cluster to work with `KCM`. These participating nodes will be referred as `KCM` nodes. |
| Pod            | A Pod is an abstraction in Kubernetes to represent one or more containers and their configuration. It is the smallest schedulable unit in Kubernetes. |
| OIR            | Acronym for [Opaque Integer Resource][oir-docs]. In Kubernetes, OIR allow cluster operators to advertise new node-level resources that would be otherwise unknown to the system. | 
| Volume         | A volume is a directory (on host file system). In Kubernetes, a volume has the same lifetime as the Pod that uses it. Many types of volumes are supported in Kubernetes. | 
| `hostPath`       | `hostPath` is a volume type in Kubernetes. It mounts a file or directory from the host file system into the Pod. | 

### Prepare `KCM` nodes by running `kcm cluster-init`. 
`KCM` nodes can be prepared by using [`kcm cluster-init`][kcm-cluster-init] subcommand. The subcommand is expected to 
be run as a pod. The [kcm-cluster-init-pod template][cluster-init-template] can be used to run `kcm cluster-init` on a 
Kubernetes cluster. When run on a Kubernetes cluster, the Pod spawns two Pods per node at most in order to prepare 
each node.

The only value that requires change in the [kcm-cluster-init-pod template][kcm-cluster-init] is the `args` field, 
which can be modified to pass different options. 

Following are some example modifications to the `args` field: 
```yml
  - args:
      # Change this value to pass different options to cluster-init. 
      - "/kcm/kcm.py cluster-init --host-list=node1,node2,node3"
```
The above command prepares nodes "node1", "node2" and "node3" for the `KCM` software using default options. 

```yml
  - args:
      # Change this value to pass different options to cluster-init. 
      - "/kcm/kcm.py cluster-init --all-hosts"
```
The above command prepares all the nodes in the Kubernetes cluster for the `KCM` software using default options. 

```yml
  - args:
      # Change this value to pass different options to cluster-init. 
      - "/kcm/kcm.py cluster-init --host-list=node1,node2,node3 --kcm-cmd-list=init,discover"
```
The above command prepares nodes "node1", "node2" and "node3" but only runs the `kcm init` and `kcm discover` 
subcommands on each of those nodes. 

For more details on the options provided by `kcm cluster-init`, see this [description][kcm-cluster-init].

### Prepare `KCM` nodes by running each `KCM` subcommand as a Pod. 

Notes:
- The subcommands described below should be run in the same order. 
- The documentation in this section assumes that the `KCM` configuration directory is `/etc/kcm` and the `kcm`
binary is installed on the host under `/opt/bin`.
- In all the pod templates used in this section, the name of container image used is `kcm:v0.1.0`. It is expected that the 
`kcm` container image is built and cached locally in the host. The `image` field will require modification if the 
container image is hosted remotely (e.g., in https://hub.docker.com/).

#### Run `kcm init`
The `KCM` nodes in the kubernetes cluster should be initialized in order to be used with the KCM software using 
[`kcm-init`][kcm-init]. To initialize the `KCM` nodes, the [kcm-init-pod template][init-template] can be used. 

`kcm init` takes the `--conf-dir`, `--num-dp-cores` and the `--num-cp-cores` flags. In the 
[kcm-init-pod template][init-template], the values to these flags can be modified. The value for `--conf-dir` can be 
set by changing the `path` value of the `hostPath` for the `kcm-conf-dir`. The value for `--num-dp-cores` and 
`--num-cp-cores` can be set by changing the values for the `NUM_DP_CORES` and `NUM_CP_CORES` environment variables, 
respectively. 

Values that might require modification in the [kcm-init-pod template][init-template] are shown as snippets below:

```yml
  volumes:
  - hostPath:
      # Change this to modify the KCM config dir in the host file system.
      path: "/etc/kcm"
    name: kcm-conf-dir
```

```yml
    env:
    - name: NUM_DP_CORES
      # Change this to modify the value passed to `--num-dp-cores` flag.
      value: '4'
    - name: NUM_CP_CORES
      # Change this to modify the value passed to `--num-cp-cores` flag.
      value: '1'
```

#### Advertising `KCM` Opaque Integer Resource (OIR) slots
All the `KCM` nodes in the Kubernetes cluster should be patched with `KCM` [OIR][oir-docs] slots using 
[`kcm discover`][kcm-discover]. The OIR slots are advertised as the dataplane pools need to be allocated exclusively.
The number of slots advertised should be equal to the number of cpu lists under the __dataplane__ pool, as determined 
by examining the `KCM` configuration directory. [kcm-discover-pod template][discover-template] can be used to 
advertise the `KCM` OIR slots.

`kcm discover` takes the `--conf-dir` flag. In the [kcm-discover-pod template][discover-template], the value for 
`--conf-dir` can be configured by changing the `path` value of the `hostPath` for `kcm-conf-dir`. After running 
this Pod in a node, the node will be patched with `pod.alpha.kubernetes.io/opaque-int-resource-kcm' OIR. 

Values that might require modification in the [kcm-discover-pod template][discover-template] are shown as snippets 
below:

```yml
  volumes:
  - hostPath:
      # Change this to modify the KCM config dir in the host file system.
      path: "/etc/kcm"
    name: kcm-conf-dir
```

#### Run `kcm reconcile`
In order to reconcile from an outdated `KCM` configuration state, each `KCM` node should run 
[`kcm reconcile`][kcm-reconcile] periodically. `kcm reconcile` can be run periodically using the 
[kcm-reconcile-daemonset template][reconcile-template].

In the [kcm-reconcile-daemonset template][reconcile-template], the time between each invocation of `kcm reconcile` 
can be adjusted by changing the value of the KCM_RECONCILE_SLEEP_TIME environment variable. The value specifies time 
in seconds. `kcm reconcile` takes the `--conf-dir` flag. This value can be configured by changing the `path` 
value of the `hostPath` for the `kcm-conf-dir` in the [kcm-reconcile-daemonset][reconcile-template] template. 

Values that might require modification in the [kcm-reconcile-daemonset template][reconcile-template] are shown as 
snippets below:

```yml
    env:
    - name: KCM_RECONCILE_SLEEP_TIME
        # Change this to modify the sleep interval between consecutive 
        # kcm reconcile runs. The value is specified in seconds.  
        value: '60'
```

```yml
  volumes:
  - hostPath:
      # Change this to modify the KCM config dir in the host file system.
      path: "/etc/kcm"
    name: kcm-conf-dir
```

#### Run `kcm install`
[`kcm install`][kcm-install] is used to create a zero-dependency binary of the `KCM` software and place it on the host 
filesystem. Subsequent containers can isolate themselves by mounting the install directory from the host and then 
calling `kcm isolate`. To run it on all the `KCM` nodes, the [kcm-install-pod template][install-template] 
can be used. 

`kcm install` takes the `--install-dir` flag. In the [kcm-install-pod template][install-template], the value for 
`--install-dir` can be configured by changing the `path` value of the `hostPath` for the `kcm-install-dir`.

Values that might require modification in the [kcm-install-pod template][install-template] are shown as snippets 
below:

```yml
  volumes:
  - hostPath:
      # Change this to modify the KCM installation dir in the host file system.
      path: "/opt/bin"
    name: kcm-install-dir
```

## Running the `kcm isolate` Hello World Pod
After following the instructions in the previous section, the cluster is ready to run the `Hello World` Pod. The Hello 
World [kcm-isolate-pod template][isolate-template] describes a simple Pod with three containers requesting CPUs from 
the __dataplane__, __controlplane__ and the __infra__ pools, respectively, using [`kcm isolate`][kcm-isolate]. The 
`pool` is requested by passing the desired value to the `--pool` flag when using `kcm isolate` as described in the 
[documentation][kcm-isolate].

`kcm isolate` takes the `--conf-dir` and `--install-dir` flags. In the [kcm-isolate-pod template][isolate-template], 
the values for `--conf-dir` and `--install-dir` can be modified by changing the `path` values of the `hostPath`. 

Values that might require modification in the [kcm-isolate-pod template][isolate-template] are shown as snippets 
below:
 
```yml
  volumes:
  - hostPath:
      # Change this to modify the KCM installation dir in the host file system.
      path: "/opt/bin"
    name: kcm-install-dir
  - hostPath:
      # Change this to modify the KCM config dir in the host file system.
      path: "/etc/kcm"
    name: kcm-conf-dir
```

Notes: 
- The Hello World kcm-isolate-pod consumes the `pod.alpha.kubernetes.io/opaque-int-resource-kcm` Opaque Integer 
Resource (OIR) only in the container isolated using the __dataplane__ pool. The `KCM` software assumes that only 
container isolated using the __dataplane__ pool requests the OIR and each of these containers should consume exactly 
one OIR. This restricts the number of pods that can land on a Kubernetes node to the expected value. 
- The `kcm isolate` Hello World Pod should only be run after following the instructions provided in the 
[`Setting up the cluster`][cluster-setup] section. 

## Validating the environment
**TODO:** describe how to run e2e / smoke tests against an existing cluster.

## Troubleshooting and recovery
**TODO**

[cluster-setup]: #setting-up-the-cluster
[doc-cli]: cli.md
[kcm-init]: cli.md#kcm-init
[kcm-discover]: cli.md#kcm-discover
[kcm-reconcile]: cli.md#kcm-reconcile
[kcm-install]: cli.md#kcm-install
[kcm-isolate]: cli.md#kcm-isolate
[kcm-cluster-init]: cli.md#kcm-cluster-init
[init-template]: ../resources/pods/kcm-init-pod.yaml
[discover-template]: ../resources/pods/kcm-discover-pod.yaml
[reconcile-template]: ../resources/pods/kcm-reconcile-daemonset.yaml
[install-template]: ../resources/pods/kcm-install-pod.yaml
[isolate-template]: ../resources/pods/kcm-isolate-pod.yaml
[cluster-init-template]: ../resources/pods/kcm-cluster-init-pod.yaml
[oir-docs]: http://kubernetes.io/docs/user-guide/compute-resources#opaque-integer-resources-alpha-feature
[cluster-init-op-manual]: #prepare-kcm-nodes-by-running-kcm-cluster-init
