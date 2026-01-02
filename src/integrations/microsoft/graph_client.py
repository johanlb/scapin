"""
Microsoft Graph API Client

Provides async HTTP client for Microsoft Graph API with:
- Automatic authentication
- Rate limiting and retry logic
- Pagination support
- Delta queries for efficient polling
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from src.integrations.microsoft.auth import MicrosoftAuthenticator
from src.monitoring.logger import get_logger

logger = get_logger("integrations.microsoft.graph_client")


class GraphAPIError(Exception):
    """Raised when Graph API returns an error"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


@dataclass
class GraphClient:
    """
    Microsoft Graph API Client

    Handles HTTP requests to Graph API with authentication,
    rate limiting, pagination, and delta queries.

    Usage:
        auth = MicrosoftAuthenticator(config, cache_dir)
        client = GraphClient(auth)

        # Simple GET
        me = await client.get("/me")

        # GET with pagination
        messages = await client.get_all_pages("/me/chats")

        # POST
        await client.post("/me/chats/123/messages", {"body": {"content": "Hello"}})

        # Clean up when done
        await client.close()
    """

    authenticator: MicrosoftAuthenticator
    base_url: str = "https://graph.microsoft.com/v1.0"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    _delta_links: dict[str, str] = field(default_factory=dict, init=False)
    _client: Optional[httpx.AsyncClient] = field(default=None, init=False)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and release resources"""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "GraphClient":
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        await self.close()

    async def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Make GET request to Graph API

        Args:
            endpoint: API endpoint (e.g., "/me/chats")
            params: Query parameters

        Returns:
            Response JSON as dict

        Raises:
            GraphAPIError: If request fails
        """
        return await self._request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Make POST request to Graph API

        Args:
            endpoint: API endpoint
            json_data: Request body

        Returns:
            Response JSON as dict

        Raises:
            GraphAPIError: If request fails
        """
        return await self._request("POST", endpoint, json=json_data)

    async def get_all_pages(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        max_pages: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get all pages of a collection

        Automatically handles @odata.nextLink pagination.

        Args:
            endpoint: API endpoint
            params: Query parameters
            max_pages: Maximum pages to fetch (safety limit)

        Returns:
            List of all items across all pages

        Raises:
            GraphAPIError: If any request fails
        """
        items: list[dict[str, Any]] = []
        url = f"{self.base_url}{endpoint}"
        page_count = 0

        while url and page_count < max_pages:
            page_count += 1

            # Make request
            if page_count == 1:
                # First page uses params
                data = await self._request("GET", endpoint, params=params)
            else:
                # Subsequent pages use full URL from @odata.nextLink
                data = await self._request_url("GET", url)

            # Collect items
            items.extend(data.get("value", []))

            # Check for next page
            url = data.get("@odata.nextLink")

        if page_count >= max_pages:
            logger.warning(f"Hit max pages limit ({max_pages}) for {endpoint}")

        return items

    async def get_delta(
        self,
        resource: str,
        params: Optional[dict[str, Any]] = None,
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        """
        Get changes using delta query

        Delta queries return only items that have changed since the last call.
        The delta link is stored and reused automatically.

        Args:
            resource: Resource path (e.g., "/me/chats")
            params: Additional query parameters

        Returns:
            Tuple of (changed_items, delta_link)

        Raises:
            GraphAPIError: If request fails
        """
        # Check for stored delta link
        delta_link = self._delta_links.get(resource)

        if delta_link:
            # Use stored delta link
            data = await self._request_url("GET", delta_link)
        else:
            # Initial request with /delta
            endpoint = f"{resource}/delta"
            data = await self._request("GET", endpoint, params=params)

        # Get items
        items = data.get("value", [])

        # Handle pagination for delta
        next_link = data.get("@odata.nextLink")
        while next_link:
            next_data = await self._request_url("GET", next_link)
            items.extend(next_data.get("value", []))
            next_link = next_data.get("@odata.nextLink")
            # deltaLink is in the last page
            if "@odata.deltaLink" in next_data:
                data["@odata.deltaLink"] = next_data["@odata.deltaLink"]

        # Store new delta link for next call
        new_delta_link = data.get("@odata.deltaLink")
        if new_delta_link:
            self._delta_links[resource] = new_delta_link

        return items, new_delta_link

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make request to Graph API endpoint"""
        url = f"{self.base_url}{endpoint}"
        return await self._request_url(method, url, params=params, json=json)

    async def _request_url(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make request to full URL"""
        # Get token (this is sync, but fast if cached)
        token = self.authenticator.get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        last_error: Optional[Exception] = None

        client = await self._get_client()

        for attempt in range(self.max_retries):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                )

                # Handle throttling
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                # Handle errors
                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    error_info = error_data.get("error", {})
                    raise GraphAPIError(
                        message=error_info.get("message", f"HTTP {response.status_code}"),
                        status_code=response.status_code,
                        error_code=error_info.get("code"),
                    )

                # Success
                if response.status_code == 204:
                    return {}  # No content
                return response.json()

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Request error: {e} (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))

        # All retries exhausted
        raise GraphAPIError(f"Request failed after {self.max_retries} attempts: {last_error}")
