"""Offline tests: request bodies, output formatting and error messages. Run: pytest tests"""

import os

import pytest

from tools import client
from tools.get_contents import ContextFetchGetContentsTool
from tools.get_contents import build_body as contents_body
from tools.search import ContextFetchSearchTool
from tools.search import build_body as search_body


def test_search_body_defaults_and_filters():
    body = search_body(
        {
            "query": "vector db",
            "num_results": 3.0,
            "include_domains": "github.com, docs.python.org",
            "exclude_domains": "",
            "start_published_date": " 2026-01-01 ",
        }
    )
    assert body == {
        "query": "vector db",
        "numResults": 3,
        "contents": {"text": False, "highlights": False, "prunedContext": True},
        "includeDomains": ["github.com", "docs.python.org"],
        "startPublishedDate": "2026-01-01",
    }
    assert search_body({"query": "q", "content": "none"})["contents"] == {
        "text": False,
        "highlights": False,
        "prunedContext": False,
    }


def test_contents_body_splits_urls_but_keeps_commas_inside_one():
    body = contents_body({"urls": "https://a.com/x,y, https://b.com\nhttps://c.com", "highlights_query": "pricing"})
    assert body == {
        "urls": ["https://a.com/x,y", "https://b.com", "https://c.com"],
        "text": True,
        "highlights": {"query": "pricing"},
    }
    assert contents_body({"urls": "https://a.com", "text": False, "pruned_context": True}) == {
        "urls": ["https://a.com"],
        "text": False,
        "prunedContext": True,
    }


def test_error_messages():
    assert "keys/free" in client.error_message(401, {"error": "invalid_api_key"})
    paid = client.error_message(402, {"message": "Out of credits."})
    assert paid == "Out of credits. Add credits at https://api.contextfetch.dev/buy/instant"
    assert "query: too long" in client.error_message(422, {"detail": [{"loc": ["body", "query"], "msg": "too long"}]})
    assert "public http(s)" in client.error_message(400, {"error": "url_not_allowed"})
    assert "do not use credits" in client.error_message(503, {"message": "Search unavailable"})


class FakeResponse:
    def __init__(self, status, data):
        self.status_code, self._data, self.headers, self.text = status, data, {}, ""

    def json(self):
        return self._data


def run(tool_cls, params, monkeypatch, status, data):
    calls = []
    monkeypatch.setattr(
        client.requests, "request", lambda *a, **kw: calls.append((a, kw)) or FakeResponse(status, data)
    )
    tool = tool_cls.from_credentials({"contextfetch_api_key": "test-key"})
    return list(tool.invoke(params)), calls


def test_search_tool_outputs_json_and_text(monkeypatch):
    data = {
        "results": [{"url": "https://a.com", "title": "A", "prunedContext": "alpha"}],
        "costDollars": {"total": 0.001},
    }
    messages, calls = run(ContextFetchSearchTool, {"query": "q"}, monkeypatch, 200, data)
    assert calls[0][0] == ("POST", "https://api.contextfetch.dev/v1/search")
    assert calls[0][1]["headers"]["Authorization"] == "Bearer test-key"
    assert messages[0].message.json_object == data
    assert "alpha" in messages[1].message.text


def test_contents_tool_reports_failed_pages_and_api_errors(monkeypatch):
    data = {"results": [], "statuses": [{"id": "https://x.com", "status": "error", "error": {"message": "timeout"}}]}
    messages, _ = run(ContextFetchGetContentsTool, {"urls": "https://x.com"}, monkeypatch, 200, data)
    assert "https://x.com: timeout" in messages[-1].message.text
    messages, _ = run(
        ContextFetchGetContentsTool, {"urls": "https://x.com"}, monkeypatch, 401, {"error": "invalid_api_key"}
    )
    assert len(messages) == 1 and "did not accept the API key" in messages[0].message.text


@pytest.mark.skipif(not os.environ.get("CONTEXTFETCH_API_KEY"), reason="set CONTEXTFETCH_API_KEY for the live test")
def test_live():
    key = os.environ["CONTEXTFETCH_API_KEY"]
    search = list(
        ContextFetchSearchTool.from_credentials({"contextfetch_api_key": key}).invoke(
            {"query": "python asyncio timeout", "num_results": 2}
        )
    )
    assert search[0].message.json_object["results"], search
    print(search[1].message.text[:400])
    pages = list(
        ContextFetchGetContentsTool.from_credentials({"contextfetch_api_key": key}).invoke(
            {
                "urls": "https://docs.python.org/3/library/asyncio-task.html",
                "highlights_query": "timeout",
                "text": False,
            }
        )
    )
    assert pages[0].message.json_object["results"], pages
    print(pages[1].message.text[:400])
