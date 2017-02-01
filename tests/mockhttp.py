# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the "Software"), without modification,
# provided the following conditions are met:
#
# * Neither the name of Intel nor the names of its suppliers may be used to
#   endorse or promote products derived from this Software without specific
#   prior written permission.
# * No reverse engineering, decompilation, or disassembly of this Software
#   is permitted.
#
# Limited patent license.  Intel grants you a world-wide, royalty-free,
# non-exclusive license under patents it now or hereafter owns or controls to
# make, have made, use, import, offer to sell and sell ("Utilize") this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  "Third Party Programs" are the files
# listed in the "third-party-programs.txt" text file that is included with the
# Software and may include Intel programs under separate license terms. Third
# Party Programs, even if included with the distribution of the Materials, are
# governed by separate license terms and those license terms solely govern your
# use of those programs.
#
# DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
# DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS
# OR APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR
# DEATH.
#
# LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO
# INDEMNIFIY AND HOLD INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING
# FROM YOUR USE OR UNAUTHORIZED USE OF THE SOFTWARE.
#
# No support.  Intel may make changes to the Software, at any time without
# notice, and is not obligated to support, update or provide training for the
# Software.
#
# Termination. Intel may terminate your right to use the Software in the event
# of your breach of this Agreement and you fail to cure the breach within a
# reasonable period of time.
#
# Feedback.  Should you provide Intel with comments, modifications,
# corrections, enhancements or other input ("Feedback") related to the Software
# Intel will be free to use, disclose, reproduce, license or otherwise
# distribute or exploit the Feedback in its sole discretion without any
# obligations or restrictions of any kind, including without limitation,
# intellectual property rights or licensing obligations.
#
# Compliance with laws.  You agree to comply with all relevant laws and
# regulations governing your use, transfer, import or export (or prohibition
# thereof) of the Software.
#
# Governing law.  All disputes will be governed by the laws of the United
# States of America and the State of Delaware without reference to conflict of
# law principles and subject to the exclusive jurisdiction of the state or
# federal courts sitting in the State of Delaware, and each party agrees that
# it submits to the personal jurisdiction and venue of those courts and waives
# any objections. The United Nations Convention on Contracts for the
# International Sale of Goods (1980) is specifically excluded and will not
# apply to the Software.

from concurrent.futures import Future
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import socket
from threading import Thread


class Server(HTTPServer):
    def __init__(self):
        self.host = "localhost"
        self.port = next_free_port()
        self.url = "http://{}:{}".format(self.host, self.port)
        self.hook = error_hook
        # Invoke parent class (HTTPServer) constructor
        super().__init__((self.host, self.port), MockHTTPRequestHandler)

    def reset_hook(self):
        self.hook = error_hook

    def call_hook(self, method, handler):
        try:
            self.hook(method, handler)
        except BrokenPipeError as e:
            logging.info("Client disconnected early: ", e)

    def next_request(self):
        return RequestContext(self)

    # Front half of context guard
    def __enter__(self):
        logging.info("Starting mock HTTP server at {}".format(self.url))
        self.server_thread = Thread(target=self.serve_forever)
        # Prevent this thread from hanging the interpreter;
        # interpreter may exit when only daemon threads remain.
        self.server_thread.daemon = True
        self.server_thread.start()
        return self

    # Back half of context guard
    def __exit__(self, type, value, traceback):
        # By default, shuts down the server within 500ms.
        logging.info("Shutting down mock HTTP server")
        self.shutdown()
        logging.info("Waiting for mock HTTP server to shut down")
        self.server_thread.join()


class MockHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):  # noqa: N802
        logging.debug("Mock HTTP server: HEAD")
        self.server.call_hook("HEAD", self)

    def do_OPTIONS(self):  # noqa: N802
        logging.debug("Mock HTTP server: OPTIONS")
        self.server.call_hook("OPTIONS", self)

    def do_GET(self):  # noqa: N802
        logging.debug("Mock HTTP server: GET")
        self.server.call_hook("GET", self)

    def do_POST(self):  # noqa: N802
        logging.debug("Mock HTTP server: POST")
        self.server.call_hook("POST", self)

    def do_PUT(self):  # noqa: N802
        logging.debug("Mock HTTP server: PUT")
        self.server.call_hook("PUT", self)

    def do_PATCH(self):  # noqa: N802
        logging.debug("Mock HTTP server: PATCH")
        self.server.call_hook("PATCH", self)

    def do_DELETE(self):  # noqa: N802
        logging.debug("Mock HTTP server: DELETE")
        self.server.call_hook("DELETE", self)

    def do_TRACE(self):  # noqa: N802
        logging.debug("Mock HTTP server: TRACE")
        self.server.call_hook("TRACE", self)


class RequestContext:
    def __init__(self, server):
        self.server = server
        self.future_request = Future()
        self.future_context_exit = Future()

    # Front half of context guard
    def __enter__(self):
        self.future_request.set_running_or_notify_cancel()
        self.future_context_exit.set_running_or_notify_cancel()

        # A hook that completes this request context's future and waits
        # for the context to end before returning.
        def context_hook(m, h):
            # Complete the request future, unblocking any waiters on
            # `.result()`.
            self.future_request.set_result((m, h))
            # Block "forever" on scope exit to avoid releasing resources
            # (file descriptors, sockets) prematurely.
            self.future_context_exit.result()

        self.server.hook = context_hook

        return self.future_request

    # Back half of context guard
    def __exit__(self, type, value, traceback):
        # Unblock the context hook function to allow the do_XXX function in
        # the handler to return.
        self.future_context_exit.set_result(None)
        # Clean up the hook in the server.
        self.server.reset_hook()


def error_hook(method, handler):
    logging.error("No mock HTTP hook installed for request")
    logging.error("METHOD: {}".format(method))
    logging.error("HEADERS:\n{}".format(handler.headers))
    logging.error("BODY:\n{}".format(handler.rfile.read()))
    handler.send_response(500)
    handler.end_headers()
    raise RuntimeError("No mock HTTP hook installed for request")


def next_free_port():
    # NOTE: Since we later attempt to bind to this socket, there is a
    # potential for errors in case the OS enforces a reuse timeout, etc.
    # Since this is only executed in the context of the tests, let's just
    # monitor it and see if it causes a problem. Anecdotally, have not seen
    # any errors from this in any environment yet.
    with socket.socket(socket.AF_INET, type=socket.SOCK_STREAM) as inet_sock:
        inet_sock.bind(("localhost", 0))
        _, port = inet_sock.getsockname()
    return port
