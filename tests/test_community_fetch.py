import io
import urllib.request

import pytest

from er_save_manager import community_fetch as cf

BASE = "https://raw.githubusercontent.com/Hapfel1/er-character-presets/main/"


def test_ids_and_urls():
    assert cf.safe_id("preset_000") == "preset_000"
    for bad in ("../x", "a/b", "", "x" * 65, None, "a.json"):
        with pytest.raises(cf.CommunityFetchError):
            cf.safe_id(bad)

    assert cf.resolve_url(BASE, "presets/preset_000/data.json") == (
        BASE + "presets/preset_000/data.json"
    )
    assert cf.resolve_url(BASE, BASE + "index.json?ts=1") == BASE + "index.json?ts=1"
    for bad in (
        "https://evil.example/x.png",
        "http://raw.githubusercontent.com/Hapfel1/r/main/x.png",
        "https://raw.githubusercontent.com/Other/r/main/x.png",
        BASE + "../../Other/r/main/x.png",
        BASE + "%2e%2e/x",
        "/etc/passwd",
        "../x",
        "presets/..\\x",
        "",
    ):
        with pytest.raises(cf.CommunityFetchError):
            cf.resolve_url(BASE, bad)


def test_redirect_outside_prefix_is_refused():
    handler = cf._AllowedRedirects()
    req = urllib.request.Request(BASE + "index.json")
    with pytest.raises(cf.CommunityFetchError):
        handler.redirect_request(req, None, 302, "", {}, "https://evil.example/")


def test_size_cap(monkeypatch):
    class Response(io.BytesIO):
        headers: dict = {}

    class Opener:
        def open(self, url, timeout):
            return Response(b"x" * 11)

    monkeypatch.setattr(cf, "_opener", lambda context: Opener())
    assert cf.fetch_bytes(BASE + "a", None, 11) == b"x" * 11
    with pytest.raises(cf.CommunityFetchError):
        cf.fetch_bytes(BASE + "a", None, 10)
    with pytest.raises(cf.CommunityFetchError):
        cf.fetch_bytes("https://evil.example/a", None, 100)
