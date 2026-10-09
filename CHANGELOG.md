# Changelog

## 3.8.1 - 2026-10-02

- Fixed startup failure when upgrading an existing installation whose model cache was written with storage version 3.
- Added explicit Home Assistant `Store` migration for model-cache versions 1-3 to the multi-provider cache schema.
- Legacy cache entries are tagged as LLM7, preventing accidental reuse when OVHcloud is selected.
- No manual `.storage` deletion is required.

## 3.8.0 - 2026-10-02

- Added selectable multi-provider support for LLM7.io and OVHcloud AI Endpoints.
- Added separate stored credentials for LLM7 and OVHcloud; only the active provider credential is transmitted.
- Added bundled OVHcloud `gpt-oss-20b` and `gpt-oss-120b` model metadata with tool-calling, streaming, reasoning, JSON, and 131k-context capabilities.
- Added provider-specific endpoints, anonymous/authenticated request pacing, provider URLs, diagnostics, and reference limits.
- Added config-entry migration to version 7; existing installations remain on LLM7 by default.
- Provider switching now repairs incompatible model/fallback selections automatically.
- Retains 3.7 token-saving mode and local Home Assistant intent routing for simple device commands.
- Requires Home Assistant 2026.9.0 or newer.

## 3.7.0

- Added token-saving context mode and prompt-size telemetry.
- Added local Home Assistant intent routing for simple device commands before external LLM calls.

## 3.6.3

- Added request pacing to avoid provider per-second limits during multi-step tool calls.

## 3.6.2

- Improved HTTP 429 handling and Retry-After reporting.

## 3.6.1

- Added transient provider/model failover inside a single provider.

## 3.6.0

- Migrated runtime state to ConfigEntry.runtime_data and Home Assistant 2026.9 / probatio OpenAPI schema conversion.
