"""Base entity for the MOVA litter box."""

from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PropertyDef
from .coordinator import MovaLitterBoxCoordinator


def category_for(definition: PropertyDef) -> EntityCategory | None:
    """Map a PropertyDef entity_category string to the HA enum."""
    if definition.entity_category == "diagnostic":
        return EntityCategory.DIAGNOSTIC
    if definition.entity_category == "config":
        return EntityCategory.CONFIG
    return None


class MovaLitterBoxEntity(CoordinatorEntity[MovaLitterBoxCoordinator]):
    """Common device info / availability for all litter box entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MovaLitterBoxCoordinator) -> None:
        super().__init__(coordinator)
        record = coordinator.device_record or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.did)},
            name=record.get("customName") or "MOVA Litter Box",
            manufacturer="MOVA",
            model=coordinator.model,
            sw_version=(record.get("ver") or record.get("firmwareVersion")),
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.device_online
