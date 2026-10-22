"""Bounded Chat Completions / Responses adapter, including CC Switch routing."""

import json
import os
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.error import HTTPError, URLError


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OpenAICompatibleClient:
    def __init__(self, config, timeout=60):
        url = config["base_url"].rstrip("/")
        parsed = urlsplit(url)
        self.local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        self.protocol = config.get("protocol", "chat_completions")
        self.auth_mode = config.get("auth_mode", "environment")
        if self.protocol not in {"chat_completions", "responses"}:
            raise ValueError("unsupported API protocol")
        if self.auth_mode not in {"environment", "cc_switch"}:
            raise ValueError("unsupported authentication mode")
        if (not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.scheme not in {"https", "http"}
                or (parsed.scheme == "http" and not self.local)):
            raise ValueError("base_url requires HTTPS, or HTTP on loopback, with no credentials/query/fragment")
        if self.auth_mode == "cc_switch" and not self.local:
            raise ValueError("CC Switch authentication requires a loopback URL")
        self.url = url + ("/responses" if self.protocol == "responses" else "/chat/completions")
        self.model = config["model"]
        if not isinstance(self.model, str) or not self.model.strip() or self.model == "SET_YOUR_MODEL" or len(self.model) > 200:
            raise ValueError("configure a real model identifier before live mode")
        # This is only a placeholder: CC Switch injects its configured upstream key.
        self.key = "PROXY_MANAGED" if self.auth_mode == "cc_switch" else os.environ.get(config.get("api_key_env", "SYMMETRYLAB_API_KEY"))
        if not self.key:
            raise ValueError("API key environment variable is not set")
        self.timeout = timeout

    def complete(self, messages, max_tokens):
        if self.protocol == "responses":
            body = {"model": self.model, "instructions": "\n".join(m["content"] for m in messages if m["role"] == "system"),
                    "input": [m for m in messages if m["role"] != "system"],
                    "max_output_tokens": max_tokens, "store": False, "stream": False}
        else:
            body = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
        request = Request(self.url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json", "User-Agent": "SymmetryLab/0.2", "Authorization": "Bearer " + self.key})
        handlers = [NoRedirect] + ([ProxyHandler({})] if self.local else [])
        try:
            with build_opener(*handlers).open(request, timeout=self.timeout) as response:
                data = response.read(1_000_001)
            if len(data) > 1_000_000:
                raise RuntimeError("model response exceeds size limit")
            # Some routing providers return SSE even for a non-streaming request.
            if data.lstrip().startswith((b"event:", b"data:")):
                events = [json.loads(line[5:].strip()) for line in data.decode().splitlines()
                          if line.startswith("data:") and line[5:].strip() not in {"", "[DONE]"}]
                completed = [e["response"] for e in events if e.get("type") == "response.completed"]
                if not completed:
                    raise RuntimeError("model stream did not complete")
                body = completed[-1]
            else:
                body = json.loads(data)
            if self.protocol == "responses":
                if body.get("status") in {"failed", "incomplete", "cancelled"} or body.get("error"):
                    raise RuntimeError("model response was incomplete or failed")
                content = "".join(part["text"] for item in body.get("output", []) if item.get("type") == "message"
                                  for part in item.get("content", []) if part.get("type") == "output_text")
            else:
                content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("model returned no text content")
            return {"content": content, "usage": body.get("usage") or {}, "model": self.model}
        except HTTPError as exc:
            raise RuntimeError(f"model request failed (HTTP {exc.code})") from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError("model connection failed or timed out; check the service and routing settings") from None
        except (KeyError, IndexError, TypeError, UnicodeError, json.JSONDecodeError):
            raise RuntimeError("model returned malformed JSON") from None
