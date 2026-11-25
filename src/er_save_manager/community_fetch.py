"""Downloads from the community preset and character library repositories.

Index files name ids and URLs that become cache file names and download
targets, so they are checked before use: ids are plain names, URLs stay under
the Hapfel1 raw.githubusercontent.com tree (redirects included), certificates
are always verified and every response has a size cap.
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request

ALLOWED_PREFIX = "https://raw.githubusercontent.com/Hapfel1/"

INDEX_MAX_BYTES = 8 * 1024 * 1024
JSON_MAX_BYTES = 1024 * 1024
IMAGE_MAX_BYTES = 20 * 1024 * 1024
CHARACTER_MAX_BYTES = 32 * 1024 * 1024

_ID_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_REL_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")


class CommunityFetchError(Exception):
    pass


def safe_id(value: object) -> str:
    """value if it is usable as a file name stem, else CommunityFetchError."""
    if isinstance(value, str) and _ID_RE.match(value):
        return value
    raise CommunityFetchError(f"Invalid id: {str(value)[:80]!r}")


def resolve_url(base_url: str, url: object) -> str:
    """Absolute URL under ALLOWED_PREFIX for url, relative paths joined to base_url."""
    if not isinstance(url, str) or not url:
        raise CommunityFetchError("Missing URL")
    if url.startswith(("http://", "https://")):
        full = url
    elif _REL_RE.match(url):
        full = base_url + url
    else:
        raise CommunityFetchError(f"Invalid relative URL: {url[:120]!r}")
    _check_allowed(full)
    return full


def _check_allowed(url: str) -> None:
    path = url.split("?", 1)[0]
    if (
        not url.startswith(ALLOWED_PREFIX)
        or "/../" in path
        or "/./" in path
        or "\\" in url
        or "%2e" in path.lower()
        or "@" in path
    ):
        raise CommunityFetchError(
            f"URL outside the community repositories: {url[:120]!r}"
        )


def ssl_context() -> ssl.SSLContext:
    """Verifying context, using certifi's CA bundle when it is installed."""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


class _AllowedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_allowed(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener(context: ssl.SSLContext) -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context), _AllowedRedirects()
    )


def fetch_bytes(
    url: str, context: ssl.SSLContext, max_bytes: int, timeout: float = 15
) -> bytes:
    """Body of url (already resolved), CommunityFetchError past max_bytes."""
    _check_allowed(url)
    with _opener(context).open(url, timeout=timeout) as response:
        length = response.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > max_bytes:
            raise CommunityFetchError(f"Response larger than {max_bytes} bytes")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise CommunityFetchError(f"Response larger than {max_bytes} bytes")
    return data
