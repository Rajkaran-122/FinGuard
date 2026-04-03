# FinGuard — System Design and Architectural Guide

This document captures the system design thinking behind the FinGuard API. It outlines architectural decisions, trade-offs, and production scaling strategies suitable for technical evaluation.

---

## 1. System Behavior Under Load (100K Users / 1M Records)

### Bottleneck Analysis
| Component | Bottleneck | Mitigation Strategy (Implemented) |
|-----------|-----------|----------------------------------|
| `COUNT(*)` on records list | Full table scan at 1M+ rows | Cursor-based pagination avoids OFFSET; COUNT is bounded by ownership filter |
| Dashboard aggregations | CPU-heavy `SUM/GROUP BY` on every request | Cache-aside pattern with 1-hour TTL limits repeated database queries |
| JWT validation | DB round-trip on every request to re-fetch user | Acceptable at current scale; at 100K RPS would add Redis session cache |
| Cache memory | Unbounded growth of cache keys | TTL-based expiration and prefix invalidation maintain bounded memory constraints |

### Scaling Strategies
- **Database**: Add read replicas; route aggregation queries to read-only replicas.
- **Cache**: Transition in-memory dictionary to a Redis cluster. The API exposes standard `.get`/`.set`/`.invalidate_prefix` methods requiring zero changes to the service layer.
- **Async Processing**: Offload cache invalidation to a background task queue (e.g., Celery or ARQ) to prevent write operations from blocking on cache purging.

---

## 2. Failure Handling Strategy

### Cache Inconsistency
**Scenario**: An administrator creates a record, but cache invalidation fails mid-operation.
**Current Design**: Cache invalidation runs synchronously after `db.commit()`. If the process crashes between commit and invalidation, the client interfaces with stale data until the TTL expires (1 hour maximum).
**Production Solution**: Utilize database-level notifications (e.g., PostgreSQL `LISTEN/NOTIFY`) to trigger cache invalidation asynchronously, guaranteeing delivery across process restarts.

### Duplicate Write Protection
**Scenario**: A network timeout induces a client to retry a `POST /api/records/` request.
**Current Design**: The `Idempotency-Key` header stores the initial response. Retries with the identical key return the cached response without creating duplicate database entries.
**Significance**: Duplicate financial records corrupt dashboard analytics and audit trails.

### Database Connection Exhaustion
**Scenario**: 1000 concurrent requests exhaust the connection pool.
**Current Design**: The SQLAlchemy session factory with the `yield` keyword ensures connections consistently return logic to the pool, even during exception handling.
**Production Solution**: Explicitly configure `pool_size`, `max_overflow`, and `pool_timeout` in the SQLAlchemy engine, and integrate connection health checks.

### Concurrent Update Conflicts
**Scenario**: Two administrators attempt to update the same record simultaneously.
**Current Design**: SQLAlchemy's unit-of-work pattern resolves basic write conflicts. The immutable audit log captures both transaction versions sequentially.
**Production Solution**: Implement optimistic locking via an incremental `version` column: `UPDATE ... WHERE id = ? AND version = ?`.

---

## 3. Trade-offs and Architecture Rationale

### Database Selection: PostgreSQL vs SQLite/MongoDB
| Specification | PostgreSQL | SQLite | MongoDB |
|---------------|-----------|--------|---------|
| ACID Transactions | Full guarantee | WAL mode limits concurrency | Eventual consistency limits financial safety |
| Concurrent Writes | Row-level locks | File-level locks | Document-level locks |
| Aggregation Performance | Robust query planner + indexes | Limited optimizer engine | Lacks complex JOIN operations |
| Schema Evolution | Alembic migrations | Manual table alterations | Schemaless design risks data corruption |
| **Rationale**: Financial data necessitates strict ACID guarantees. PostgreSQL's query planner automatically optimizes the `SUM/GROUP BY` aggregations using defined composite indexes. |

### Caching Strategy: Synchronous vs Asynchronous Queue
- **Scope Alignment**: Implementing RabbitMQ or Redis Streams would introduce infrastructural complexity disproportionate to the backend assignment parameters limit.
- **The Cache-Aside Pattern**: The internal dictionary object adheres to the exact method signature of a Redis client. Migrating to Redis requires modifying a single module (`cache.py`) without disrupting the service layer.
- **Bounded Risk**: Time-to-Live (TTL) parameters guarantee that stale data self-corrects within an hour even under worst-case invalidation failure events.

### Authorization: Permission Arrays vs Role Enums
- **Legacy Design**: Explicit procedural checks (`if user.role == "admin"`) require extensive refactoring to support new roles.
- **Current Design**: Granular capabilities checks (`if "records:write" in user.permissions`). Adding a new functional role (e.g., "Auditor") only requires seeding a specific array (`["records:read", "dashboard:view"]`) with no codebase alterations.
- **Authentication Model**: This reflects AWS IAM policy architectures where functional permissions attach directly to active principals.

---

## 4. Security Framework

### Horizontal Privilege Escalation Protection (IDOR)
**Vulnerability**: A user attempts to manipulate a URL parameter to access another user's record (`GET /api/records/{uuid}`).
**Resolution**: All database queries resolve sequentially through the ownership scope filter `_active_records(db, user_id=scope)`. Standard users only access data where `created_by == their_id`. Unauthorized operations return HTTP 404 (Not Found) rather than 403 (Forbidden) to prevent an attacker from inferring record existence boundaries.

### Cryptographic and Identity Safety
- The `password_hash` column is explicitly omitted from the `UserResponse` serialization payload.
- Pydantic V2 strictly enforces `from_attributes` mode, serializing only explicitly declared properties mapping from the ORM.
- The schema isolates the internal SQLAlchemy models, acting as a structural firewall against accidental data exposure.

### Input Validation Constraints
| Layer | Verification Scope | Implementation Example |
|-------|-------------------|----------------------|
| Pydantic Schema | Type mismatches, explicit range limitations | `amount: Decimal = Field(..., gt=0)` |
| SQLAlchemy Enum | Domain-specific structural types | `RecordType("invalid")` raises intrinsic ValueError |
| Database Constraints | Reference validation, NULL states | `nullable=False`, `ondelete="CASCADE"` |

---

## 5. Architectural Flow Examples

### Request Lifecycle Trace
1. The client issues `POST /api/records/` including a Bearer JWT.
2. The middleware extracts the component → `get_current_user` decodes the JWT, queries the database, and validates the `is_active` boolean state.
3. The `require_permissions("records:write")` dependency cross-references the requested action against the user's JSON capabilities array.
4. Pydantic V2 parses the incoming request body according to the `RecordCreate` definitions (enforcing positive integers and regex matching).
5. The API Router delegates the validated parameters into `record_service.create_record()`.
6. The Service layer resolves ownership constraints and triggers `record_repository.create_record()`.
7. The Repository layer persists the transaction into PostgreSQL and issues an invalidation command against all `dashboard_*` cache stores.
8. The Service layer structures the standardized `ResponseWrapper`, omitting confidential internal model properties via the Pydantic boundary model.

### Outage Handling and Post-Mortem Strategy
1. A continuous `/health` endpoint exposes real-time database connection statuses to enable load-balancer traffic diversion from degraded instances.
2. A structured JSON logger injects a unique trace component (`request_id`) across all functional lines to trace complex distributed errors.
3. The global application architecture handles unhandled exceptions (Code 500) natively, outputting sanitized JSON schema structures without leaking interpreter stack traces.
4. The immutable audit log preserves exact representations of historical values, enabling structural reconstruction of data following accidental administrator corruption events.
