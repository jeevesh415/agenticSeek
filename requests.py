"""Minimal requests-compatible shim for offline test environments.

This module intentionally implements only the subset used by this project.
"""
from __future__ import annotations

import json as _json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class RequestException(Exception):
    """Base HTTP request exception."""


class HTTPError(RequestException):
    """Raised for non-2xx responses when applicable."""


class exceptions:  # pylint: disable=too-few-public-methods
    RequestException = RequestException
    HTTPError = HTTPError


@dataclass
class Response:
    status_code: int
    text: str
    reason: str = ""

    def json(self) -> Any:
        return _json.loads(self.text)


def _request(method: str, url: str, *, json: Any = None, headers: dict | None = None, timeout: int = 10) -> Response:
    request_headers = dict(headers or {})
    data = None
    if json is not None:
        data = _json.dumps(json).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=request_headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            body = resp.read().decode("utf-8", errors="replace")
            return Response(status_code=resp.status, text=body, reason=getattr(resp, "reason", ""))
    except urllib.error.HTTPError as e:  # pragma: no cover - hard to trigger deterministically in tests
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        return Response(status_code=e.code, text=body, reason=str(e.reason))
    except Exception as e:  # pragma: no cover
        raise RequestException(str(e)) from e


def get(url: str, headers: dict | None = None, timeout: int = 10) -> Response:
    return _request("GET", url, headers=headers, timeout=timeout)


def post(url: str, json: Any = None, headers: dict | None = None, timeout: int = 10) -> Response:
    return _request("POST", url, json=json, headers=headers, timeout=timeout)
