"""Loopback-only HTTP workbench with one bounded research worker."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from threading import Event, Lock, Thread
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4
from symmetrylab.agent_core.workbench import run_agent, limits_from
from symmetrylab.communication.workbench import render_agent_report
from symmetrylab.database.workbench import RunStore
from symmetrylab.model.client import OpenAICompatibleClient

DEFAULT_CONNECTION = {"base_url": "http://127.0.0.1:15721/v1", "model": "", "protocol": "responses",
                      "auth_mode": "cc_switch", "api_key_env": "SYMMETRYLAB_API_KEY"}
CONNECTION_FIELDS = set(DEFAULT_CONNECTION)


def connection_config(config):
    if not isinstance(config, dict) or set(config) - CONNECTION_FIELDS:
        raise ValueError("only public connection settings are accepted; API keys belong in CC Switch or environment variables")
    result = dict(DEFAULT_CONNECTION, **config)
    if any(not isinstance(v, str) or len(v) > 500 for v in result.values()):
        raise ValueError("invalid connection settings")
    return result


class Workbench:
    def __init__(self, root, config=None):
        self.store = RunStore(root)
        self.config = connection_config(config or {})
        self.token = secrets.token_urlsafe(32)
        self.lock = Lock()
        self.active = None
        self.cancel = Event()
        self.snapshots = {}
        self.probing = False

    def snapshot(self, identifier):
        with self.lock:
            if identifier in self.snapshots:
                return deepcopy(self.snapshots[identifier])
        state = self.store.read(identifier)
        if state["status"] == "running":
            state["status"] = "interrupted"
            state["limitations"].append("Server stopped before completion. Start a new run to continue research.")
        return state

    def listing(self):
        rows = {r["run_id"]: r for r in self.store.list()}
        with self.lock:
            for identifier, s in self.snapshots.items():
                rows[identifier] = {k: s[k] for k in ("run_id", "goal", "status", "mode", "created_at")}
            active = self.active
        for row in rows.values():
            if row["status"] == "running" and row["run_id"] != active:
                row["status"] = "interrupted"
        return sorted(rows.values(), key=lambda row: row["created_at"], reverse=True)[:100]

    def start(self, request):
        mode, goal = request.get("mode", "demo"), request.get("goal", "")
        if mode not in {"demo", "live"} or not isinstance(goal, str) or not 1 <= len(goal.strip()) <= 4000:
            raise ValueError("select demo/live and enter a research question (1–4000 characters)")
        config = connection_config(request.get("connection", self.config))
        limits = limits_from({"limits": request.get("limits", {})})
        client = OpenAICompatibleClient(config) if mode == "live" else None
        with self.lock:
            if self.active or self.probing:
                raise ValueError("a run or connection test is already active")
            identifier = uuid4().hex
            self.active = identifier
            self.cancel = Event()
            self.config = config
            self.snapshots[identifier] = {"run_id": identifier, "goal": goal, "mode": mode, "status": "running", "created_at": "pending"}
        def update(state):
            with self.lock:
                self.snapshots[identifier] = state
        def worker():
            try:
                run_agent(goal, self.store.folder(identifier), mode, {"limits": limits}, client, self.cancel.is_set, update)
            except Exception:
                # Never expose arbitrary exception text from infrastructure or credentials.
                with self.lock:
                    self.snapshots[identifier]["status"] = "failed"
                    self.snapshots[identifier]["error"] = "Run failed unexpectedly; inspect local implementation and tests."
            finally:
                with self.lock:
                    self.active = None
        Thread(target=worker, daemon=True).start()
        return {"run_id": identifier}

    def probe(self, config):
        config = connection_config(config)
        client = OpenAICompatibleClient(config, timeout=15)
        with self.lock:
            if self.active or self.probing:
                raise ValueError("wait for the current run or test to finish")
            self.probing = True
        try:
            response = client.complete([{"role": "user", "content": "Reply with OK only."}], 64)
            self.config = config
            return {"status": "connected", "model": response["model"], "protocol": config["protocol"],
                    "message": "The service returned a valid text response. This test used a real model request."}
        finally:
            with self.lock:
                self.probing = False


def make_server(port=8787, root="data/workbench", config=None):
    app = Workbench(root, config)
    static = Path(__file__).parent / "static"
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def safe_origin(self, mutation=False):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in allowed or (origin and origin != "http://" + host):
                return False
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                return False
            return not mutation or secrets.compare_digest(self.headers.get("X-SymmetryLab-Token", ""), app.token)

        def send(self, data, status=200, kind="application/json; charset=utf-8", filename=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode() if kind.startswith("application/json") else data.encode()
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if not self.safe_origin():
                return self.send({"error": "local same-origin access required"}, 403)
            parts = urlsplit(self.path)
            routes = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
            if parts.path in routes:
                name, mime = routes[parts.path]
                return self.send((static / name).read_bytes(), kind=mime + "; charset=utf-8")
            if parts.path == "/api/bootstrap":
                return self.send({"token": app.token, "connection": app.config, "runs": app.listing()})
            if parts.path == "/api/runs":
                return self.send(app.listing())
            try:
                path = parts.path.strip("/").split("/")
                if len(path) in {3, 4} and path[:2] == ["api", "runs"]:
                    state = app.snapshot(path[2])
                    if len(path) == 3:
                        return self.send(state)
                    if path[3] == "report":
                        audience = parse_qs(parts.query).get("audience", ["researcher"])[0]
                        report = render_agent_report(state, audience)
                        return self.send(report, kind="text/plain; charset=utf-8", filename=f"symmetrylab_{audience}.md" if "download" in parse_qs(parts.query) else None)
                    if path[3] == "download":
                        return self.send(state, filename="symmetrylab_result.json")
            except (ValueError, OSError, KeyError):
                return self.send({"error": "run or report not available"}, 404)
            return self.send({"error": "not found"}, 404)

        def do_POST(self):
            if not self.safe_origin(True):
                return self.send({"error": "valid local request token required"}, 403)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 24000 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("a bounded JSON request is required")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("request must be an object")
                if self.path == "/api/runs":
                    return self.send(app.start(data), 202)
                if self.path == "/api/connection/test":
                    return self.send(app.probe(data))
                path = self.path.strip("/").split("/")
                if len(path) == 4 and path[:2] == ["api", "runs"] and path[3] == "cancel":
                    with app.lock:
                        if app.active != path[2]:
                            raise ValueError("this run is not active")
                        app.cancel.set()
                    return self.send({"status": "cancellation_requested"})
                return self.send({"error": "not found"}, 404)
            except (ValueError, RuntimeError, OSError, KeyError, TypeError):
                # Adapter errors are deliberately sanitized; use a helpful general message.
                return self.send({"error": "Request failed. Check the model ID, Base URL, selected protocol and local routing/key configuration; only one run or test can be active."}, 400)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.app = app
    return server


def serve(port=8787, root="data/workbench", config=None):
    server = make_server(port, root, config)
    print(f"SymmetryLab Workbench: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.app.cancel.set()
    finally:
        server.server_close()
