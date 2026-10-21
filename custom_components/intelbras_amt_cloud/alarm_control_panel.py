"""Alarm panels for Intelbras AMT (cloud)."""

from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AmtConfigEntry
from .const import PARTITIONS
from .coordinator import AmtCoordinator
from .entity import AmtEntity
from .protocol import arm_command, disarm_command


async def async_setup_entry(
    hass: HomeAssistant, entry: AmtConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    if coordinator.data.partitioned:
        count = len(coordinator.client.model.armed)
        async_add_entities(AmtAlarmPanel(coordinator, p) for p in PARTITIONS[:count])
    else:
        async_add_entities([AmtAlarmPanel(coordinator, None)])


class AmtAlarmPanel(AmtEntity, AlarmControlPanelEntity):
    _attr_code_arm_required = False

    def __init__(self, coordinator: AmtCoordinator, partition: str | None) -> None:
        super().__init__(coordinator, f"alarm_{partition.lower()}" if partition else "alarm")
        self.partition = partition
        if partition:
            self._attr_translation_key = "partition"
            self._attr_translation_placeholders = {"partition": partition}
        else:
            self._attr_translation_key = "panel"
        features = AlarmControlPanelEntityFeature.ARM_AWAY
        if coordinator.client.model.stay:
            features |= AlarmControlPanelEntityFeature.ARM_HOME
        self._attr_supported_features = features

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        data = self.coordinator.data
        if data is None:
            return None
        if self.partition:
            armed = data.armed.get(self.partition, False)
            stay = data.stay.get(self.partition, False)
        else:
            armed = data.any_armed
            stay = any(data.stay.values())
        if data.siren and armed:
            return AlarmControlPanelState.TRIGGERED
        if armed and stay:
            return AlarmControlPanelState.ARMED_HOME
        if armed:
            return AlarmControlPanelState.ARMED_AWAY
        return AlarmControlPanelState.DISARMED

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self.coordinator.async_command(arm_command(self.partition))

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self.coordinator.async_command(arm_command(self.partition, stay=True))

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self.coordinator.async_command(disarm_command(self.partition, self.coordinator.client.model))
