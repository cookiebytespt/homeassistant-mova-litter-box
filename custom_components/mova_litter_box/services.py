"""Home Assistant services for the MOVA litter box.

These are generic, low-level control services so a user can trigger or probe
any device action / property from Home Assistant while the action (aiid) map
is still being confirmed on real hardware:

  * ``mova_litter_box.send_action``  -> raw MIOT action (siid/aiid/params)
  * ``mova_litter_box.set_property`` -> raw MIOT property write (siid/piid/value)
  * ``mova_litter_box.refresh``      -> force a coordinator data refresh

All three resolve the target coordinator from the loaded config entries and
delegate to the coordinator helpers (async_call_action / async_set_property /
async_request_refresh).
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import MovaLitterBoxCoordinator

ATTR_ENTRY_ID = "entry_id"
ATTR_SIID = "siid"
ATTR_AIID = "aiid"
ATTR_PIID = "piid"
ATTR_PARAMS = "params"
ATTR_VALUE = "value"

SERVICE_SEND_ACTION = "send_action"
SERVICE_SET_PROPERTY = "set_property"
SERVICE_REFRESH = "refresh"

_SERVICES_REGISTERED = "__services_registered"

SEND_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SIID): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_AIID): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional(ATTR_PARAMS, default=list): vol.All(
            cv.ensure_list, [dict]
        ),
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)

SET_PROPERTY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SIID): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_PIID): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_VALUE): object,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)

REFRESH_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)


def _loaded_coordinators(hass: HomeAssistant) -> list[MovaLitterBoxCoordinator]:
    """Return the coordinators of every loaded MOVA litter box entry."""
    coordinators: list[MovaLitterBoxCoordinator] = []
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if isinstance(coordinator, MovaLitterBoxCoordinator):
            coordinators.append(coordinator)
    return coordinators


def _coordinator_from_call(
    hass: HomeAssistant, call: ServiceCall
) -> MovaLitterBoxCoordinator:
    """Resolve the coordinator targeted by a service call."""
    entry_id = call.data.get(ATTR_ENTRY_ID)
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        coordinator = getattr(entry, "runtime_data", None) if entry else None
        if isinstance(coordinator, MovaLitterBoxCoordinator):
            return coordinator
        raise HomeAssistantError(
            f"No loaded MOVA litter box entry found for {entry_id}."
        )

    coordinators = _loaded_coordinators(hass)
    if len(coordinators) == 1:
        return coordinators[0]
    if not coordinators:
        raise HomeAssistantError("No MOVA litter box entries are loaded.")
    raise HomeAssistantError(
        "Multiple MOVA litter box entries are loaded; pass entry_id."
    )


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register the domain services once for the whole integration."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_SERVICES_REGISTERED):
        return

    async def async_handle_send_action(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        params: list[Any] = list(call.data.get(ATTR_PARAMS) or [])
        await coordinator.async_call_action(
            call.data[ATTR_SIID],
            call.data[ATTR_AIID],
            params,
        )

    async def async_handle_set_property(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await coordinator.async_set_property(
            call.data[ATTR_SIID],
            call.data[ATTR_PIID],
            call.data[ATTR_VALUE],
        )

    async def async_handle_refresh(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_ACTION,
        async_handle_send_action,
        schema=SEND_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PROPERTY,
        async_handle_set_property,
        schema=SET_PROPERTY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        async_handle_refresh,
        schema=REFRESH_SCHEMA,
    )
    domain_data[_SERVICES_REGISTERED] = True


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove the domain services when the last entry unloads."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data.get(_SERVICES_REGISTERED):
        return
    hass.services.async_remove(DOMAIN, SERVICE_SEND_ACTION)
    hass.services.async_remove(DOMAIN, SERVICE_SET_PROPERTY)
    hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    domain_data.pop(_SERVICES_REGISTERED, None)
