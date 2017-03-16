<!--
Intel License for KCM (version January 2017)

Copyright (c) 2017 Intel Corporation.

Use.  You may use the software (the "Software"), without modification, provided
the following conditions are met:

* Neither the name of Intel nor the names of its suppliers may be used to
  endorse or promote products derived from this Software without specific
  prior written permission.
* No reverse engineering, decompilation, or disassembly of this Software
  is permitted.

Limited patent license.  Intel grants you a world-wide, royalty-free,
non-exclusive license under patents it now or hereafter owns or controls to
make, have made, use, import, offer to sell and sell ("Utilize") this Software,
but solely to the extent that any such patent is necessary to Utilize the
Software alone. The patent license shall not apply to any combinations which
include this software.  No hardware per se is licensed hereunder.

Third party and other Intel programs.  "Third Party Programs" are the files
listed in the "third-party-programs.txt" text file that is included with the
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
enhancements or other input ("Feedback") related to the Software Intel will be
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

# Known issues

## Potential race between Kubernetes scheduler and pool state.

If a `kcm isolate` process terminates abnormally in a way that prevents
releasing the assigned CPU list (e.g. because it was sent the KILL
signal), then there is an interval of time between process termination
and when `kcm reconcile` is able to remove the invalid process ID from
the KCM configuration directory. During this interval, although the opaque
integer resource becomes available, the next invocation of `kcm isolate` may
not be able to safely make an allocation. In this case, `kcm isolate` should
be expected to crash with a nonzero exit status. This appears to the operator
as a filed pod launch. The scheduler will try to reschedule the pod.
This condition will persist on the affected node until `kcm reconcile` has a
chance to run, at which point it will detect that the saved process ID from
the reaped container is no longer valid and free the cores for reuse.

## Potential conflict with process ID reuse by the OS kernel.

If a `kcm isolate` process terminates abnormally in a way that prevents
releasing the assigned CPU list (e.g. because it was sent the KILL
signal), then there is an interval of time between process termination
and when `kcm reconcile` is able to remove the invalid process ID from
the KCM configuration directory. During this interval, if another
process is started and the kernel happens to recycle the old PID, then
`kcm reconcile` will not be able to detect the leaked CPU list.
This scenario should be very rare in practice.

## `kcm init` flag values for `--num-cp-cores` and `--num-dp-cores` must be positive integers

This places constratints on the construction of the user container
command value. Zero is also unsupported.

## The flag value for `--interval` (used in `kcm reconcile` and `kcm node-report`) must be an integer.

Fractional seconds are unsupported.
