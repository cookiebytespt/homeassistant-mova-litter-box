"""Number entities for the MOVA litter box."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MovaConfigEntry
from .const import PROPERTIES, PropertyDef
from .coordinator import MovaLitterBoxCoordinator
from .entity import MovaLitterBoxEntity, category_for


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MovaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        MovaPropertyNumber(coordinator, definition)
        for definition in PROPERTIES
        if definition.kind == "number"
    )


class MovaPropertyNumber(MovaLitterBoxEntity, NumberEntity):
    """A writable numeric property."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self, coordinator: MovaLitterBoxCoordinator, definition: PropertyDef
    ) -> None:
        super().__init__(coordinator)
        self._definition = definition
        self._attr_unique_id = f"{coordinator.did}-{definition.key}"
        self._attr_translation_key = definition.key
        self._attr_icon = definition.icon
        self._attr_native_unit_of_measurement = definition.unit
        self._attr_entity_category = category_for(definition)
        self._attr_entity_registry_enabled_default = definition.confirmed
        if definition.min_value is not None:
            self._attr_native_min_value = definition.min_value
        if definition.max_value is not None:
            self._attr_native_max_value = definition.max_value
        if definition.step is not None:
            self._attr_native_step = definition.step

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.get_property(
            self._definition.siid, self._definition.piid
        )
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_property(
            self._definition.siid,
            self._definition.piid,
            int(value) if float(value).is_integer() else value,
        )
