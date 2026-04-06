# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Security**: Hardened user registration module to universally assign the `viewer` role to all public signups, removing a critical privilege escalation vector.
- **Cache Bounds**: `CacheManager` now enforces an LRU memory limit (`maxsize=10,000`) preventing memory starvation at scale.
- **Idempotency Locks**: Introduced atomic `pending` state locking to the `IdempotencyManager` handling flow. Mitigates duplicate transaction processing during concurrent requests with identical fingerprint payloads.
- **Observability**: Expose detailed cache hit/miss/size metrics on the generic `/health` endpoint.
- **Unit Tests**: comprehensive isolation tests for `cache`, `scope`, `idempotency`, and `security` components achieving critical pathway coverage.

### Changed
- **Architectural Documentation**: Aligned `ARCHITECTURE.md` and `BRD.md` to reflect PostgreSQL as the definitive production dialect, transitioning SQLite exclusively toward internal test tooling paradigms.
- **Cache Invalidation Coupling**: Transitioned Cache-Aside invalidation directives fully onto the Service Layer boundary (`record_service.py`), restoring pure database abstraction to the repository layer.
- **Ownership Scope Module**: Abstracted previously duplicated multi-tenancy filtering routines into a centralized configurable provider (`core/scope.py`).
- **Telemetry Health Checks**: Refactored the core readiness probe to execute active database connection pings rather than hardcoded string responses.

### Removed
- **Redundant Components**: Eliminated the bespoke `IdempotencyEngine` via consolidation with the newly robust global `cache_service` singleton.
- **Meta-files**: Dropped out-of-band project planning documentation prioritizing standard repository documentation layouts.

## [1.0.0] - 2026-04-04
### Added
- Initial project release with Authentication, Role-Based Access Control, Idempotency tracking, and Cache-Aside analytical endpoints.
