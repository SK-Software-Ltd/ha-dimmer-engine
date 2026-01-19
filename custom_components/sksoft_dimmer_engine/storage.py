"""Storage helper for SKSoft Dimmer Engine integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_KEY_CCW, STORAGE_VERSION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)


class DimmerEngineStore:
    """Class to manage persistent storage for the dimmer engine registry."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY
        )

    async def async_load(self) -> dict[str, Any]:
        """Load the registry from storage."""
        data = await self._store.async_load()
        if data is None:
            return {}
        return data

    async def async_save(self, data: dict[str, Any]) -> None:
        """Save the registry to storage."""
        await self._store.async_save(data)

    async def async_remove(self) -> None:
        """Remove the storage file."""
        await self._store.async_remove()


class CCWCycleStore:
    """Class to manage persistent storage for the CCW (Correlated Color Temperature) cycle registry."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_CCW
        )

    async def async_load(self) -> dict[str, Any]:
        """Load the registry from storage."""
        data = await self._store.async_load()
        if data is None:
            return {}
        return data

    async def async_save(self, data: dict[str, Any]) -> None:
        """Save the registry to storage."""
        await self._store.async_save(data)

    async def async_remove(self) -> None:
        """Remove the storage file."""
        await self._store.async_remove()
