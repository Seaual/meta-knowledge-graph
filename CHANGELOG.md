# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1] - 2026-04-25

### Added

- Added `conversationId` support to agent chat requests so LangGraph sessions can be isolated per conversation.
- Added a shared resilience helper for retry-aware external calls with structured logging.
- Added regression tests for retry behavior and LLM wrapper failures.
- Added a release summary section to `README.md`.

### Changed

- Reworked concept persistence to batch inserts and relation writes in a single database transaction.
- Updated graph rendering so the Concepts page refreshes one ForceGraph instance instead of rebuilding it on routine UI state changes.
- Switched chat graph rendering to true lazy loading and simplified the related API import path.
- Enabled Vite vendor chunk splitting via `splitVendorChunkPlugin()`.

### Verification

- `python -m compileall backend mkg tests`
- `npm run typecheck`
- `npm run build`

### Known Gaps

- Python tests were added but not executed in this environment because `pytest` is not installed.
- Frontend production build still reports a large vendor chunk warning.
