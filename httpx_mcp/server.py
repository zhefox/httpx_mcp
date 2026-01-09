"""
HTTPX MCP Server - HTTP Request Testing Tool

Provides the following MCP tools:
- http_request: Send HTTP requests (GET, POST, PUT, DELETE, PATCH, etc.)
- http_raw: Parse raw HTTP requests (supports Burp Suite capture format)
"""

import json
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create MCP server
server = Server("httpx-mcp")


def format_response(response: httpx.Response, include_headers: bool = True) -> str:
    """Format HTTP response into a readable string"""
    result_parts = []
    
    # Status line
    result_parts.append(f"HTTP/{response.http_version} {response.status_code} {response.reason_phrase}")
    result_parts.append("")
    
    # Response headers
    if include_headers:
        result_parts.append("=== Response Headers ===")
        for name, value in response.headers.items():
            result_parts.append(f"{name}: {value}")
        result_parts.append("")
    
    # Response body
    result_parts.append("=== Response Body ===")
    
    content_type = response.headers.get("content-type", "")
    body = response.text
    
    # Try to format JSON
    if "application/json" in content_type:
        try:
            parsed = json.loads(body)
            body = json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    
    result_parts.append(body)
    
    # Add response time
    result_parts.append("")
    result_parts.append(f"=== Request Info ===")
    result_parts.append(f"Time: {response.elapsed.total_seconds():.3f}s")
    result_parts.append(f"Size: {len(response.content)} bytes")
    
    return "\n".join(result_parts)


def parse_headers(headers_input: str | dict | list | None) -> dict:
    """Parse request headers, supports multiple formats"""
    if headers_input is None:
        return {}
    
    if isinstance(headers_input, dict):
        return headers_input
    
    if isinstance(headers_input, list):
        result = {}
        for item in headers_input:
            if isinstance(item, str) and ":" in item:
                key, value = item.split(":", 1)
                result[key.strip()] = value.strip()
            elif isinstance(item, dict):
                result.update(item)
        return result
    
    if isinstance(headers_input, str):
        # Try to parse as JSON
        try:
            parsed = json.loads(headers_input)
            if isinstance(parsed, dict):
                return parsed
            elif isinstance(parsed, list):
                return parse_headers(parsed)
        except json.JSONDecodeError:
            pass
        
        # Parse line by line "Key: Value" format
        result = {}
        for line in headers_input.strip().split("\n"):
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        return result
    
    return {}


