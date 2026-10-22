"""Loopback-only HTTP workbench with one bounded research worker."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import shutil
from threading import Event, Lock, Thread
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4
from symmetrylab.agent_core.workbench import run_agent, limits_from
from symmetrylab.agent_core.profile import research_profile
from symmetrylab.communication.workbench import render_agent_report
from symmetrylab.database.workbench import RunStore
from symmetrylab.model.client import OpenAICompatibleClient
from symmetrylab.literature.service import Literature

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


HINTS = {
    "API key environment variable is not set": "Export the variable in the same terminal before starting the server (export SYMMETRYLAB_API_KEY=...), then restart it.",
    "HTTP 401": "The service rejected the key. Check that the key is valid and belongs to this Base URL.",
    "HTTP 403": "The service refused access. Check the key's permissions or account balance.",
    "HTTP 404": "Wrong endpoint. Base URL must end at /v1 (without /responses or /chat/completions), and the protocol must be one the service supports.",
    "HTTP 400": "The service rejected the request. Check the model ID spelling and try the other protocol.",
    "HTTP 429": "Rate limited or out of quota at the provider.",
    "connection failed or timed out": "The service did not answer. For CC Switch, confirm local routing is enabled on this port; for a remote service, check the URL and network/proxy.",
    "returned no text content": "The service answered without text. Try the other protocol (Responses vs Chat Completions).",
    "malformed JSON": "The response was not OpenAI-compatible JSON. Check the Base URL and protocol.",
}


def explain(message):
    hint = next((v for k, v in HINTS.items() if k in message), "")
    return message[:300] + (" — " + hint if hint else "")


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
        self.literature = Literature(Path(root).resolve().parent / "literature")
        self.encoder_job = {"status": "idle"}

    def prepare_encoder(self):
        """Explicit, user-requested PhysBERT download in the background."""
        with self.lock:
            if self.encoder_job["status"] == "preparing":
                return self.encoder_job
            self.encoder_job = {"status": "preparing"}
        def work():
            from symmetrylab.literature.encoders import prepare_physbert
            try:
                result = prepare_physbert()
                self.literature._encoder = None
                job = {"status": "ready", "version": result["version"]}
            except Exception:
                job = {"status": "failed", "message": "PhysBERT could not be prepared. Install the 'physics' extra (pip install -e .[physics]) and check the network."}
            with self.lock:
                self.encoder_job = job
        Thread(target=work, daemon=True).start()
        return self.encoder_job

    def literature_state(self):
        return {**self.literature.state(), "encoder_job": self.encoder_job}

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
                rows[identifier] = {**{k: s[k] for k in ("run_id", "goal", "status", "mode", "created_at")}, "track": s.get("research_profile", {}).get("track", "legacy")}
            active = self.active
        for row in rows.values():
            if row["status"] == "running" and row["run_id"] != active:
                row["status"] = "interrupted"
        return sorted(rows.values(), key=lambda row: row["created_at"], reverse=True)[:100]

    def start(self, request):
        mode, goal = request.get("mode", "demo"), request.get("goal", "")
        if mode not in {"demo", "live"} or not isinstance(goal, str) or not 1 <= len(goal.strip()) <= 4000:
            raise ValueError("select demo/live and enter a research question (1–4000 characters)")
        profile = research_profile(request.get("research_profile"))
        config = connection_config(request.get("connection", self.config))
        limits = limits_from({"limits": request.get("limits", {}), "research_profile": profile})
        client = OpenAICompatibleClient(config) if mode == "live" else None
        style = self.literature.active_style() if request.get("use_style") else None
        if request.get("use_style") and not style:
            raise ValueError("No active voice profile. Build and enable it on the Paper survey page first.")
        with self.lock:
            if self.active or self.probing:
                raise ValueError("a run or connection test is already active")
            identifier = uuid4().hex
            self.active = identifier
            self.cancel = Event()
            self.config = config
            self.snapshots[identifier] = {"run_id": identifier, "goal": goal, "mode": mode, "status": "running", "created_at": "pending", "research_profile": profile}
        def update(state):
            with self.lock:
                self.snapshots[identifier] = state
        def worker():
            try:
                extra = {"style_prompt": style["prompt"], "style_hash": style["hash"]} if style else {}
                run_agent(goal, self.store.folder(identifier), mode, {"limits": limits, **extra, **({"research_profile": profile} if profile["track"] != "legacy" else {})}, client, self.cancel.is_set, update)
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

    def clear(self, track):
        """Delete stored runs (and therefore their lessons and preferences) for one workspace."""
        if track not in {"theory", "experiment", "all"}:
            raise ValueError("choose theory, experiment or all")
        with self.lock:
            if self.active or self.probing:
                raise ValueError("wait for the current run or test to finish before clearing history")
            removed = 0
            for row in self.store.list():
                row_track = "experiment" if row["track"] == "experiment" else "theory"
                if track != "all" and row_track != track:
                    continue
                folder = self.store.folder(row["run_id"])
                if folder.parent != self.store.root:
                    continue
                shutil.rmtree(folder)
                self.snapshots.pop(row["run_id"], None)
                removed += 1
        return {"status": "cleared", "removed": removed}

    def probe(self, config):
        config = connection_config(config)
        client = OpenAICompatibleClient(config, timeout=60)
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
            public_navigation = (not mutation and self.command == "GET" and urlsplit(self.path).path in {"/", "/experiment", "/papers"}
                                 and self.headers.get("Sec-Fetch-Mode") == "navigate" and self.headers.get("Sec-Fetch-Dest") == "document")
            if self.headers.get("Sec-Fetch-Site") == "cross-site" and not public_navigation:
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
            routes = {"/": ("index.html", "text/html"), "/experiment": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css"),
                      "/papers": ("papers.html", "text/html"), "/papers.js": ("papers.js", "text/javascript")}
            if parts.path in routes:
                name, mime = routes[parts.path]
                return self.send((static / name).read_bytes(), kind=mime + "; charset=utf-8")
            if parts.path == "/api/bootstrap":
                return self.send({"token": app.token, "connection": app.config, "runs": app.listing()})
            if parts.path == "/api/runs":
                return self.send(app.listing())
            if parts.path == "/api/literature":
                return self.send(app.literature_state())
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
                if not 0 < length <= 64000 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("a bounded JSON request is required")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("request must be an object")
                if self.path == "/api/runs":
                    return self.send(app.start(data), 202)
                if self.path == "/api/connection/test":
                    return self.send(app.probe(data))
                if self.path == "/api/runs/clear":
                    return self.send(app.clear(data.get("track")))
                if self.path.startswith("/api/literature/"):
                    lit, action = app.literature, self.path.rsplit("/", 1)[-1]
                    if action == "profile":
                        lit.set_profile(data.get("keywords", []), data.get("papers", []), data.get("physics_only", True))
                    elif action == "search":
                        lit.search()
                    elif action == "vote":
                        lit.vote(data.get("paper_id"), data.get("vote"))
                    elif action == "adopt":
                        lit.adopt(data.get("term"))
                    elif action == "style":
                        lit.rebuild_style(data.get("enabled", True))
                    elif action == "style-enabled":
                        lit.set_style_enabled(bool(data.get("enabled")))
                    elif action == "clear":
                        lit.clear()
                    elif action == "prepare-encoder":
                        app.prepare_encoder()
                    else:
                        return self.send({"error": "not found"}, 404)
                    return self.send(app.literature_state())
                path = self.path.strip("/").split("/")
                if len(path) == 4 and path[:2] == ["api", "runs"] and path[3] == "preference":
                    state = app.snapshot(path[2])
                    if state["status"] != "completed":
                        raise ValueError("Preference feedback requires a completed research dossier")
                    choices = {d["direction_id"]: d["title"] for d in state.get("directions", [])}
                    left, right, choice, reason = (data.get(k) for k in ("left", "right", "choice", "reason"))
                    if any(not isinstance(x, str) for x in (left, right, choice, reason)):
                        raise ValueError("Invalid preference fields")
                    if left == right or left not in choices or right not in choices or choice not in {left, right, "tie", "defer"} or not 1 <= len(reason.strip()) <= 1500:
                        raise ValueError("Compare two existing directions and supply a reason")
                    item = {"origin":"researcher_feedback", "left":choices[left], "right":choices[right],
                            "choice":choices.get(choice, choice), "reason":reason.strip()}
                    with app.lock:
                        target = app.store.folder(path[2]) / "preference_feedback.jsonl"
                        if target.is_symlink() or (target.exists() and target.stat().st_size > 90000):
                            raise ValueError("Feedback storage limit reached")
                        with target.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    return self.send({"status":"recorded", "message":"Preference saved for future runs with the same supplied paper context."})
                if len(path) == 4 and path[:2] == ["api", "runs"] and path[3] == "cancel":
                    with app.lock:
                        if app.active != path[2]:
                            raise ValueError("this run is not active")
                        app.cancel.set()
                    return self.send({"status": "cancellation_requested"})
                return self.send({"error": "not found"}, 404)
            except (ValueError, RuntimeError) as exc:
                # Project-authored messages never contain keys or response bodies; show the actual cause.
                return self.send({"error": explain(str(exc))}, 400)
            except (OSError, KeyError, TypeError):
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
