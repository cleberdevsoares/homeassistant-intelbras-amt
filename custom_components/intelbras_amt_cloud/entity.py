"""Base entity for Intelbras AMT (cloud)."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AmtCoordinator


class AmtEntity(CoordinatorEntity[AmtCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AmtCoordinator, key: str) -> None:
        super().__init__(coordinator)
        client = coordinator.client
        self._attr_unique_id = f"{client.mac}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, client.mac)},
            connections={(CONNECTION_NETWORK_MAC, client.mac.lower())},
            name=f"Central {client.model.name}",
            manufacturer=MANUFACTURER,
            model=client.model.name,
            sw_version=str(coordinator.data.firmware) if coordinator.data else None,
        )
