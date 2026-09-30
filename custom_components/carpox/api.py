"""Client de l'API CarpoX : une seule lecture, /api/me/overview."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class CarpoxError(Exception):
    """Erreur de communication avec le serveur CarpoX."""


class CarpoxAuthError(CarpoxError):
    """Jeton refusé (révoqué, ou pas un jeton personnel)."""


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


class CarpoxClient:
    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self._session = session
        self.url = normalize_url(url)
        self._token = token.strip()

    async def overview(self) -> dict[str, Any]:
        try:
            async with asyncio.timeout(20):
                resp = await self._session.get(
                    self.url + "/api/me/overview",
                    headers={"Authorization": "Bearer " + self._token, "Accept": "application/json"},
                )
                if resp.status in (401, 403):
                    raise CarpoxAuthError
                if resp.status != 200:
                    raise CarpoxError(f"HTTP {resp.status}")
                data = await resp.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise CarpoxError(str(err)) from err
        if not isinstance(data, dict) or "user" not in data or "cars" not in data:
            raise CarpoxError("réponse inattendue : est-ce bien un serveur CarpoX ?")
        return data
