"""Sensors for Intelbras AMT (cloud)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AmtConfigEntry
from .entity import AmtEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AmtConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AmtFirmware(entry.runtime_data, "firmware")])


class AmtFirmware(AmtEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.firmware if self.coordinator.data else None
