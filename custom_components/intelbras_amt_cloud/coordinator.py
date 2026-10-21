"""Polling coordinator for Intelbras AMT (cloud)."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER
from .protocol import AmtAuthError, AmtCloudClient, AmtError, PanelStatus


class AmtCoordinator(DataUpdateCoordinator[PanelStatus]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: AmtCloudClient) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client

    async def _async_update_data(self) -> PanelStatus:
        try:
            return await self.client.async_status()
        except AmtAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AmtError as err:
            raise UpdateFailed(str(err)) from err

    async def async_command(self, cmd: list[int]) -> None:
        try:
            await self.client.async_send(cmd)
        except AmtAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(str(err)) from err
        except AmtError as err:
            LOGGER.error("Falha ao enviar comando para a central: %s", err)
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        await super().async_shutdown()
        await self.client.async_close()
