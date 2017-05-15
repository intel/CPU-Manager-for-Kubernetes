# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
