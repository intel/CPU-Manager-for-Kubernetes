from .. import helpers, mockhttp
import requests


def test_mockhttp_server():
    def http_client():
        assert 200 is requests.get(server.url).status_code

    with mockhttp.Server() as server:
        with server.next_request() as f:
            with helpers.background(http_client) as thread:
                # Wait up to 5 seconds for a result
                (method, handler) = f.result(5)
                assert method is "GET"
                handler.send_response(200, "OK")
                handler.end_headers()
        thread.join()
