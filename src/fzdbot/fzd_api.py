import asyncio
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

API_KEY_HEADER = "X-API-Key"


class FzdApiError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class FzdApi:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def set_tag(self, discord_user_id: int, discord_user_name: str, tag: str) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/v1/players/{discord_user_id}/tag",
            json={"discord_user_name": discord_user_name, "tag": tag},
        )

    async def add_score(
        self,
        discord_user_id: int,
        discord_user_name: str,
        tag: str,
        scheduled_event_id: int,
        score: int,
        machine_id: int | None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/v1/players/{discord_user_id}/scores",
            json={
                "scheduled_event_id": scheduled_event_id,
                "discord_user_name": discord_user_name,
                "tag": tag,
                "score": score,
                "machine_id": machine_id,
            },
        )

    async def list_scores(self, discord_user_id: int, scheduled_event_id: int) -> list[dict[str, Any]]:
        body = await self._request(
            "GET",
            f"/v1/players/{discord_user_id}/scores?scheduled_event_id={scheduled_event_id}",
        )
        return body["scores"]

    async def edit_score(self, discord_user_id: int, score_id: int, points: int) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/v1/players/{discord_user_id}/scores/{score_id}",
            json={"points": points},
        )

    async def delete_score(self, discord_user_id: int, score_id: int) -> None:
        await self._request("DELETE", f"/v1/players/{discord_user_id}/scores/{score_id}")

    async def machines(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/v1/machines")

    async def active_events(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/v1/events/active")

    async def scoreboard(self, scheduled_event_id: int, discord_user_id: int) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/v1/events/{scheduled_event_id}/scoreboard?discord_user_id={discord_user_id}",
        )

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)

        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method, url, json=json, headers={API_KEY_HEADER: self._api_key}
            ) as response:
                body = await self._read_body(response)
                if response.status >= 400:
                    raise FzdApiError(self._message_for(response.status, body), response.status)
                return body
        except asyncio.TimeoutError as error:
            logger.error("[API] %s %s timed out", method, url)
            raise FzdApiError("The FZD API did not answer in time. Nothing was changed.") from error
        except aiohttp.ClientError as error:
            logger.error("[API] %s %s failed: %s", method, url, error)
            raise FzdApiError(f"Could not reach the FZD API ({error}). Nothing was changed.") from error

    @staticmethod
    async def _read_body(response: aiohttp.ClientResponse) -> Any:
        try:
            return await response.json(content_type=None)
        except (ValueError, aiohttp.ContentTypeError):
            return {}

    @staticmethod
    def _message_for(status: int, body: Any) -> str:
        detail = body.get("detail") if isinstance(body, dict) else None
        if status == 401:
            return "The FZD API rejected this bot's key. Its `FZD_API_KEY` needs to match what the API has configured."
        if status == 403:
            return "The FZD API refused this request."
        if status == 404:
            return f"The FZD API could not find that record. ({detail or 'not found'})"
        if status == 409:
            return f"The FZD API could not make that change. ({detail or 'conflict'})"
        if status == 422:
            return f"The FZD API rejected the request as invalid: {detail if isinstance(detail, str) else body or 'no detail given'}"
        if status >= 500:
            return f"The FZD API failed ({status}). Nothing was changed; try again, and tell a dev if it keeps happening."
        return f"The FZD API answered {status}. ({detail or 'no detail given'})"
