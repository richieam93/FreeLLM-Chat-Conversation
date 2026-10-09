"""Shared entity helpers for FreeLLM Chat."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr

from .const import CONF_PROVIDER, DOMAIN, INTEGRATION_VERSION, PROJECT_URL
from .provider import normalize_provider, provider_name
from .runtime import FreeLLMConfigEntry


def service_device_info(entry: FreeLLMConfigEntry) -> dr.DeviceInfo:
    """Return the shared service device information."""
    return dr.DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="richieam93",
        model=f"FreeLLM Chat for {provider_name(normalize_provider(entry.data.get(CONF_PROVIDER)))}",
        entry_type=dr.DeviceEntryType.SERVICE,
        configuration_url=PROJECT_URL,
        sw_version=INTEGRATION_VERSION,
    )
