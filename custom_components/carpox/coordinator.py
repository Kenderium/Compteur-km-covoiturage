"""Lecture périodique du serveur CarpoX."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CarpoxAuthError, CarpoxClient, CarpoxError
from .const import CONF_SCAN_INTERVAL_MIN, DEFAULT_SCAN_INTERVAL_MIN, DOMAIN

_LOGGER = logging.getLogger(__name__)

type CarpoxConfigEntry = ConfigEntry[CarpoxCoordinator]


class CarpoxCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: CarpoxConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CarpoxConfigEntry, client: CarpoxClient) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL_MIN, DEFAULT_SCAN_INTERVAL_MIN)
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN,
                         update_interval=timedelta(minutes=minutes))
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.overview()
        except CarpoxAuthError as err:
            raise ConfigEntryAuthFailed("Jeton CarpoX refusé") from err
        except CarpoxError as err:
            raise UpdateFailed(f"Serveur CarpoX injoignable : {err}") from err

    @property
    def user(self) -> dict[str, Any]:
        return self.data["user"]

    def car(self, car_id: str) -> dict[str, Any] | None:
        for car in self.data["cars"]:
            if car["id"] == car_id:
                return car
        return None
