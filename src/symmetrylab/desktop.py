"""SymmetryLab desktop application: the workbench in a native window.

The same interface runs inside the operating system's web view (WKWebView on macOS)
through pywebview. A private loopback server on a random port serves it; nothing is
reachable from other machines. Data lives in the per-user application folder.
"""
import argparse
import os
from pathlib import Path
import sys
import threading
import webbrowser

APP_NAME = "SymmetryLab"


def data_dir():
    """Per-user data folder. SYMMETRYLAB_HOME overrides it (useful for tests)."""
    if os.environ.get("SYMMETRYLAB_HOME"):
        return Path(os.environ["SYMMETRYLAB_HOME"]).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME


class Bridge:
    """Functions the page may call as window.pywebview.api.* (downloads and links)."""
    window = None

    def save_file(self, filename, text):
        import webview
        name = Path(str(filename)).name or "symmetrylab.txt"
        chosen = self.window.create_file_dialog(webview.FileDialog.SAVE, save_filename=name)
        if not chosen:
            return {"status": "cancelled"}
        target = Path(chosen if isinstance(chosen, str) else chosen[0])
        target.write_text(str(text), encoding="utf-8")
        return {"status": "saved", "path": str(target)}

    def open_external(self, url):
        if isinstance(url, str) and url.startswith(("https://", "http://")):
            webbrowser.open(url)
        return True


def start_server(root):
    from symmetrylab.web.server import make_server
    root = Path(root)
    (root / "workbench").mkdir(parents=True, exist_ok=True)
    server = make_server(0, root / "workbench")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument("--server-only", action="store_true", help="serve without opening a window (diagnostics)")
    args, _ = parser.parse_known_args(argv)
    root = data_dir()
    server = start_server(root)
    url = f"http://127.0.0.1:{server.server_port}/"
    if args.server_only:
        print(f"{APP_NAME} serving {url} with data in {root}", flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
        return 0
    import webview
    bridge = Bridge()
    bridge.window = webview.create_window(APP_NAME, url, js_api=bridge, width=1440, height=920, min_size=(1000, 700),
                                          text_select=True, background_color="#F5F6F0")
    try:
        webview.start(private_mode=False, storage_path=str(root / "webview"))
    finally:
        server.app.cancel.set()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
