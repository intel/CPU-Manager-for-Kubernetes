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

# Known issues

## Potential race between Kubernetes scheduler and pool state.

If a `cmk isolate` process terminates abnormally in a way that prevents
releasing the assigned CPU list (e.g. because it was sent the KILL
signal), then there is an interval of time between process termination
and when `cmk reconcile` is able to remove the invalid process ID from
the CMK configuration directory. During this interval, although the opaque
integer resource becomes available, the next invocation of `cmk isolate` may
not be able to safely make an allocation. In this case, `cmk isolate` should
be expected to crash with a nonzero exit status. This appears to the operator
as a filed pod launch. The scheduler will try to reschedule the pod.
This condition will persist on the affected node until `cmk reconcile` has a
chance to run, at which point it will detect that the saved process ID from
the reaped container is no longer valid and free the cores for reuse.

## Potential conflict with process ID reuse by the OS kernel.

If a `cmk isolate` process terminates abnormally in a way that prevents
releasing the assigned CPU list (e.g. because it was sent the KILL
signal), then there is an interval of time between process termination
and when `cmk reconcile` is able to remove the invalid process ID from
the CMK configuration directory. During this interval, if another
process is started and the kernel happens to recycle the old PID, then
`cmk reconcile` will not be able to detect the leaked CPU list.
This scenario should be very rare in practice.

## `cmk init` flag values for `--num-cp-cores` and `--num-dp-cores` must be positive integers

This places constratints on the construction of the user container
command value. Zero is also unsupported.

## The flag value for `--interval` (used in `cmk reconcile` and `cmk node-report`) must be an integer.

Fractional seconds are unsupported.
