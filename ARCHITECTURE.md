# Architecture Decisions

This document captures the core architectural design and trade-offs for the FinGuard backend.

## 1. Core Architecture Pattern: Layered (N-Tier)

The project enforces a strict, unidirectional flow of control:
`Router ➔ Service ➔ Repository ➔ ORM/Database`

- **Routers**: Handle HTTP, request validation (Pydantic), and Dependency Injection for authentication/authorization.
- **Services**: House pure business logic, orchestrate cache invalidations, and enforce data scope (multi-tenancy) so business rules are separated from transport rules.
- **Repositories**: Handle all SQLAlchemy queries. They do not know about HTTP, caches, or users — they execute parameterized SQL.

*Trade-off*: Adds some boilerplate (passing data between layers), but guarantees testability and prevents "God controllers".

## 2. Database Choice: PostgreSQL

We chose PostgreSQL as the primary persistence layer over simpler alternatives like SQLite or managed multi-model NoSQL databases.

- **Reasoning**: Financial systems demand absolute consistency. PostgreSQL guarantees robust ACID compliance and handles complex aggregations (needed for the dashboard) exceptionally well.
- **Why not MongoDB**: Relational data (users own records, records belong to categories) queried strictly through tabular aggregates is perfectly suited for SQL. NoSQL would force fragile application-side joins for our dashboard metrics.
- **Local Dev / Testing**: SQLAlchemy abstracts the dialect perfectly, allowing us to drop to an in-memory SQLite database solely for lightning-fast test execution while deploying to a robust PostgreSQL setup in production.

## 3. Caching Strategy: Bounded Cache-Aside

Analytics queries run `COUNT()`, `SUM()`, and `GROUP BY` across thousands of records. Computing these per-request at scale would exhaust database CPU.

- **Implementation**: Bounded in-memory Cache-Aside pattern.
- **Flow**: Dashboard reads hit the cache dict. On miss, it calculates from DB and stores with a TTL. Any write operation in the record service invalidates the specific user's dashboard cache prefixes.
- **Evolution**: The `CacheManager` exposes a standard `.get()`, `.set()`, and `.invalidate_prefix()` API. Migrating to Redis in a distributed environment requires modifying exactly one class under `app/core/cache.py`, with zero changes to business logic.
- **Safety**: Bounded via LRU (maxsize) to prevent unbounded memory growth at 100k+ users.

## 4. Idempotency Gateways

Financial APIs cannot tolerate network-retry "double-spend" errors. The API handles network unpredictability using Idempotency Keys.

- **How it works**: Client sends an `Idempotency-Key` header with their POST payload.
- **Protection Flow**:
  1. Check fast in-memory cache for computed response.
  2. Check persistent DB layer for survivability across restarts.
  3. Attempt lock acquisition via 'pending' status row insertion.
  4. Compare a SHA-256 fingerprint of `method + path + user_id + body` to reject modified retries.
  5. Compute, persist 'completed' status, and return.

## 5. Security & RBAC Middleware

- **Role Base**: Roles (admin, analyst, viewer) map to granular permission arrays.
- **IDOR Protection**: The system universally prevents Insecure Direct Object Reference by centralizing data scoping. Endpoints query records by injecting a `user_id` scope from `get_data_scope()`. If an unauthorized viewer requests an existing admin record by UUID, the repository naturally returns `None`, and the API produces a 404 Not Found rather than a 403 Forbidden, concealing the record's existence.
