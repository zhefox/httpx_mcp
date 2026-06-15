# HTTPX MCP

An MCP tool for HTTP interface testing, built on the httpx library, designed for AI.

## Features

- 🚀 **Full HTTP Method Support**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- 📝 **Multiple Request Formats**: JSON, form data, raw text
- 🔧 **Custom Headers**: Support for arbitrary HTTP headers
- 📋 **Raw Request Parsing**: Directly paste Burp Suite captured requests
- ⏱️ **Response Details**: Status code, response headers, response body, timing statistics
- 🔒 **SSL Control**: Optional SSL certificate verification

## Installation

```bash
cd httpx-mcp
pip install -e .
```
or

```
pip install httpx-mcp
```


## MCP Configuration

Add to your MCP configuration file:

```json
{
  "mcpServers": {
    "httpx-mcp": {
      "command": "python",
      "args": ["-m", "httpx_mcp.server"],
      "cwd": "c:/Users/ZHEFOX/Desktop/mcptools/httpx-mcp"
    }
  }
}
```

Or use directly after installation:

```json
{
  "mcpServers": {
    "httpx-mcp": {
      "command": "httpx-mcp"
    }
  }
}
```

## Security

`httpx-mcp` can make outbound HTTP requests from the machine where the MCP
server is running. To reduce SSRF risk when tool calls are influenced by LLM
output or prompt injection, requests to non-public network addresses are blocked
by default. This includes localhost/loopback, private RFC1918 ranges, link-local
addresses such as cloud metadata endpoints, IPv6 unique local addresses, and
other non-globally routable targets. Redirect targets are validated before each
redirected request.

For trusted and isolated security testing environments that intentionally need
internal network access, set `HTTPX_MCP_ALLOW_PRIVATE_NETWORK=true` in the MCP
server environment:

```json
{
  "mcpServers": {
    "httpx-mcp": {
      "command": "httpx-mcp",
      "env": {
        "HTTPX_MCP_ALLOW_PRIVATE_NETWORK": "true"
      }
    }
  }
}
```

Only enable this option when you understand that the tool can then reach any
HTTP(S) endpoint available to the MCP server process.

## Available Tools

### 1. `http_request` - General HTTP Request

Send any HTTP request, switch request method via the `method` parameter.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | ✅ | - | Full URL |
| `method` | string | - | GET | HTTP method: GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS |
| `params` | string | - | - | URL query parameters, JSON or key=value format |
| `headers` | string | - | - | Request headers, JSON format |
| `body` | string | - | - | Request body |
| `content_type` | string | - | application/json | Content-Type |
| `timeout` | number | - | 30 | Timeout in seconds |
| `follow_redirects` | boolean | - | true | Whether to follow redirects |
| `verify_ssl` | boolean | - | true | Whether to verify SSL |
| `include_headers` | boolean | - | true | Whether response includes headers |

**Examples:**

```
# GET request
method="GET", url="https://httpbin.org/get"

# GET with query parameters
method="GET", url="https://httpbin.org/get", params='{"page": "1", "size": "10"}'

# POST JSON
method="POST", url="https://httpbin.org/post", body='{"name": "test", "value": 123}'

# PUT update
method="PUT", url="https://httpbin.org/put", body='{"id": 1, "name": "updated"}'

# DELETE
method="DELETE", url="https://httpbin.org/delete"

# With authentication header
method="GET", url="https://api.example.com/users", headers='{"Authorization": "Bearer token123"}'

# POST form
method="POST", url="https://httpbin.org/post", body="username=admin&password=123", content_type="application/x-www-form-urlencoded"

# Disable SSL verification
method="GET", url="https://self-signed.example.com", verify_ssl=false
```

### 2. `http_raw` - Raw HTTP Request

Directly parse raw HTTP requests captured by tools like Burp Suite.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `raw_request` | string | ✅ | - | Raw HTTP request text |
| `base_url` | string | - | - | Base URL (if request doesn't contain full URL) |
| `verify_ssl` | boolean | - | true | Whether to verify SSL |

**Example:**

```
raw_request="""
POST /api/login HTTP/1.1
Host: example.com
Content-Type: application/json
Cookie: session=abc123

{"username":"admin","password":"123456"}
"""
base_url="https://example.com"
```

## Response Format

The tool returns formatted response information:

```
HTTP/1.1 200 OK

=== Response Headers ===
content-type: application/json
date: Mon, 01 Jan 2024 00:00:00 GMT
...

=== Response Body ===
{
  "result": "success",
  "data": {...}
}

=== Request Info ===
Time: 0.234s
Size: 1024 bytes
```

## Use Cases

1. **API Testing**: Quickly test REST API endpoints
2. **Security Testing**: Send custom payloads for security testing
3. **Interface Debugging**: View detailed request/response information
4. **Request Replay**: Directly use Burp captured content to replay requests

## License

MIT

## Acknowledgements

SSRF hardening was reported privately by Syed Anas Mohiuddin.

