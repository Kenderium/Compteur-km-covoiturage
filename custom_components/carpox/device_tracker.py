"""Dernière position connue de chaque voiture (fin du dernier parcours GPS).

Pas de suivi en direct : le boîtier n'envoie ses trajets qu'en arrivant sur
un WiFi connu. La position est celle de la fin du dernier trajet reçu.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CarpoxConfigEntry
from .entity import CarpoxCarEntity
from .sensor import _time


async def async_setup_entry(hass: HomeAssistant, entry: CarpoxConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def add_new_cars() -> None:
        new = [c["id"] for c in coordinator.data["cars"] if c["id"] not in known]
        known.update(new)
        async_add_entities(CarpoxTracker(coordinator, car_id) for car_id in new)

    add_new_cars()
    entry.async_on_unload(coordinator.async_add_listener(add_new_cars))


class CarpoxTracker(CarpoxCarEntity, TrackerEntity):
    _attr_translation_key = "position"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator, car_id: str) -> None:
        super().__init__(coordinator, car_id, "position")

    @property
    def _position(self) -> dict[str, Any] | None:
        car = self.car
        return None if car is None else car.get("last_position")

    @property
    def latitude(self) -> float | None:
        pos = self._position
        return None if pos is None else pos["lat"]

    @property
    def longitude(self) -> float | None:
        pos = self._position
        return None if pos is None else pos["lon"]

    @property
    def location_accuracy(self) -> float:
        return 20

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        pos = self._position
        return None if pos is None else {"releve_le": _time(pos["at"])}
