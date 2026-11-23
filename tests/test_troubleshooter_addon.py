"""Troubleshooter addon download: asset selection and install over an old version."""

import io
import zipfile

import pytest

from er_save_manager.addons import troubleshooter_addon_manager as tam


class _Response:
    def __init__(self, payload=None, content=b""):
        self._payload = payload
        self._content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload

    def iter_content(self, chunk_size):
        yield self._content


@pytest.mark.skipif(tam.os.name == "nt", reason="Linux asset layout")
def test_update_replaces_old_install_with_bare_appimage(tmp_path, monkeypatch):
    monkeypatch.setattr(tam.Path, "home", lambda: tmp_path)
    url = "https://example.invalid/v2.0.0/FromSoftware-Troubleshooter_2.0.0_Linux.AppImage"
    release = {
        "tag_name": "v2.0.0",
        "assets": [
            {
                "name": "FromSoftware-Troubleshooter_2.0.0_Windows.zip",
                "browser_download_url": "x",
            },
            {"name": url.rsplit("/", 1)[1], "browser_download_url": url},
        ],
    }
    old_zip = io.BytesIO()
    with zipfile.ZipFile(old_zip, "w") as z:
        z.writestr("FromSoftware-Troubleshooter-1.8.0-x86_64.AppImage", b"old")
    responses = {
        "old": _Response(content=old_zip.getvalue()),
        tam.TroubleshooterAddon.GITHUB_API_URL: _Response(payload=release),
        url: _Response(content=b"new"),
    }
    monkeypatch.setattr(tam.requests, "get", lambda u, **kw: responses[u])

    addon = tam.TroubleshooterAddon()
    monkeypatch.setattr(addon, "get_download_url", lambda v: "old")
    assert addon.download_and_install("1.8")
    assert addon.executable_path.read_bytes() == b"old"

    addon = tam.TroubleshooterAddon()
    assert addon.check_for_updates() == (True, "2.0.0")
    assert addon.get_download_url("2.0.0") == url
    assert addon.download_and_install("2.0.0")
    assert addon.executable_path.read_bytes() == b"new"
    assert addon.get_installed_version() == "2.0.0"
    assert sorted(p.name for p in addon.addon_dir.iterdir()) == [
        "FromSoftware-Troubleshooter",
        "version.json",
    ]
