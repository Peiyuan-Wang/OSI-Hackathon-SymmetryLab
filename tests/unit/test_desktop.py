import webbrowser
from symmetrylab import desktop


def test_data_dir_override_and_platform_default(monkeypatch, tmp_path):
    monkeypatch.setenv("SYMMETRYLAB_HOME", str(tmp_path / "home"))
    assert desktop.data_dir() == tmp_path / "home"
    monkeypatch.delenv("SYMMETRYLAB_HOME")
    monkeypatch.setattr(desktop.sys, "platform", "darwin")
    assert str(desktop.data_dir()).endswith("Library/Application Support/SymmetryLab")


def test_bridge_opens_only_web_links(monkeypatch):
    opened = []
    monkeypatch.setattr(webbrowser, "open", opened.append)
    bridge = desktop.Bridge()
    bridge.open_external("https://arxiv.org/abs/2510.04184")
    bridge.open_external("file:///etc/passwd"); bridge.open_external("javascript:alert(1)")
    assert opened == ["https://arxiv.org/abs/2510.04184"]


def test_server_uses_app_data_folder(tmp_path):
    server = desktop.start_server(tmp_path)
    try:
        assert server.app.connection.path == tmp_path / "connection.json"
        assert server.app.literature.root == tmp_path / "literature"
        assert (tmp_path / "workbench").is_dir()
    finally:
        server.shutdown(); server.server_close()
