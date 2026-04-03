# FinGuard — Finance API

FinGuard is a structured RESTful backend designed to process financial records at scale. It implements production-standard data logic, granular access control, dynamic analytics, and complete GitHub Actions CI/CD workflows.

---

## Technical Features

FinGuard implements standard architectural patterns for enterprise environments:

1. **PostgreSQL & Alembic Migrations:** Utilizes a containerized `postgres:15-alpine` system and tracks schema evolution using `Alembic`.
2. **Granular RBAC Arrays vs Enums:** Implemenets a permission-array dependency injection model (`users:manage`, `records:write`, `dashboard:view`) over rigid string Enums.
3. **Event-Driven Cache Invalidation:** The dashboard aggregates transactional data natively. When write operations execute, the backend invalidates corresponding dashboard caches to prevent stale data retrieval.
4. **MoM Analytics & Time Buckets:** `summary_service.py` dynamically matches bounded queries against preceding time buckets to extract Month-over-Month (MoM) momentum percentages.
5. **Idempotency Gateways & Rate Limiting:** Write operations require `Idempotency-Key` headers to prevent duplicate network retries. Built-in `slowapi` rate limits throttle excessive login attempts.
6. **Automated CI/CD (Pytest):** A decoupled Pytest environment integrated within `.github/workflows/ci.yml`. It triggers ephemeral Postgres containers to validate logic upon PR creations.

---

## System Architecture

**Stack:** Python 3.12 | FastAPI | SQLAlchemy | PostgreSQL | Docker | Pytest

### Layered Architecture

```mermaid
graph TB
    subgraph Client Layer
        C1[Web Dashboard]
        C2[Postman / cURL]
    end

    subgraph API Gateway
        MW[Rate Limiter + CORS + Structured Logger]
        R1[Auth Router]
        R2[Records Router]
        R3[Dashboard Router]
        R4[Users Router]
    end

    subgraph Security Layer
        JWT[JWT Token Decoder]
        RBAC[Permission Array Gate]
        OWN[Ownership Scope Filter]
    end

    subgraph Service Layer
        AS[Auth Service]
        RS[Record Service]
        SS[Summary Service]
        US[User Service]
    end

    subgraph Data Layer
        REPO[Record Repository]
        CACHE[Cache-Aside Store]
        AUDIT[Immutable Audit Log]
    end

    subgraph Persistence
        DB[(PostgreSQL 15)]
        MIG[Alembic Migrations]
    end

    C1 & C2 -->|HTTPS| MW
    MW --> R1 & R2 & R3 & R4
    R1 --> JWT --> AS
    R2 & R3 & R4 --> JWT --> RBAC --> OWN
    OWN --> RS & SS & US
    RS & SS --> CACHE
    RS & SS & US --> REPO
    RS --> AUDIT
    REPO --> DB
    MIG -.->|Schema Version Control| DB

    style CACHE fill:#2d6a4f,stroke:#1b4332,color:#d8f3dc
    style DB fill:#1d3557,stroke:#457b9d,color:#a8dadc
    style RBAC fill:#e63946,stroke:#d62828,color:#f1faee
    style OWN fill:#e76f51,stroke:#f4a261,color:#fff
```

### Request Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant Router
    participant JWT Auth
    participant RBAC
    participant Service
    participant Cache
    participant Repository
    participant PostgreSQL

    Client->>Router: HTTP Request + Bearer Token
    Router->>JWT Auth: Extract & decode token
    JWT Auth->>PostgreSQL: Re-fetch user (block deactivated)
    JWT Auth-->>Router: User object

    Router->>RBAC: Check permissions array
    alt Missing permissions
        RBAC-->>Client: 403 Forbidden
    end

    Router->>Service: Execute business logic

    Note over Service: Ownership scope resolved<br/>Admin → all data<br/>Others → own data only

    alt Read Operation (GET)
        Service->>Cache: Check cache (key = scope + params)
        alt Cache HIT
            Cache-->>Service: Cached result
        else Cache MISS
            Service->>Repository: Query with ownership filter
            Repository->>PostgreSQL: SQL (indexed aggregation)
            PostgreSQL-->>Repository: Result set
            Repository-->>Service: Data
            Service->>Cache: Store (TTL = 1 hour)
        end
    else Write Operation (POST/PUT/DELETE)
        Service->>Repository: Mutate record
        Repository->>PostgreSQL: INSERT/UPDATE + audit log
        PostgreSQL-->>Repository: Committed
        Service->>Cache: Invalidate dashboard_* keys
    end

    Service-->>Client: JSON Response
