"""Intelbras AMT (cloud) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID, CONF_MAC, CONF_MODEL, MODELS, PLATFORMS
from .coordinator import AmtCoordinator
from .protocol import AmtCloudClient

type AmtConfigEntry = ConfigEntry[AmtCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AmtConfigEntry) -> bool:
    client = AmtCloudClient(
        entry.data[CONF_MAC],
        entry.data[CONF_PASSWORD],
        MODELS[entry.data[CONF_MODEL]],
        entry.data[CONF_DEVICE_ID],
    )
    coordinator = AmtCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_shutdown)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: AmtConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AmtConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
