"""Intégration CarpoX : km, carburant estimé et soldes de covoiturage.

Chaque entrée correspond à un compte CarpoX (adresse du serveur + jeton
personnel en lecture seule, créé dans l'app, onglet Compte). Chaque voiture
du compte devient un appareil Home Assistant.
"""

from __future__ import annotations

from homeassistant.const import CONF_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarpoxClient
from .coordinator import CarpoxConfigEntry, CarpoxCoordinator

PLATFORMS = [Platform.SENSOR, Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: CarpoxConfigEntry) -> bool:
    client = CarpoxClient(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_TOKEN])
    coordinator = CarpoxCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload_on_options_change))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CarpoxConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _reload_on_options_change(hass: HomeAssistant, entry: CarpoxConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
