from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import ContextFetchError, request, split_urls

MAX_URLS = 10


def build_body(params: dict[str, Any]) -> dict[str, Any]:
    text = params.get("text")
    body: dict[str, Any] = {
        "urls": split_urls(params.get("urls")),
        "text": True if text is None else bool(text),
    }
    query = str(params.get("highlights_query") or "").strip()
    if query:
        body["highlights"] = {"query": query}
    if params.get("pruned_context"):
        body["prunedContext"] = True
    return body


def failed_pages(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"url": s.get("id"), "error": (s.get("error") or {}).get("message") or "Page did not load"}
        for s in response.get("statuses") or []
        if isinstance(s, dict) and s.get("status") == "error"
    ]


def format_pages(response: dict[str, Any]) -> str:
    blocks = []
    for r in response.get("results") or []:
        lines = [f"# {r.get('title') or r.get('url', '')}", f"URL: {r.get('url', '')}"]
        content = r.get("prunedContext") or r.get("text")
        if r.get("highlights") and not r.get("prunedContext"):
            lines.append("")
            lines.append("Highlights:\n" + "\n\n".join(str(h) for h in r["highlights"]))
        if content:
            lines.append("")
            lines.append(str(content))
        blocks.append("\n".join(lines))
    failed = failed_pages(response)
    if failed:
        blocks.append("Pages that did not load:\n" + "\n".join(f"- {f['url']}: {f['error']}" for f in failed))
    return "\n\n---\n\n".join(blocks)


class ContextFetchGetContentsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = self.runtime.credentials.get("contextfetch_api_key")
        if not api_key:
            yield self.create_text_message("ContextFetch API key is missing. Set it in the plugin credentials.")
            return

        body = build_body(tool_parameters)
        if not body["urls"]:
            yield self.create_text_message("Please enter at least one URL.")
            return
        if len(body["urls"]) > MAX_URLS:
            yield self.create_text_message(f"Too many URLs: {len(body['urls'])}. Send up to {MAX_URLS} at a time.")
            return

        try:
            response = request("POST", api_key, "/v1/contents", body)
        except ContextFetchError as e:
            yield self.create_text_message(f"ContextFetch could not get the pages: {e}")
            return

        if not response.get("results") and not failed_pages(response):
            yield self.create_text_message("No content could be fetched from the given URLs.")
            return
        yield self.create_json_message(response)
        yield self.create_text_message(format_pages(response))
