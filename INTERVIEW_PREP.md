# FinGuard — Senior Engineering Interview Preparation Guide

This document captures the **system design thinking** behind FinGuard. Use it to confidently explain architectural decisions, trade-offs, and production scaling strategies during technical interviews.

---

## 1. System Behavior Under Load (100K Users / 1M Records)

### What Breaks First
| Component | Bottleneck | Mitigation (Already Implemented) |
|-----------|-----------|----------------------------------|
| `COUNT(*)` on records list | Full table scan at 1M+ rows | Cursor-based pagination avoids OFFSET; COUNT is bounded by ownership filter |
| Dashboard aggregations | CPU-heavy `SUM/GROUP BY` on every request | Cache-aside pattern with 1-hour TTL eliminates repeated DB hits |
| JWT validation | DB round-trip on every request to re-fetch user | Acceptable at this scale; at 100K RPS would add Redis session cache |
| Cache memory | Unbounded growth of cache keys | TTL-based expiration + prefix invalidation keeps memory bounded |

### What I Would Change at Scale
- **Database**: Add read replicas; route aggregation queries to replicas
- **Cache**: Swap in-memory `dict` for Redis cluster (zero code changes — same `.get/.set/.invalidate_prefix` API)
- **Async Processing**: Move cache invalidation to a background task queue (Celery/ARQ) so writes don't block on cache purging

---

## 2. Failure Handling Strategy

### Cache Inconsistency
**Scenario**: Admin creates a record, cache invalidation fails mid-operation.
**Current Design**: Cache invalidation runs synchronously *after* `db.commit()`. If the process crashes between commit and invalidation, client sees stale data until TTL expires (1 hour max).
**Production Fix**: Use database-level `LISTEN/NOTIFY` (PostgreSQL) to trigger cache invalidation, guaranteeing delivery even across process restarts.

### Duplicate Write Protection
**Scenario**: Network timeout causes client to retry a `POST /api/records/` request.
**Current Design**: `Idempotency-Key` header stores the first response. Retries with the same key return the cached response without creating duplicates.
**Why This Matters in Finance**: A duplicate $50,000 income record would corrupt all dashboard analytics and audit trails.

### Database Connection Exhaustion
**Scenario**: 1000 concurrent requests exhaust the connection pool.
**Current Design**: SQLAlchemy session factory with `yield` ensures connections are always returned to the pool, even on exceptions.
**Production Fix**: Configure `pool_size`, `max_overflow`, and `pool_timeout` in SQLAlchemy engine. Add connection health checks.

### Race Conditions on Update
**Scenario**: Two admins update the same record simultaneously.
**Current Design**: SQLAlchemy's unit-of-work pattern handles basic conflicts. The immutable audit log captures both versions.
**Production Fix**: Add optimistic locking with a `version` column: `UPDATE ... WHERE id = ? AND version = ?`.

---

## 3. Trade-offs Explained

### Why PostgreSQL (Not SQLite/MongoDB)
| Factor | PostgreSQL | SQLite | MongoDB |
|--------|-----------|--------|---------|
| ACID Transactions | ✅ Full | ✅ WAL mode | ❌ Eventually consistent |
| Concurrent Writes | ✅ Row-level locks | ❌ File-level locks | ✅ Document-level |
| Aggregation Performance | ✅ Query planner + indexes | ⚠️ Limited optimizer | ❌ No JOINs |
| Schema Evolution | ✅ Alembic migrations | ❌ Manual | ⚠️ Schemaless = risky |
| **Why I chose it**: Financial data demands ACID guarantees. A corrupted transaction record is unacceptable. PostgreSQL's query planner also optimizes our `SUM/GROUP BY` aggregations automatically using the composite indexes I defined. |

### Why Sync Cache Invalidation (Not Async Queue)
- **Assignment Scope**: Adding RabbitMQ/Redis Streams would demonstrate infrastructure setup, not backend thinking
- **The Cache-Aside Pattern**: The internal `dict` with `.get/.set/.invalidate_prefix` methods has the *identical API surface* as a Redis client. Swapping to Redis requires changing one file (`cache.py`), zero service layer changes
- **Bounded Risk**: TTL ensures stale data self-corrects within 1 hour maximum, even if edge-case invalidation failures occur

### Why Permission Arrays (Not Role Enums)
- **Old Design**: `if user.role == "admin"` — adding a new role requires modifying every check point
- **Current Design**: `if "records:write" in user.permissions` — adding an "Auditor" role means seeding `["records:read", "dashboard:view"]` with zero code changes
- **Real-World Analog**: This mirrors AWS IAM policy design where permissions are attached to principals, not hardcoded into application logic

---

## 4. Security Design

### IDOR Prevention (Insecure Direct Object Reference)
**The Attack**: User A guesses User B's record UUID and accesses it via `GET /api/records/{uuid}`.
**The Fix**: Every query passes through `_active_records(db, user_id=scope)`. Non-admin users can only see records where `created_by == their_id`. The system returns `404` (not `403`) to prevent information leakage about record existence.

### Password Safety
- `password_hash` column is never included in `UserResponse` Pydantic schema
- Pydantic V2's `from_attributes` mode only serializes explicitly declared fields
- Even a code mistake in the router cannot leak the hash — the schema acts as a firewall

### Input Validation Layers
| Layer | What It Catches | Example |
|-------|----------------|---------|
| Pydantic Schema | Type mismatches, range violations | `amount: Decimal = Field(..., gt=0)` |
| SQLAlchemy Enum | Invalid record types | `RecordType("invalid")` raises ValueError |
| Database Constraints | NULL violations, FK integrity | `nullable=False`, `ondelete="CASCADE"` |

---

## 5. Key Interview Answers

### "Walk me through a request lifecycle"
1. Client sends `POST /api/records/` with JWT in Authorization header
2. FastAPI extracts token → `get_current_user` dependency decodes JWT, re-fetches user from DB, checks `is_active`
3. `require_permissions("records:write")` dependency verifies user has the permission in their JSON array
4. Pydantic V2 validates the request body against `RecordCreate` schema (amount > 0, type matches regex, etc.)
5. Router calls `record_service.create_record()` — service layer handles business logic
6. Service calls `record_repository.create_record()` — repository handles DB interaction
7. Repository commits to PostgreSQL, then invalidates all `dashboard_*` cache keys
8. Response is serialized through `RecordResponse` schema (which excludes internal fields like `deleted_at`)

### "How do you handle a production outage?"
1. Health check endpoint (`/health`) returns DB connection status — load balancer routes traffic away from unhealthy instances
2. Structured JSON logging middleware attaches a `request_id` (UUID4) to every log line — enables distributed tracing
3. Global exception handler catches unhandled errors and returns safe `500` response without leaking stack traces
4. Immutable audit log preserves all record state changes — enables forensic investigation after incidents

### "What would you do differently with more time?"
1. **Optimistic Locking**: Add `version` column to prevent concurrent update conflicts
2. **Background Workers**: Move cache invalidation and audit logging to async task queue
3. **Rate Limiting per User**: Current rate limiting is global; production needs per-user token bucket
4. **API Versioning**: Prefix routes with `/v1/` to support backward-compatible schema evolution
