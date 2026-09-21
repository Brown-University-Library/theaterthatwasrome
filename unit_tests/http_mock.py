from contextlib import ContextDecorator
from unittest.mock import patch
from urllib.parse import parse_qsl

import httpx2
from typing_extensions import Self

GET = 'GET'
POST = 'POST'
PUT = 'PUT'


class BdrMock(ContextDecorator):
    """
    Supplies HTTPX2 responses without permitting any real network requests.
    """

    def __init__(self) -> None:
        """
        Creates a transport with an explicit response registry.
        Called by: module initialization, outage tests
        """
        self.routes: list[tuple[str, httpx2.URL, str | bytes | Exception, int, str, bool]] = []
        self.calls: list[httpx2.Request] = []
        self.transport = httpx2.MockTransport(self.handle_request)
        self.patcher = patch('httpx2.HTTPTransport.handle_request', side_effect=self.transport.handle_request)

    def __enter__(self) -> Self:
        """
        Starts intercepting HTTPX2 calls for one test.
        Called by: contextlib.ContextDecorator.__call__(), outage tests
        """
        self.reset()
        self.patcher.start()
        return self

    def __exit__(self, *exc) -> None:
        """
        Restores the transport after a test.
        Called by: contextlib.ContextDecorator.__call__(), outage tests
        """
        self.patcher.stop()

    def reset(self) -> None:
        """
        Clears registered responses and call history between scenarios.
        Called by: __enter__(), HTTP tests
        """
        self.routes.clear()
        self.calls.clear()

    def add(
        self,
        method: str,
        url: str,
        *,
        body: str | bytes | Exception = '',
        status: int = 200,
        content_type: str = 'text/plain',
        match_querystring: bool = False,
    ) -> None:
        """
        Registers a response, optionally matching all query parameters.
        Called by: HTTP tests
        """
        self.routes.append((method, httpx2.URL(url), body, status, content_type, match_querystring))

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        """
        Returns a registered response and rejects unexpected requests.
        Called by: httpx2.MockTransport.handle_request()
        """
        self.calls.append(request)
        response = None
        for method, url, body, status, content_type, match_query in self.routes:
            same_url = request.url.copy_with(query=None) == url.copy_with(query=None)
            same_query = sorted(parse_qsl(request.url.query.decode())) == sorted(parse_qsl(url.query.decode()))
            if method == request.method and same_url and (not match_query or same_query):
                if isinstance(body, Exception):
                    raise body
                response = httpx2.Response(status, content=body, headers={'Content-Type': content_type}, request=request)
                break
        if response is None:
            raise AssertionError(f'Unexpected HTTP request: {request.method} {request.url}')
        return response


activate = BdrMock()
add = activate.add
reset = activate.reset
