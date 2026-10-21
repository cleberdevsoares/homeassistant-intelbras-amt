"""Config flow for Intelbras AMT (cloud)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_ID,
    CONF_MAC,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    DEFAULT_MODEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MIN_SCAN_INTERVAL,
    MODELS,
)
from .protocol import (
    AmtAuthError,
    AmtBusyError,
    AmtCloudClient,
    AmtConnectionError,
    AmtModelError,
    AmtPanelOfflineError,
    normalize_mac,
)

PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): str,
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
        vol.Required(CONF_MODEL, default=DEFAULT_MODEL): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(MODELS),
                translation_key=CONF_MODEL,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


async def _validate(mac: str, password: str, model: str, device_id: str) -> str | None:
    client = AmtCloudClient(mac, password, MODELS[model], device_id)
    try:
        await client.async_status()
    except AmtAuthError:
        return "invalid_auth"
    except AmtPanelOfflineError:
        return "panel_offline"
    except AmtBusyError:
        return "panel_busy"
    except AmtModelError:
        return "wrong_model"
    except AmtConnectionError as err:
        LOGGER.warning("Falha ao validar central Intelbras: %s", err)
        return "cannot_connect"
    finally:
        await client.async_close()
    return None


class AmtOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class AmtConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AmtOptionsFlow:
        return AmtOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                mac = normalize_mac(user_input[CONF_MAC])
            except ValueError:
                errors[CONF_MAC] = "invalid_mac"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                device_id = uuid.uuid4().hex[:16]
                password = user_input[CONF_PASSWORD].strip()
                error = await _validate(mac, password, user_input[CONF_MODEL], device_id)
                if error:
                    errors["base"] = error
                else:
                    return self.async_create_entry(
                        title=f"Central {MODELS[user_input[CONF_MODEL]].name}",
                        data={
                            CONF_MAC: mac,
                            CONF_PASSWORD: password,
                            CONF_MODEL: user_input[CONF_MODEL],
                            CONF_DEVICE_ID: device_id,
                        },
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input or {}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            password = user_input[CONF_PASSWORD].strip()
            error = await _validate(
                entry.data[CONF_MAC], password, entry.data[CONF_MODEL], entry.data[CONF_DEVICE_ID]
            )
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: password})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders={"mac": entry.data[CONF_MAC]},
            errors=errors,
        )
