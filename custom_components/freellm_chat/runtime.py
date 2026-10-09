"""Typed runtime data for FreeLLM Chat."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .api import LLM7Client
from .model_manager import ModelManager
from .usage_manager import UsageManager


@dataclass(slots=True)
class FreeLLMRuntimeData:
    """Objects that exist only while one config entry is loaded."""

    client: LLM7Client
    model_manager: ModelManager
    usage_manager: UsageManager


# Home Assistant 2026.x supports typed ConfigEntry.runtime_data.
type FreeLLMConfigEntry = ConfigEntry[FreeLLMRuntimeData]
