"""Binary sensors for Intelbras AMT (cloud)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AmtConfigEntry
from .entity import AmtEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AmtConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([AmtSiren(coordinator, "siren"), AmtConnected(coordinator, "connected")])


class AmtSiren(AmtEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.siren if self.coordinator.data else None


class AmtConnected(AmtEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success
