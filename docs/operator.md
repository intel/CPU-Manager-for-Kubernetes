# `kcm` operator manual

_Related:_

- [Using the kcm command-line tool][doc-cli]

## System requirements
Kubernetes >= v1.5.0

## Setting up the cluster

This section describes the setup required to use the `KCM` software. The steps described below should be followed in the 
same order. 

Notes: 
- The operator can choose any number of nodes in the kubernetes cluster to work with `KCM`. These participating 
nodes will be referred as `KCM` nodes.
- The documentation in this section assumes that the `KCM` configuration directory is `/etc/kcm` and the `KCM`
binary is installed on the host file system at `/opt/bin/kcm`. 

### Run `kcm init`
The `KCM` nodes in the kubernetes cluster should be initialized in order to be used with the KCM software using 
[`kcm-init`][kcm-init]. To initialize the `KCM` nodes, the `kcm init` [Pod template][init-template] can be used. 

In the [Pod template][init-template], `KCM` configuration directory in the host file system can be configured by changing the 
[value of the hostPath][hostpath-init-template]. 

**TODO:** Add script to run kcm-discover-Pod on `KCM` nodes.

### Advertising `KCM` Opaque Integer Resource (OIR) slots
All the `KCM` nodes in the Kubernetes cluster should be patched with `KCM` [OIR][oir-docs] slots using 
[`kcm discover`][kcm-discover]. The OIR slots are advertised as the dataplane pools need to be allocated exclusively.
The number of slots advertised should be equal to the number of cpu lists under the __dataplane__ pool, as determined by 
examining the `KCM` configuration directory. 

The `kcm discover` [Pod template][discover-template] can be used to advertise the `KCM` OIR slots. In the 
[Pod template][discover-template], `KCM` configuration directory in the host file system can be configured by 
changing the [value of the hostPath][hostpath-discover-template]. After running this Pod in a node, the node will be patched 
with `pod.alpha.kubernetes.io/opaque-int-resource-kcm' OIR. 

**TODO:** Add script to run kcm-discover-Pod on `KCM` nodes.

### Run `kcm reconcile`
In order to reconcile from an outdated `KCM` configuration state, each `KCM` node should run 
[`kcm reconcile`][kcm-reconcile] periodically. `kcm reconcile` can be run periodically using the 
[DaemonSet template][reconcile-template].

In the [DaemonSet template][discover-template], the time between each invocation of `kcm reconcile` can be adjusted 
by changing the [value of the KCM_RECONCILE_SLEEP_TIME][sleeptime-reconcile-template] environment variable. The 
value specifies time in seconds. `KCM` configuration directory in the host file system can be configured by changing the 
[value of the hostPath][hostpath-reconcile-template]. 


## Validating the environment
**TODO:** describe how to run e2e / smoke tests against an existing cluster.

## Troubleshooting and recovery
**TODO**

[doc-cli]: cli.md
[kcm-init]: cli.md#kcm-init
[kcm-discover]: cli.md#kcm-discover
[kcm-reconcile]: cli.md#kcm-reconcile
[init-template]: templates/kcm-init-pod.json.template
[discover-template]: templates/kcm-discover-pod.json.template
[reconcile-template]: templates/kcm-reconcile-daemonset.json.templates
[oir-docs]: http://kubernetes.io/docs/user-guide/compute-resources#opaque-integer-resources-alpha-feature
[hostpath-init-template]: 
[hostpath-discover-template]: templates/kcm-discover-pod.json.template#L44 
[hostpath-reconcile-template]: templates/kcm-reconcile-daemonset.json.template#L61
[sleeptime-reconcile-template]: templates/kcm-reconcile-daemonset.json.template#L30
