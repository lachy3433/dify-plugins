# ContextFetch

**Author:** contextfetch
**Version:** 0.0.1
**Type:** tool
**Source:** https://github.com/lachy3433/dify-plugins/tree/contextfetch-source/contextfetch
**Contact:** hello@contextfetch.dev

## Description

[ContextFetch](https://contextfetch.dev) is a web search and page contents API for AI agents. This plugin adds two tools to Dify:

- **ContextFetch Search**: search the web. Each result has a title, URL, published date and page content: pruned context (the chunks relevant to the query, in page order), highlights, or the full page as Markdown. 1 credit per search.
- **ContextFetch Get Contents**: fetch up to 10 pages as Markdown, optionally with the chunks relevant to a query. 1 credit per page that loads.

Both tools return the API's JSON response and a Markdown text version for the LLM.

## Setup

1. Get an API key. A free key with 2,500 credits (one per network):

   ```bash
   curl -X POST https://api.contextfetch.dev/v1/keys/free
   ```

   Paid credit packs and the docs are at https://contextfetch.dev/docs.
2. In Dify, install the ContextFetch plugin from the Marketplace.
3. Open **Tools > ContextFetch > Authorize** and paste the API key. The key is checked with `GET /v1/balance`, which costs no credits.

## Usage

Add **ContextFetch Search** or **ContextFetch Get Contents** to an Agent, Chatflow or Workflow.

ContextFetch Search parameters:

| Parameter | Description |
| --- | --- |
| Query | What to search for (up to 2,000 characters). Required. |
| Max Results | 1 to 25, default 5. |
| Page Content | Pruned context (default), Highlights, Full text, or None. |
| Include Domains / Exclude Domains | Comma-separated domains, e.g. `docs.python.org, github.com`. |
| Published After | ISO 8601 date, e.g. `2026-01-01`. |

ContextFetch Get Contents parameters:

| Parameter | Description |
| --- | --- |
| URLs | Up to 10 public http(s) URLs, separated by commas, spaces or new lines. Required. |
| Highlights Query | Return the chunks of each page relevant to this query. |
| Full Text | Return each page as Markdown (default on). |
| Pruned Context | Return the relevant chunks joined in page order, to save tokens. |

Pages that fail to load are listed with the reason. API errors come back as a text message that says what to do next (for example, an invalid key, credits ran out with a link to add more, or a rate limit).

## Connection requirements

The plugin sends HTTPS requests to `https://api.contextfetch.dev` only, authenticated with your API key as `Authorization: Bearer <key>`. The Dify plugin runtime needs outbound network access to that host.

## Privacy

See [PRIVACY.md](PRIVACY.md).
