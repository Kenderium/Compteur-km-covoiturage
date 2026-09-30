"""Assistant de configuration : adresse du serveur et jeton personnel."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarpoxAuthError, CarpoxClient, CarpoxError, normalize_url
from .const import (
    CONF_SCAN_INTERVAL_MIN,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    MAX_SCAN_INTERVAL_MIN,
    MIN_SCAN_INTERVAL_MIN,
)

_LOGGER = logging.getLogger(__name__)


class CarpoxConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _check(self, url: str, token: str) -> tuple[dict[str, Any] | None, dict[str, str]]:
        """Lit la vue d'ensemble. Retourne (données, erreurs du formulaire)."""
        if not url.startswith(("https://", "http://")):
            return None, {CONF_URL: "invalid_url"}
        client = CarpoxClient(async_get_clientsession(self.hass), url, token)
        try:
            return await client.overview(), {}
        except CarpoxAuthError:
            return None, {"base": "invalid_auth"}
        except CarpoxError:
            return None, {"base": "cannot_connect"}
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Erreur inattendue en contactant CarpoX")
            return None, {"base": "unknown"}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            token = user_input[CONF_TOKEN].strip()
            data, errors = await self._check(url, token)
            if data is not None:
                # Un même compte CarpoX ne peut être ajouté qu'une fois ; plusieurs comptes, oui.
                await self.async_set_unique_id(f"{url}#{data['user']['id']}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"CarpoX {data['user']['display_name']}",
                    data={CONF_URL: url, CONF_TOKEN: token},
                )
        schema = vol.Schema({
            vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, "https://")): str,
            vol.Required(CONF_TOKEN): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Le jeton a été révoqué : on en demande un nouveau pour le même compte."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            data, errors = await self._check(entry.data[CONF_URL], token)
            if data is not None:
                await self.async_set_unique_id(f"{entry.data[CONF_URL]}#{data['user']['id']}")
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(entry, data_updates={CONF_TOKEN: token})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return CarpoxOptionsFlow()


class CarpoxOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL_MIN, DEFAULT_SCAN_INTERVAL_MIN)
        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL_MIN, default=current): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_MIN, max=MAX_SCAN_INTERVAL_MIN)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
