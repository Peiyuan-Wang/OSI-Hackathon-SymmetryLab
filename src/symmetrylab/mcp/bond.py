"""Bounded Streamable HTTP MCP client for Valency's fixed public endpoint.

No redirects, remote code, credential persistence, or raw server errors. Tool
schemas are discovered after authentication, rather than assumed from examples.
"""
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from symmetrylab.tools.sources import NoRedirect

ENDPOINT = 'https://mcp.valency.io/'
MAX_BYTES = 2_000_000
VERSIONS = {'2025-11-25', '2025-06-18', '2025-03-26'}


class BondError(RuntimeError):
    """A user-safe diagnostic; never includes provider bodies or credentials."""


def http_post(payload, headers):
    request = Request(ENDPOINT, data=json.dumps(payload).encode(), headers=headers, method='POST')
    try:
        with build_opener(NoRedirect).open(request, timeout=20) as response:
            meta = {k.lower(): v for k, v in response.headers.items()}
            if 'id' not in payload or response.status == 202:
                return None, meta
            if 'text/event-stream' in meta.get('content-type', ''):
                # Stop as soon as our RPC completes; a stream may remain open.
                total, lines, deadline = 0, [], time.monotonic() + 30
                while time.monotonic() < deadline:
                    line = response.readline(MAX_BYTES + 1)
                    total += len(line)
                    if total > MAX_BYTES:
                        raise BondError('Bond response exceeded the size limit.')
                    if not line or not line.strip():
                        if lines:
                            message = json.loads('\n'.join(lines))
                            if isinstance(message, dict) and message.get('id') == payload['id']:
                                return message, meta
                            lines = []
                        if not line:
                            break
                    elif line.startswith(b'data:'):
                        lines.append(line[5:].decode('utf-8').lstrip(' ').rstrip('\r\n'))
                raise BondError('Bond did not complete the request in time.')
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise BondError('Bond response exceeded the size limit.')
            return json.loads(body), meta
    except HTTPError as exc:
        code = exc.code
        exc.close()
        if code in (401, 403):
            raise BondError('Bond rejected the token. Copy a current token from Valency Settings.') from None
        if code == 429:
            raise BondError('Bond rate limit reached. Try again later.') from None
        raise BondError(f'Bond HTTP request failed (status {code}).') from None
    except BondError:
        raise
    except (OSError, ValueError):
        raise BondError('Bond connection failed or returned an invalid response.') from None


class BondMCP:
    def __init__(self, token, post=http_post):
        if not isinstance(token, str) or not token or len(token) > 8192 or any(c.isspace() for c in token):
            raise BondError('Enter a Bond bearer token in Paper survey first.')
        self.token, self.post = token, post
        self.version, self.session, self.sequence = None, None, 0
        self.tools = None

    def rpc(self, method, params, notification=False):
        self.sequence += 1
        payload = {'jsonrpc': '2.0', 'method': method, 'params': params}
        if not notification:
            payload['id'] = self.sequence
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                   'Authorization': 'Bearer ' + self.token}
        if self.version:
            headers['MCP-Protocol-Version'] = self.version
        if self.session:
            headers['Mcp-Session-Id'] = self.session
        message, meta = self.post(payload, headers)
        if method == 'initialize':
            self.session = meta.get('mcp-session-id')
        if notification:
            return None
        if not isinstance(message, dict) or message.get('id') != self.sequence or message.get('jsonrpc') != '2.0':
            raise BondError('Bond returned an invalid MCP response.')
        if 'error' in message or not isinstance(message.get('result'), dict):
            raise BondError('Bond MCP request failed. Check your token and service availability.')
        return message['result']

    def connect(self):
        if self.version:
            return
        result = self.rpc('initialize', {'protocolVersion': '2025-11-25', 'capabilities': {},
                                        'clientInfo': {'name': 'SymmetryLab', 'version': '0.3.1'}})
        version = result.get('protocolVersion')
        if version not in VERSIONS:
            raise BondError('Bond selected an unsupported MCP protocol version.')
        self.version = version
        self.rpc('notifications/initialized', {}, notification=True)

    def list_tools(self):
        self.connect()
        if self.tools is None:
            found, params = {}, {}
            for _ in range(5):
                result = self.rpc('tools/list', params)
                if not isinstance(result.get('tools'), list):
                    raise BondError('Bond did not return tool definitions.')
                for tool in result['tools']:
                    if isinstance(tool, dict) and isinstance(tool.get('name'), str):
                        found[tool['name']] = tool
                cursor = result.get('nextCursor')
                if not cursor:
                    self.tools = found
                    break
                params = {'cursor': cursor}
            else:
                raise BondError('Bond tool discovery exceeded the page limit.')
        return self.tools

    def call(self, name, arguments):
        self.connect()
        result = self.rpc('tools/call', {'name': name, 'arguments': arguments})
        if result.get('isError'):
            raise BondError('Bond tool call failed. Check the token, quota and tool compatibility.')
        return result


def tool_data(result):
    """Prefer structured output; accept the MCP JSON-in-text compatibility form."""
    if isinstance(result.get('structuredContent'), (dict, list)):
        return result['structuredContent']
    for item in result.get('content', []):
        if isinstance(item, dict) and item.get('type') == 'text':
            try:
                value = json.loads(item.get('text', ''))
            except (ValueError, TypeError):
                continue
            if isinstance(value, (dict, list)):
                return value
    raise BondError('Bond returned an unsupported data format; no papers were imported.')
