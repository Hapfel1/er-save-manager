"""
Minimal PostgREST client for the community Supabase project.

Covers the calls the sharing and metrics modules make (select with eq/in
filters, insert, rpc) over plain HTTP, with the anon key and no
authentication. Raises SupabaseError on any non-2xx response; the message
carries the response body, so callers can match PostgREST error text such
as "duplicate key".
"""

from __future__ import annotations

from typing import Any

import requests

SUPABASE_URL = "https://rnsrvcfjzsgrgiwvsbub.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
    "InJuc3J2Y2ZqenNncmdpd3ZzYnViIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0NjM5"
    "ODgsImV4cCI6MjA4NTAzOTk4OH0.W54LjC-aJs5RgWSQ0O2-UhY6S2kGco9Ra6AgvgJfXHo"
)

TIMEOUT = 15

# PostgREST list syntax treats these as separators inside in.(...)
_RESERVED = ",:()"


class SupabaseError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }


def _quote(value: Any) -> str:
    text = str(value)
    if any(char in text for char in _RESERVED):
        return f'"{text}"'
    return text


def _request(method: str, path: str, **kwargs) -> Any:
    response = requests.request(
        method,
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={**_headers(), **kwargs.pop("headers", {})},
        timeout=TIMEOUT,
        **kwargs,
    )
    if not response.ok:
        raise SupabaseError(f"HTTP {response.status_code}: {response.text}")
    if not response.content:
        return None
    return response.json()


def select(
    table: str,
    columns: str = "*",
    eq: dict[str, Any] | None = None,
    in_: tuple[str, list[Any]] | None = None,
) -> list[dict[str, Any]]:
    """Rows of `table`, filtered by column equality and/or one column IN list."""
    params = {"select": columns.replace(" ", "")}
    for column, value in (eq or {}).items():
        params[column] = f"eq.{value}"
    if in_ is not None:
        column, values = in_
        params[column] = f"in.({','.join(_quote(v) for v in values)})"
    return _request("GET", table, params=params) or []


def insert(table: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    """Insert one row, return the inserted rows as PostgREST echoes them."""
    return (
        _request("POST", table, json=row, headers={"Prefer": "return=representation"})
        or []
    )


def rpc(function: str, params: dict[str, Any]) -> Any:
    """Call a Postgres function exposed by PostgREST."""
    return _request("POST", f"rpc/{function}", json=params)
