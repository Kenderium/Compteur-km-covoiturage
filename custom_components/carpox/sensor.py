"""Capteurs CarpoX : km, carburant estimé, soldes, dernière synchro."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CarpoxConfigEntry, CarpoxCoordinator
from .entity import CarpoxAccountEntity, CarpoxCarEntity

EUR = "EUR"


def _euros(cents: int | None) -> float | None:
    return None if cents is None else round(cents / 100, 2)


def _time(unix: int | None) -> datetime | None:
    return None if not unix else datetime.fromtimestamp(unix, tz=timezone.utc)


def _transfers(items: list[dict[str, Any]], who: str) -> list[dict[str, Any]]:
    return [{"nom": t[who]["name"], "montant": _euros(t["amount_cents"])} for t in items]


@dataclass(frozen=True, kw_only=True)
class CarSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


@dataclass(frozen=True, kw_only=True)
class AccountSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _km(key: str, value_fn, state_class=SensorStateClass.MEASUREMENT, **kw) -> CarSensorDescription:
    return CarSensorDescription(
        key=key, translation_key=key, value_fn=value_fn, device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS, state_class=state_class,
        suggested_display_precision=0, **kw)


CAR_SENSORS: tuple[CarSensorDescription, ...] = (
    _km("km_since_fill", lambda c: c["km"]["since_fill"], icon="mdi:gas-station-outline"),
    CarSensorDescription(
        key="fuel_remaining", translation_key="fuel_remaining",
        value_fn=lambda c: c["fuel"]["remaining_l"],
        device_class=SensorDeviceClass.VOLUME_STORAGE, native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, icon="mdi:gas-station",
        attrs_fn=lambda c: {
            "reservoir_l": c["fuel"]["tank_l"],
            "dernier_plein": _time((c["fuel"]["last_fill"] or {}).get("at")),
            "litres_dernier_plein": (c["fuel"]["last_fill"] or {}).get("litres"),
        }),
    CarSensorDescription(
        key="fuel_level", translation_key="fuel_level", value_fn=lambda c: c["fuel"]["remaining_pct"],
        native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT, icon="mdi:gauge"),
    _km("range", lambda c: c["fuel"]["range_km"], icon="mdi:map-marker-distance"),
    CarSensorDescription(
        key="consumption", translation_key="consumption", value_fn=lambda c: c["fuel"]["consumption_l_100km"],
        native_unit_of_measurement="L/100 km", state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1, icon="mdi:fuel",
        attrs_fn=lambda c: {"source": c["fuel"]["consumption_source"],
                            "mesuree": c["fuel"]["measured_l_100km"]}),
    _km("total_km", lambda c: c["km"]["total"], SensorStateClass.TOTAL_INCREASING, icon="mdi:counter",
        attrs_fn=lambda c: {"km_badges": c["km"]["tracked"], "km_sans_badge": c["km"]["untracked"]}),
    _km("untracked_km", lambda c: c["km"]["untracked"], SensorStateClass.TOTAL_INCREASING,
        icon="mdi:account-question-outline"),
    _km("odometer", lambda c: c["km"]["odometer"], SensorStateClass.TOTAL_INCREASING, icon="mdi:speedometer"),
    _km("my_km", lambda c: c["me"]["km"], SensorStateClass.TOTAL_INCREASING, icon="mdi:account-arrow-right"),
    CarSensorDescription(
        key="my_balance", translation_key="my_balance", value_fn=lambda c: _euros(c["me"]["balance_cents"]),
        device_class=SensorDeviceClass.MONETARY, native_unit_of_measurement=EUR, suggested_display_precision=2,
        attrs_fn=lambda c: {"je_dois": _transfers(c["me"]["owes"], "to"),
                            "on_me_doit": _transfers(c["me"]["owed"], "from")}),
    CarSensorDescription(
        key="settlements", translation_key="settlements", value_fn=lambda c: len(c["settlements"]),
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:swap-horizontal",
        attrs_fn=lambda c: {
            "virements": [f"{t['from']['name']} → {t['to']['name']} : {_euros(t['amount_cents']):.2f} €"
                          for t in c["settlements"]],
            "soldes": {b["name"]: _euros(b["cents"]) for b in c["balances"]},
        }),
    CarSensorDescription(
        key="last_sync", translation_key="last_sync", value_fn=lambda c: _time(c["last_sync_at"]),
        device_class=SensorDeviceClass.TIMESTAMP, icon="mdi:cloud-sync"),
    _km("last_trip", lambda c: (c["last_trip"] or {}).get("km"), icon="mdi:car-clock",
        attrs_fn=lambda c: {} if not c["last_trip"] else {
            "depart": _time(c["last_trip"]["start"]),
            "arrivee": _time(c["last_trip"]["end"]),
            "a_bord": c["last_trip"]["people"],
            "sans_badge": c["last_trip"]["type"] == "drive",
        }),
    CarSensorDescription(
        key="trips", translation_key="trips", value_fn=lambda c: c["trips_count"],
        state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:map-marker-path"),
)

ACCOUNT_SENSORS: tuple[AccountSensorDescription, ...] = (
    AccountSensorDescription(
        key="balance", translation_key="balance", value_fn=lambda d: _euros(d["totals"]["balance_cents"]),
        device_class=SensorDeviceClass.MONETARY, native_unit_of_measurement=EUR, suggested_display_precision=2,
        attrs_fn=lambda d: {
            "je_dois": [{"voiture": c["name"], **t} for c in d["cars"] for t in _transfers(c["me"]["owes"], "to")],
            "on_me_doit": [{"voiture": c["name"], **t} for c in d["cars"]
                           for t in _transfers(c["me"]["owed"], "from")],
        }),
    AccountSensorDescription(
        key="owes", translation_key="owes", value_fn=lambda d: _euros(d["totals"]["owes_cents"]),
        device_class=SensorDeviceClass.MONETARY, native_unit_of_measurement=EUR, suggested_display_precision=2),
    AccountSensorDescription(
        key="owed", translation_key="owed", value_fn=lambda d: _euros(d["totals"]["owed_cents"]),
        device_class=SensorDeviceClass.MONETARY, native_unit_of_measurement=EUR, suggested_display_precision=2),
    AccountSensorDescription(
        key="total_my_km", translation_key="total_my_km", value_fn=lambda d: d["totals"]["km"],
        device_class=SensorDeviceClass.DISTANCE, native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=0),
)


async def async_setup_entry(hass: HomeAssistant, entry: CarpoxConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities(CarpoxAccountSensor(coordinator, d) for d in ACCOUNT_SENSORS)
    known: set[str] = set()

    @callback
    def add_new_cars() -> None:
        """Une voiture ajoutée au compte plus tard apparaît sans recharger."""
        new = [c["id"] for c in coordinator.data["cars"] if c["id"] not in known]
        known.update(new)
        async_add_entities(CarpoxCarSensor(coordinator, car_id, d) for car_id in new for d in CAR_SENSORS)

    add_new_cars()
    entry.async_on_unload(coordinator.async_add_listener(add_new_cars))


class CarpoxCarSensor(CarpoxCarEntity, SensorEntity):
    entity_description: CarSensorDescription

    def __init__(self, coordinator: CarpoxCoordinator, car_id: str, description: CarSensorDescription) -> None:
        super().__init__(coordinator, car_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        car = self.car
        return None if car is None else self.entity_description.value_fn(car)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        car = self.car
        if car is None or self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(car)


class CarpoxAccountSensor(CarpoxAccountEntity, SensorEntity):
    entity_description: AccountSensorDescription

    def __init__(self, coordinator: CarpoxCoordinator, description: AccountSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
