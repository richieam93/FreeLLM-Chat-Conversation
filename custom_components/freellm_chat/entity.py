"""Shared entity helpers for FreeLLM Chat."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PROJECT_URL


def service_device_info(entry: ConfigEntry) -> dr.DeviceInfo:
    """Return the shared service device information."""
    return dr.DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="richieam93",
        model="FreeLLM Chat for LLM7.io",
        entry_type=dr.DeviceEntryType.SERVICE,
        configuration_url=PROJECT_URL,
    )
