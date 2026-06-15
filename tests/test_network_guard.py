import asyncio
import os
import inspect
import threading
import unittest
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

from httpx_mcp import server as mcp_server


class _LocalHandler(BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        type(self).seen.append(self.path)
        body = b"local-only-service"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


class _LocalServer:
    def __enter__(self):
        _LocalHandler.seen = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _LocalHandler)
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    @property
    def url(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    @property
    def seen(self):
        return list(_LocalHandler.seen)


def _httpx_response(status_code, url, *, headers=None, text=""):
    response = httpx.Response(
        status_code,
        headers=headers,
        text=text,
        request=httpx.Request("GET", url),
    )
    response._elapsed = timedelta(seconds=0)
    return response


class NetworkGuardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._previous_allow = os.environ.pop("HTTPX_MCP_ALLOW_PRIVATE_NETWORK", None)

    async def asyncSetUp(self):
        asyncio.get_running_loop().set_debug(False)

    def tearDown(self):
        if self._previous_allow is None:
            os.environ.pop("HTTPX_MCP_ALLOW_PRIVATE_NETWORK", None)
        else:
            os.environ["HTTPX_MCP_ALLOW_PRIVATE_NETWORK"] = self._previous_allow

    async def test_http_request_blocks_loopback_by_default(self):
        with _LocalServer() as local:
            result = await mcp_server.call_tool(
                "http_request",
                {"method": "GET", "url": f"{local.url}/secret"},
            )

            self.assertIn("Blocked request", result[0].text)
            self.assertEqual([], local.seen)

    async def test_http_raw_blocks_loopback_by_default(self):
        with _LocalServer() as local:
            port = local.server.server_address[1]
            raw_request = f"GET /raw-secret HTTP/1.1\nHost: 127.0.0.1:{port}\n\n"

            result = await mcp_server.call_tool(
                "http_raw",
                {"raw_request": raw_request},
            )

            self.assertIn("Blocked request", result[0].text)
            self.assertEqual([], local.seen)

    async def test_http_request_allows_private_targets_when_operator_opts_in(self):
        os.environ["HTTPX_MCP_ALLOW_PRIVATE_NETWORK"] = "true"

        with _LocalServer() as local:
            result = await mcp_server.call_tool(
                "http_request",
                {"method": "GET", "url": f"{local.url}/allowed"},
            )

            self.assertIn("local-only-service", result[0].text)
            self.assertEqual(["/allowed"], local.seen)

    async def test_http_request_revalidates_redirect_targets(self):
        calls = []
        original_async_client = mcp_server.httpx.AsyncClient

        class RedirectingClient:
            def __init__(self, *args, **kwargs):
                self.follow_redirects = kwargs.get("follow_redirects", False)
                self.request_hooks = kwargs.get("event_hooks", {}).get("request", [])

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def request(self, method, url, **kwargs):
                url = str(url)
                for hook in self.request_hooks:
                    result = hook(httpx.Request(method, url))
                    if inspect.isawaitable(result):
                        await result
                calls.append(url)
                if url == "http://93.184.216.34/start":
                    if self.follow_redirects:
                        private_url = "http://127.0.0.1/private"
                        for hook in self.request_hooks:
                            result = hook(httpx.Request("GET", private_url))
                            if inspect.isawaitable(result):
                                await result
                        calls.append(private_url)
                        return _httpx_response(
                            200,
                            private_url,
                            text="private redirect target",
                        )
                    return _httpx_response(
                        302,
                        url,
                        headers={"Location": "http://127.0.0.1/private"},
                    )
                return _httpx_response(200, url, text="private redirect target")

        mcp_server.httpx.AsyncClient = RedirectingClient
        try:
            result = await mcp_server.call_tool(
                "http_request",
                {
                    "method": "GET",
                    "url": "http://93.184.216.34/start",
                    "follow_redirects": True,
                },
            )
        finally:
            mcp_server.httpx.AsyncClient = original_async_client

        self.assertIn("Blocked request", result[0].text)
        self.assertEqual(["http://93.184.216.34/start"], calls)
