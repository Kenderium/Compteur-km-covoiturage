"""Tests de l'intégration Home Assistant, avec un faux serveur CarpoX."""

import copy
import json
from pathlib import Path

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.carpox.const import DOMAIN

URL = "https://carpox.example.org"
OVERVIEW_URL = URL + "/api/me/overview"

# Réponse type de /api/me/overview. Le serveur vérifie qu'il renvoie bien ces
# clés (server/tests/test_home_assistant.py) : les deux côtés restent d'accord.
OVERVIEW = json.loads((Path(__file__).parent / "overview.json").read_text(encoding="utf-8"))
CAR = OVERVIEW["cars"][0]


async def _setup(hass, aioclient_mock, overview=OVERVIEW):
    aioclient_mock.get(OVERVIEW_URL, json=overview)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=f"{URL}#1", title="CarpoX Loïc",
                            data={CONF_URL: URL, CONF_TOKEN: "cpx_abc"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _entity(hass, key, platform="sensor"):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(platform, DOMAIN, f"{URL}#1_{key}")
    assert entity_id, key
    return hass.states.get(entity_id)


async def test_assistant_de_configuration(hass, aioclient_mock):
    aioclient_mock.get(OVERVIEW_URL, json=OVERVIEW)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL + "/", CONF_TOKEN: " cpx_abc "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "CarpoX Loïc"
    assert result["data"] == {CONF_URL: URL, CONF_TOKEN: "cpx_abc"}
    assert result["result"].unique_id == f"{URL}#1"
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == "Bearer cpx_abc"

    # Le même compte une deuxième fois : refusé.
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_TOKEN: "cpx_abc"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_assistant_erreurs(hass, aioclient_mock):
    aioclient_mock.get(OVERVIEW_URL, status=401)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_TOKEN: "mauvais"})
    assert result["errors"] == {"base": "invalid_auth"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "carpox.example.org", CONF_TOKEN: "x"})
    assert result["errors"] == {CONF_URL: "invalid_url"}
    aioclient_mock.clear_requests()
    aioclient_mock.get(OVERVIEW_URL, json={"pas": "carpox"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_TOKEN: "x"})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_capteurs(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock)
    assert entry.state is ConfigEntryState.LOADED

    assert _entity(hass, "box-1234_km_since_fill").state == "150.0"
    fuel = _entity(hass, "box-1234_fuel_remaining")
    assert fuel.state == "41.0"
    assert fuel.attributes["unit_of_measurement"] == "L"
    assert fuel.attributes["litres_dernier_plein"] == 45
    assert _entity(hass, "box-1234_fuel_level").state == "82.0"
    assert _entity(hass, "box-1234_consumption").attributes["source"] == "measured"
    assert _entity(hass, "box-1234_odometer").state == "100150.0"
    balance = _entity(hass, "box-1234_my_balance")
    assert balance.state == "5.0"
    assert balance.attributes["on_me_doit"] == [{"nom": "Julien", "montant": 5.0}]
    assert _entity(hass, "box-1234_settlements").attributes["virements"] == ["Julien → Loïc : 5.00 €"]
    assert _entity(hass, "box-1234_last_sync").state == "2026-09-21T14:13:20+00:00"
    last = _entity(hass, "box-1234_last_trip")
    assert last.state == "100.0" and last.attributes["a_bord"] == ["Loïc", "Julien"]
    assert _entity(hass, "account_balance").state == "5.0"
    assert _entity(hass, "account_owed").state == "5.0"

    tracker = _entity(hass, "box-1234_position", "device_tracker")
    assert tracker.attributes["latitude"] == 50.668
    assert tracker.attributes["longitude"] == 4.6118

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, f"{URL}#1_box-1234")})
    assert device.name == "Golf"


async def test_reservoir_non_regle_et_nouvelle_voiture(hass, aioclient_mock):
    car = copy.deepcopy(CAR)
    car["fuel"].update(tank_l=None, remaining_l=None, remaining_pct=None, range_km=None, last_fill=None)
    car["last_position"] = None
    car["last_trip"] = None
    entry = await _setup(hass, aioclient_mock, {**OVERVIEW, "cars": [car]})
    assert _entity(hass, "box-1234_fuel_remaining").state == "unknown"
    assert _entity(hass, "box-1234_position", "device_tracker").state == "unknown"

    # Une deuxième voiture apparaît sur le compte : ses capteurs sont créés.
    other = {**copy.deepcopy(CAR), "id": "box-9999", "name": "Clio"}
    aioclient_mock.clear_requests()
    aioclient_mock.get(OVERVIEW_URL, json={**OVERVIEW, "cars": [car, other]})
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert _entity(hass, "box-9999_km_since_fill").state == "150.0"


async def test_jeton_revoque_demande_un_nouveau(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(OVERVIEW_URL, status=401)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]

    aioclient_mock.clear_requests()
    aioclient_mock.get(OVERVIEW_URL, json=OVERVIEW)
    result = await hass.config_entries.flow.async_configure(flows[0]["flow_id"], {CONF_TOKEN: "cpx_new"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == "cpx_new"


async def test_options_intervalle(hass, aioclient_mock):
    entry = await _setup(hass, aioclient_mock)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval_min": 15})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval.total_seconds() == 900