```

### Assumptions & Trade-offs (Assignment Specific)
* **Authentication**: Employs standard JWT header parsing mapped to an in-database User entity. External OAuth (Google/SSO) was bypassed to maintain isolated sandbox testing suitable for assignment boundaries.
* **Caching vs Message Queues**: The dashboard summary utilizes a synchronous cache-aside invalidation pattern. In production systems, invalidation would use asynchronous queues (RabbitMQ/Kafka) to avoid blocking the main thread. Synchronous dictionary purging demonstrates the system design mechanism without infrastructural overhead.
* **Production Scaling Blueprint**: Moving to AWS/GCP, the architecture decouples by mapping the internal memory `dict` to a remote `Redis` cluster, and substituting the local Postgres container to an `RDS/Aurora` instance using identical Alembic configurations.

---

## Setup Instructions

**Prerequisites:** Docker, Python 3.12

### 1. Launch Infrastructure
Execute Docker Compose to bootstrap and isolate the database.
```bash
docker compose up -d
```

### 2. Setup Dependencies & Environment
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Provision Migrations & Seed Default Workspaces
Run the seeder script. This provisions Alembic `upgrade head`, pushes tables to Postgres, and seeds historical data alongside role accounts.
```bash
python scripts/seed.py
```
> **Seeded Test Accounts**:
> * **Admin**: `admin@finance.dev` | `Admin@123` (Full analytical and write access)
> * **Analyst**: `analyst@finance.dev` | `Analyst@123` (Read-only + Analytical scopes)
> * **Viewer**: `viewer@finance.dev` | `Viewer@123` (Read-only basic scopes)

### 4. Execute Backend
```bash
uvicorn app.main:app --reload
```
Navigate to **`http://localhost:8000/docs`** to explore the interactive Swagger endpoints.

---

## Test Suite Execution

The test suite includes IDOR security tests proving ownership enforcement, standard CRUD, and RBAC validations. Tests run against isolated `SQLite :memory:` nodes, dynamically overriding production dependency hooks.
```bash
python -m pytest tests/ -v
```

**Test coverage includes:**
- Health check and authentication validation
- Admin CRUD operations with cache consistency
- Unauthorized access blocked (401)
- **IDOR Protection**: Viewer cannot access admin's records by UUID
- **Ownership Scoping**: Viewer's record list excludes other users' data
- **Summary Isolation**: Viewer's dashboard aggregations strictly reflect requested user scope

---

## Security & Data Isolation

FinGuard enforces multi-tenant data isolation at the repository layer:

| User Role | Records Visible | Dashboard Scope | Write Access |
|-----------|----------------|-----------------|--------------|
| Admin | All records | Organization-wide | Full CRUD |
| Analyst | Own records only | Own data only | Read-only |
| Viewer | Own records only | Own data only | Read-only |

**IDOR Prevention**: All queries pass through `_active_records(db, user_id=scope)`. Non-admin users query records where `created_by == their_id`. Unauthorized operations return `404` (not `403`) preventing information leakage regarding record existence.

---

## Documentation Links

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Deep-dive design justifications and layering decisions
- **[INTERVIEW_PREP.md](INTERVIEW_PREP.md)** — System design thinking: scale analysis, failure scenarios, trade-offs, and security design explained for technical discussions
