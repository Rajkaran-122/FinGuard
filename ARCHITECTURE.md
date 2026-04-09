# Architecture & Design Decisions

This document captures the core architectural patterns and design trade-offs implemented in the FinGuard backend.

## 1. Primary Pattern: N-Tier Layering

The system enforces a strict, unidirectional flow of control to maintain a clean **Separation of Concerns (SoC)**:
`Router (API) ➔ Service (Business Logic) ➔ Repository (Data Access) ➔ Persistence`

-   **Routers (app/api/v1)**: Responsible for HTTP protocol handling, request/response validation (Pydantic), and Dependency Injection (Auth/AuthZ).
-   **Services (app/services)**: Orchestrates business workflows, manages cache-aside logic, and enforces multi-tenant scoping. Services are agnostic of the transport layer (HTTP).
-   **Repositories (app/repositories)**: Encapsulates all persistence logic. They execute parameterized queries and are decoupled from business rules or caching strategies.

*   **Trade-off**: While layering introduces boilerplate, it guarantees modularity and testability, preventing logic leakage between transport and persistence.

## 2. Data Strategy & Integrity

### Persistence Layer: PostgreSQL
Financial ecosystems demand high data integrity and consistency. PostgreSQL was chosen for its strict **ACID compliance** and advanced indexing capabilities.

-   **Precision Handling**: All monetary values use the `DECIMAL` (via SQLAlchemy `Numeric`) type rather than floating-point, ensuring precision is maintained across calculations.
-   **Schema Evolution**: Schema changes are managed via **Alembic migrations**, ensuring deterministic deployments and versioned database states.
-   **Dialect Resilience**: The use of SQLAlchemy allows the integration test suite to utilize an ephemeral `SQLite + aiosqlite` backend while the production environment leverages `PostgreSQL + asyncpg`.

### Caching Strategy: Deterministic Cache-Aside
Analytical queries (aggregates) are served via a bounded cache-aside pattern to reduce primary database load.

-   **Memory Safety**: The `CacheManager` utilizes an LRU (Least Recently Used) eviction policy with a `maxsize` bound to prevent unbounded memory growth.
-   **Consistency**: Cache invalidation is triggered synchronously within the service layer on write operations (`record_service`), ensuring that analytical dashboards reflect the latest state.
-   **Evolution Path**: The cache abstraction allows a seamless swap to a distributed **Redis** implementation without modifying business logic.

## 3. Reliability: Idempotency Gateways

To handle network unpredictability and prevent duplicate state changes (e.g., double-charging), the system implements an Idempotency layer.

-   **Request Fingerprinting**: All write operations are fingerprinted using a SHA-256 hash of the `Method + Path + UserID + Body`.
-   **Processing Flow**:
    1.  Verify if the `Idempotency-Key` exists in the persistence layer.
    2.  Check for a fingerprint match to reject replayed bodies.
    3.  Compute, store, and return the finalized response.
-   **Result**: Ensures exactly-once processing for critical financial mutations.

## 4. Observability & Traceability

Traceability is a first-class citizen in this architecture, enabling efficient debugging in production environments.

-   **Request Tracing**: Every request is assigned a unique `X-Request-ID` (UUID) via middleware. This ID is propagated to headers and embedded in every log entry.
-   **Structured Logging**: Utilizes `structlog` for machine-readable JSON logs in production, allowing for easy ingestion into log aggregation platforms (e.g., ELK, Datadog).
-   **Context Injection**: The Request ID is bound to the logging context at the start of the lifecycle, ensuring that all log lines related to a specific user action are automatically correlated.

## 5. System Lifecycle & Resource Management

The application utilizes the **Lifespan** pattern for managing the lifecycle of external resources.

-   **Connection Pooling**: Database and Redis connection pools are initialized during startup and disposed of gracefully during shutdown.
-   **Warm-up**: Dialect verification and initial connectivity checks are performed before the API begins accepting traffic, preventing "cold boot" errors during deployment.

## 6. Configuration & Environment

Settings are managed via **pydantic-settings**, providing a single source of truth for configuration.

-   **Early Failure**: All environment variables are validated at startup. If a required variable (like `DATABASE_URL` or `JWT_SECRET`) is missing or malformed, the application will fail to start, preventing "ghost" failures in production.
-   **Type Safety**: Configuration is strongly typed, reducing runtime errors related to misconfigured environment flags.
