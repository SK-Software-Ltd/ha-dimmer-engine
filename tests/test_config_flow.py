from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sksoft_dimmer_engine.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result.get("errors") in (None, {})

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "SKSoft Dimmer Engine"
    assert result2["data"] == {}


async def test_user_flow_aborts_when_already_configured(hass: HomeAssistant) -> None:
    existing = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={})
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_second_setup_aborts(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result2["type"] is FlowResultType.ABORT
