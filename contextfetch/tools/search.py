from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import ContextFetchError, request, split_list

CONTENT_FIELDS = ("text", "highlights", "pruned_context")


def build_body(params: dict[str, Any]) -> dict[str, Any]:
    content = params.get("content") or "pruned_context"
    body: dict[str, Any] = {
        "query": params["query"],
        "numResults": int(params.get("num_results") or 5),
        "contents": {
            "text": content == "text",
            "highlights": content == "highlights",
            "prunedContext": content == "pruned_context",
        },
    }
    for param, field in (("include_domains", "includeDomains"), ("exclude_domains", "excludeDomains")):
        domains = split_list(params.get(param))
        if domains:
            body[field] = domains
    if params.get("start_published_date"):
        body["startPublishedDate"] = str(params["start_published_date"]).strip()
    return body


def format_results(results: list[dict[str, Any]]) -> str:
    blocks = []
    for i, r in enumerate(results, 1):
        lines = [f"## {i}. {r.get('title') or r.get('url', '')}", f"URL: {r.get('url', '')}"]
        if r.get("publishedDate"):
            lines.append(f"Published: {r['publishedDate']}")
        content = r.get("prunedContext") or r.get("text")
        if not content and r.get("highlights"):
            content = "\n\n".join(str(h) for h in r["highlights"])
        if content:
            lines.append("")
            lines.append(str(content))
        blocks.append("\n".join(lines))
    return "\n\n---\n\n".join(blocks)


class ContextFetchSearchTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = self.runtime.credentials.get("contextfetch_api_key")
        if not api_key:
            yield self.create_text_message("ContextFetch API key is missing. Set it in the plugin credentials.")
            return
        if not str(tool_parameters.get("query") or "").strip():
            yield self.create_text_message("Please enter a search query.")
            return

        try:
            response = request("POST", api_key, "/v1/search", build_body(tool_parameters))
        except ContextFetchError as e:
            yield self.create_text_message(f"ContextFetch search failed: {e}")
            return

        results = response.get("results") or []
        if not results:
            yield self.create_text_message("No results found.")
            return
        yield self.create_json_message(response)
        yield self.create_text_message(format_results(results))
