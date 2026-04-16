"""
Zendesk API client — HTTP wrapper with retry, rate limiting, and pagination.

Phase 0 version: minimal client used for connection validation and discovery.
Full version with rate limiting and all endpoints is built in Phase 2.
"""

import logging
import time
from typing import Any, Generator

import requests

from src.config import AUTH, BASE_URL, PROXIES, SSL_VERIFY, require_zendesk_credentials

logger = logging.getLogger(__name__)


class ZendeskClient:
    """
    Thin wrapper around the Zendesk REST API.

    Auth: HTTP Basic with API token — '{email}/token:{token}'.
    All methods perform GET only. POST/PUT/DELETE are intentionally absent.
    """

    def __init__(self) -> None:
        require_zendesk_credentials()
        self.session = requests.Session()
        self.session.auth = AUTH
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        if PROXIES:
            self.session.proxies.update(PROXIES)
            logger.info("Proxy configured: %s", PROXIES)
        if not SSL_VERIFY:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL verification disabled (SSL_VERIFY=false)")
        self.session.verify = SSL_VERIFY

    def _request(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """
        Perform a GET request with basic error handling.

        Endpoint should be the path portion, e.g. '/api/v2/users/me.json'.
        Returns the parsed JSON body.
        Raises requests.HTTPError on 4xx/5xx with a descriptive message.
        """
        url = f"{BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
        except requests.exceptions.SSLError as exc:
            raise ConnectionError(
                f"SSL error connecting to Zendesk. If you're behind a corporate proxy, "
                f"set HTTP_PROXY and HTTPS_PROXY in your .env file.\nDetails: {exc}"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(
                f"Could not connect to {url}. Check your ZENDESK_SUBDOMAIN and network.\nDetails: {exc}"
            ) from exc

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning("Rate limited. Waiting %s seconds...", retry_after)
            time.sleep(retry_after)
            return self._request(endpoint, params)

        if not response.ok:
            raise requests.HTTPError(
                f"HTTP {response.status_code} for {url}\nResponse: {response.text[:500]}",
                response=response,
            )

        return response.json()

    def get_current_user(self) -> dict[str, Any]:
        """
        GET /api/v2/users/me.json
        Returns the authenticated user object.
        Shape: {"user": {"id": int, "name": str, "email": str, ...}}
        """
        return self._request("/api/v2/users/me.json")

    def get_ticket_fields(self) -> list[dict[str, Any]]:
        """
        GET /api/v2/ticket_fields.json (paginated)
        Returns the full list of ticket fields (system + custom).
        Shape per item: {"id": int, "title": str, "type": str, "active": bool, ...}
        """
        fields: list[dict[str, Any]] = []
        params: dict[str, Any] = {"per_page": 100, "page": 1}

        while True:
            data = self._request("/api/v2/ticket_fields.json", params=params)
            fields.extend(data.get("ticket_fields", []))
            if not data.get("next_page"):
                break
            params["page"] += 1

        return fields

    def get_views(self) -> list[dict[str, Any]]:
        """
        GET /api/v2/views.json (paginated)
        Returns all views the authenticated user can access.
        Shape per item: {"id": int, "title": str, "active": bool, "conditions": {...}, ...}
        """
        views: list[dict[str, Any]] = []
        params: dict[str, Any] = {"per_page": 100, "page": 1}

        while True:
            data = self._request("/api/v2/views.json", params=params)
            views.extend(data.get("views", []))
            if not data.get("next_page"):
                break
            params["page"] += 1

        return views

    def get_view_tickets(
        self, view_id: str | int, page_size: int = 100
    ) -> Generator[dict[str, Any], None, None]:
        """
        GET /api/v2/views/{view_id}/tickets.json (cursor pagination)
        Yields ticket dicts one by one.
        Shape per ticket: {"id": int, "subject": str, "status": str, "custom_fields": [...], ...}
        """
        params: dict[str, Any] = {"per_page": page_size}
        endpoint = f"/api/v2/views/{view_id}/tickets.json"

        while endpoint:
            data = self._request(endpoint, params)
            for ticket in data.get("tickets", []):
                yield ticket
            next_page = data.get("next_page")
            if next_page:
                # next_page is a full URL; extract the path
                endpoint = next_page.replace(BASE_URL, "")
                params = {}
            else:
                endpoint = None

    def get_side_conversations(self, ticket_id: int) -> list[dict[str, Any]]:
        """
        GET /api/v2/tickets/{ticket_id}/side_conversations.json
        Returns list of side conversations for a ticket.
        Shape per item: {"id": str (UUID), "subject": str, "state": str,
                         "participants": [...], "created_at": str, ...}
        """
        data = self._request(f"/api/v2/tickets/{ticket_id}/side_conversations.json")
        return data.get("side_conversations", [])

    def get_side_conversation_events(
        self, ticket_id: int, side_conv_id: str
    ) -> list[dict[str, Any]]:
        """
        GET /api/v2/tickets/{ticket_id}/side_conversations/{side_conv_id}/events.json
        Returns list of events for a side conversation.
        Shape per item: {"id": str, "type": str, "created_at": str,
                         "actor": {...}, "message": {...}, ...}
        """
        data = self._request(
            f"/api/v2/tickets/{ticket_id}/side_conversations/{side_conv_id}/events.json"
        )
        # API returns key "events", not "side_conversation_events"
        return data.get("events", [])