def parse_params(params_input: str | dict | None) -> dict | None:
    """Parse URL query parameters"""
    if params_input is None:
        return None
    
    if isinstance(params_input, dict):
        return params_input
    
    if isinstance(params_input, str):
        try:
            return json.loads(params_input)
        except json.JSONDecodeError:
            # Parse key=value&key2=value2 format
            result = {}
            for pair in params_input.split("&"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    result[key.strip()] = value.strip()
            return result if result else None
    
    return None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools"""
    return [
        Tool(
            name="http_request",
            description="""Send HTTP request to specified URL. Supports all HTTP methods (GET/POST/PUT/DELETE/PATCH, etc.).

Usage examples:
- GET request: method="GET", url="https://api.example.com/users"
- GET with params: method="GET", url="...", params='{"page":"1","size":"10"}'
- POST JSON: method="POST", url="...", body='{"key":"value"}'
- PUT update: method="PUT", url="...", body='{"id":1,"name":"test"}'
- DELETE: method="DELETE", url="https://api.example.com/users/1"
- Custom headers: headers='{"Authorization":"Bearer xxx"}'
- Form submit: body="name=test&age=18", content_type="application/x-www-form-urlencoded" """,
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                        "default": "GET"
                    },
                    "url": {
                        "type": "string",
                        "description": "Full URL for the request"
                    },
                    "params": {
                        "type": "string",
                        "description": "URL query parameters, JSON format or key=value&key2=value2 format"
                    },
                    "headers": {
                        "type": "string",
                        "description": "Request headers, JSON format, e.g.: {\"Authorization\": \"Bearer xxx\"}"
                    },
                    "body": {
                        "type": "string",
                        "description": "Request body, can be JSON string, form data, or raw text"
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Content-Type, e.g.: application/json, application/x-www-form-urlencoded",
                        "default": "application/json"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Request timeout in seconds",
                        "default": 30
                    },
                    "follow_redirects": {
                        "type": "boolean",
                        "description": "Whether to follow redirects",
                        "default": True
                    },
                    "verify_ssl": {
                        "type": "boolean",
                        "description": "Whether to verify SSL certificate",
                        "default": True
                    },
                    "include_headers": {
                        "type": "boolean",
                        "description": "Whether to include response headers in the output",
                        "default": True
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="http_raw",
            description="""Send raw HTTP request. Supports pasting request format directly from Burp Suite or other capture tools.

Raw request format example:
POST /api/login HTTP/1.1
Host: example.com
Content-Type: application/json

{"username":"admin","password":"123"}""",
            inputSchema={
                "type": "object",
                "properties": {
                    "raw_request": {
                        "type": "string",
                        "description": "Raw HTTP request text (including request line, headers, blank line, body)"
                    },
                    "base_url": {
                        "type": "string",
                        "description": "Base URL (if raw_request doesn't contain full URL), e.g.: https://example.com"
                    },
                    "verify_ssl": {
                        "type": "boolean",
                        "description": "Whether to verify SSL certificate",
                        "default": True
                    }
                },
                "required": ["raw_request"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute MCP tool call"""
    try:
        if name == "http_request":
            return await handle_http_request(arguments)
        elif name == "http_raw":
            return await handle_http_raw(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {str(e)}")]


async def handle_http_request(args: dict[str, Any]) -> list[TextContent]:
    """Handle general HTTP request"""
    method = args.get("method", "GET").upper()
    url = args["url"]
    params = parse_params(args.get("params"))
    headers = parse_headers(args.get("headers"))
    body = args.get("body")
    content_type = args.get("content_type", "application/json")
    timeout = args.get("timeout", 30)
    follow_redirects = args.get("follow_redirects", True)
    verify_ssl = args.get("verify_ssl", True)
    include_headers = args.get("include_headers", True)
    
    # Set Content-Type
    if body and "content-type" not in {k.lower() for k in headers}:
        headers["Content-Type"] = content_type
    
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=follow_redirects,
        verify=verify_ssl
    ) as client:
        response = await client.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            content=body.encode() if body else None
        )
        
        result = format_response(response, include_headers)
        return [TextContent(type="text", text=result)]


def parse_raw_request(raw: str, base_url: str | None = None) -> tuple[str, str, dict, str | None]:
    """Parse raw HTTP request text"""
    lines = raw.strip().replace("\r\n", "\n").split("\n")
    
    # Parse request line
    request_line = lines[0]
    parts = request_line.split()
    method = parts[0].upper()
    path = parts[1] if len(parts) > 1 else "/"
    
    # Parse request headers
    headers = {}
    body_start = len(lines)
    
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "":
            body_start = i + 1
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
    
    # Parse request body
    body = None
    if body_start < len(lines):
        body = "\n".join(lines[body_start:])
    
    # Build full URL
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        host = headers.get("Host", "")
        if base_url:
            url = base_url.rstrip("/") + path
        elif host:
            # Determine protocol based on SSL-related headers
            protocol = "https" if "443" in host else "http"
            url = f"{protocol}://{host}{path}"
        else:
            url = path
    
    return method, url, headers, body


async def handle_http_raw(args: dict[str, Any]) -> list[TextContent]:
    """Handle raw HTTP request"""
    raw_request = args["raw_request"]
    base_url = args.get("base_url")
    verify_ssl = args.get("verify_ssl", True)
    
    method, url, headers, body = parse_raw_request(raw_request, base_url)
    
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        verify=verify_ssl
    ) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            content=body.encode() if body else None
        )
        
        result = format_response(response)
        return [TextContent(type="text", text=result)]


async def run_server():
    """Run MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Main entry point"""
    import asyncio
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
