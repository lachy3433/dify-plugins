from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools.client import ContextFetchError, request


class ContextFetchProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        api_key = credentials.get("contextfetch_api_key")
        if not api_key:
            raise ToolProviderCredentialValidationError("ContextFetch API key is missing.")
        try:
            # GET /v1/balance costs no credits and answers 401 for an unknown key.
            request("GET", api_key, "/v1/balance")
        except ContextFetchError as e:
            raise ToolProviderCredentialValidationError(str(e)) from e
