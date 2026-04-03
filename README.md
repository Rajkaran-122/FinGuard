# FinGuard — Resilient Finance Data Processing Layer

This is not a traditional CRUD application. FinGuard is a backend architecture designed around scale, idempotency, and failure isolation. It is built to demonstrate system-design thinking under simulated enterprise constraints, proving how data logic behaves when subjected to strict access control and massive transaction volumes.

---

## Engineering Mindset: Designing for Failure & Scale

When interviewing for backend roles, the implementation details matter less than *why* they were chosen. This project is built around anticipating system breaking points.

### The Scale Narrative: What Breaks at 100k Users?
If this application hits 100,000 active users and millions of financial records, the immediate failure point is the **dashboard aggregation queries**.
*   **The Problem**: Running `SUM()`, `COUNT()`, and `GROUP BY` across millions of rows causes CPU exhaustion and database lock contention.
*   **The Fix**: I implemented an aggressive **Cache-Aside Pattern** alongside **Composite Grouping Indexes**. The heavy DB queries execute exactly once per hour per user. Subsequent dashboard requests bypass the database entirely, shifting the bottleneck from DB CPU to fast memory access.

### Failure Handling & Idempotency
Network retries are inevitable. If a client connection drops during a transaction, they will retry.
*   **The Problem (Duplicate Writes)**: If a user clicks "Submit" twice due to a laggy connection, they risk double-charging their financial ledger.
*   **The Fix**: The API gateway intercepts all write operations explicitly requiring an `Idempotency-Key` header. Duplicate requests fetch the finalized response from an in-memory cache directly, ensuring a mutated transaction resolves exactly once.

---

## Architectural Trade-Offs (The "Big Three")

Every technical decision in this project was weighed against constraints. Here is the reasoning:

1. **Why PostgreSQL over SQLite or Document Stores?**
   Financial ledgers strictly demand ACID compliance. Eventual consistency causes fatal race conditions, and file-level locking causes read/write contention. PostgreSQL, managed by `Alembic` schema migrations, guarantees row-level transactional integrity.

2. **Why a Synchronous Cache-Aside Pattern?**
   In a massive enterprise ecosystem, invalidations happen asynchronously via RabbitMQ or Kafka. However, within the scope of this assignment, introducing event queues is over-engineering. I built an in-memory TTL dictionary that mimics a Redis client (`.get`, `.set`, `.invalidate`). Migrating this to a distributed AWS ElastiCache cluster requires changing one file, without modifying the router or service layers.

3. **Why Permission Arrays over Hardcoded Role Enums?**
   Routing logic checking `if user.role == "admin"` creates technical debt. Instead, I injected permission arrays (e.g., `["records:write"]`). If a new "Auditor" role is required tomorrow, no API logic gets rewritten; we simply append the new role to the database array, dynamically mirroring enterprise IAM models.

---

## Core Security & Data Isolation Model

FinGuard enforces multi-tenant data isolation directly at the database repository layer, mitigating IDOR (Insecure Direct Object Reference) attacks structurally. 

*   **Ownership Filtering**: Every database query accepts an optional `user_id` scope. Non-admin queries inject the caller's UUID into the `WHERE` clause.
*   **Data Leakage Prevention**: If a user attempts to fetch a valid record that belongs to another person, the backend returns a `404 Not Found` (rather than a `403 Forbidden`). This prevents an attacker from extracting metadata regarding the existence of private entities.

---

## Project Structure & Architecture

```mermaid
graph TB
    subgraph Client Layer
        C1[Web Dashboard / Clients]
    end

    subgraph API Gateway
        MW[Rate Limiter + CORS]
        R1[Auth Router] & R2[Records Router] & R3[Dashboard Router] & R4[Users Router]
    end

    subgraph Security Layer
        JWT[JWT Decoder] --> RBAC[Permission Array Gate] --> OWN[Ownership Scope Filter]
    end

    subgraph Service & Persistence
        SRV[Service Layer] --> CACHE[Idempotency & Cache Store]
        SRV --> REPO[Repository Layer] --> DB[(PostgreSQL 15)]
    end

    C1 -->|HTTPS| MW
    MW --> R1 & R2 & R3 & R4
    R1 & R2 & R3 & R4 --> JWT
    OWN --> SRV
```

**Stack:** Python 3.12 | FastAPI | SQLAlchemy | PostgreSQL | Docker | Pytest

---

## Fast-Track Setup Instructions

**Prerequisites:** Docker, Python 3.12

### 1. Launch & Bootstrap
Run the Docker daemon to initialize the isolated PostgreSQL container.
```bash
docker compose up -d
```

### 2. Virtual Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Migrations & Seed Data
Initialize `Alembic` constraints and seed randomized financial data across multiple role boundaries.
```bash
python scripts/seed.py
```
> **Seeded Test Accounts**:
> * **Admin**: `admin@finance.dev` | `Admin@123` (Full analytical & write scopes)
> * **Analyst**: `analyst@finance.dev` | `Analyst@123` (Read-only + Analytical scopes)
> * **Viewer**: `viewer@finance.dev` | `Viewer@123` (Read-only basic scopes)

### 4. Execute Backend
```bash
uvicorn app.main:app --reload
```
Navigate natively to **`http://localhost:8000/docs`** to explore the Swagger UI endpoints.

---

## Test Suite Execution

The Pytest suite intercepts dependency injection, substituting the PostgreSQL gateway with an ephemeral `SQLite :memory:` node, and dynamically validates the ownership security boundaries.

```bash
python -m pytest tests/ -v
```

All integration testing enforces strict checks against:
- Data Scoping and Multi-tenant boundaries.
- Cache Invalidation verification.
- Idempotency validations for network retry paths.
