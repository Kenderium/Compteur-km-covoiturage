"""Entités de base : un appareil par voiture, un appareil pour le compte."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CarpoxCoordinator


def _uid_prefix(coordinator: CarpoxCoordinator) -> str:
    return coordinator.config_entry.unique_id or coordinator.config_entry.entry_id


class CarpoxCarEntity(CoordinatorEntity[CarpoxCoordinator]):
    """Entité liée à une voiture. Chaque compte a ses propres appareils :
    deux comptes dans le même Home Assistant ne se mélangent pas."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CarpoxCoordinator, car_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.car_id = car_id
        car = coordinator.car(car_id) or {}
        prefix = _uid_prefix(coordinator)
        self._attr_unique_id = f"{prefix}_{car_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{prefix}_{car_id}")},
            name=car.get("name", car_id),
            manufacturer="CarpoX",
            model="Boîtier Pico W",
            configuration_url=f"{coordinator.client.url}/#car/{car_id}",
        )

    @property
    def car(self) -> dict[str, Any] | None:
        return self.coordinator.car(self.car_id)

    @property
    def available(self) -> bool:
        return super().available and self.car is not None


class CarpoxAccountEntity(CoordinatorEntity[CarpoxCoordinator]):
    """Entité du compte : totaux sur toutes les voitures."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CarpoxCoordinator, key: str) -> None:
        super().__init__(coordinator)
        prefix = _uid_prefix(coordinator)
        user = coordinator.user
        self._attr_unique_id = f"{prefix}_account_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{prefix}_account")},
            name=f"CarpoX {user['display_name']}",
            manufacturer="CarpoX",
            model="Compte",
            configuration_url=f"{coordinator.client.url}/#account",
            entry_type=DeviceEntryType.SERVICE,
        )
