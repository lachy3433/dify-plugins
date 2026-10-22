"""HTTP calls to the ContextFetch API and error messages that say what to do next."""

import re
from typing import Any

import requests

API_BASE = "https://api.contextfetch.dev"
BUY_URL = "https://api.contextfetch.dev/buy/instant"
TIMEOUT_SECONDS = 90
RETRY_HINT = "Try again shortly. Failed requests do not use credits."


class ContextFetchError(Exception):
    pass


def split_list(value: Any, pattern: str = r"[,\n]") -> list[str]:
    """Turn a comma or newline separated string (or a list) into a list of non-empty strings."""
    if not value:
        return []
    items = value if isinstance(value, list) else re.split(pattern, str(value))
    return [s.strip() for s in items if s and s.strip()]


def split_urls(value: Any) -> list[str]:
    # Whitespace, or a comma that starts the next URL, so a comma inside one URL is kept.
    return split_list(value, r"\s+|,(?=\s*https?://)")


def _validation_text(detail: Any) -> str:
    # FastAPI 422 detail: [{"loc": ["body", "query"], "msg": "..."}] -> "query: ..."
    if not isinstance(detail, list):
        return detail if isinstance(detail, str) else ""
    return "; ".join(
        f"{'.'.join(str(p) for p in (d.get('loc') or [])[1:])}: {d.get('msg', '')}"
        for d in detail
        if isinstance(d, dict)
    )


def error_message(status: int, body: dict[str, Any]) -> str:
    message = body.get("message") or body.get("error") or f"ContextFetch answered HTTP {status}"
    if status == 402:
        return f"{body.get('message') or 'ContextFetch credits ran out.'} Add credits at {BUY_URL}"
    if status == 401:
        return (
            "ContextFetch did not accept the API key. Check the key in the ContextFetch credential. "
            "A free key with 2,500 credits: POST https://api.contextfetch.dev/v1/keys/free "
            f"(one per network). Or add credits at {BUY_URL}"
        )
    if status == 400 and body.get("error") == "url_not_allowed":
        return "This URL cannot be fetched. Only public http(s) URLs are allowed."
    if status == 422:
        return f"ContextFetch rejected the parameters: {_validation_text(body.get('detail')) or 'invalid request'}"
    if status == 429:
        return "ContextFetch is rate limiting requests. Wait a few seconds and try again."
    if status >= 500:
        return f"{message}. {RETRY_HINT}"
    return message


def request(method: str, api_key: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        response = requests.request(
            method,
            API_BASE + path,
            json=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "contextfetch-dify-plugin/0.0.1",
            },
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise ContextFetchError(f"Could not reach ContextFetch: {type(e).__name__}. {RETRY_HINT}") from e

    try:
        data = response.json()
    except ValueError:
        data = {"message": response.text[:300]}
    if not isinstance(data, dict):
        data = {}
    if response.status_code >= 400:
        raise ContextFetchError(error_message(response.status_code, data))
    return data
