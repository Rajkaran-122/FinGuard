# FinGuard — Business Requirements Document
Finance Data Processing and Access Control Backend

## 1. Executive Summary
This Business Requirements Document (BRD) formally defines the functional and non-functional requirements for the Finance Data Processing and Access Control Backend system (FinGuard). The proposed system is a RESTful backend service powering a multi-role finance dashboard. It manages financial records, enforces role-based access control, and provides aggregated analytics endpoints to support data-driven decisions by finance teams.

The system is implemented using **Python 3.12 + FastAPI + SQLite + SQLAlchemy**. FastAPI provides automatic OpenAPI documentation, native Pydantic-based request validation, and an elegant dependency injection system for robust RBAC. SQLite provides a fully ACID-compliant persistence layer out of the box, with a seamless zero-code-change migration path to PostgreSQL via SQLAlchemy's abstraction.

## 2. Business Context & Value Proposition

### 2.1 Problem Statement
There is a need for a centralized backend service that stores financial records, enforces Role-Based Access Control (RBAC), provides dashboard-ready aggregations, and handles validation and errors gracefully.

### 2.2 Value Proposition
- **FastAPI's automatic Swagger UI** guarantees API documentation is consistently synchronized with the codebase.
- **Pydantic v2** enforces strict data contracts at input/output boundaries.
- **SQLAlchemy ORM** ensures codebase longevity and database-agnostic portability.
- **Dependency Injection** centralizes RBAC checking logic visibly at the route declaration layer.
- **SQLite WAL Mode** enables excellent concurrent read-write stability during dashboard data ingestion phases.

## 3. Project Scope
- JWT-based stateless authentication with `python-jose` and bcrypt password encryption.
- Robust user and role management with strict hierarchical execution constraints (Viewer, Analyst, Admin).
- API-driven financial record CRUD with parameterized, queryable soft-deletes.
- Fast, database-aggregated summary analytical endpoints (trends, balances, categorizations).
- Meaningful HTTP status codes and unified JSON error shapes.

## 4. Access Control Requirements (RBAC)

Access control leverages FastAPI's native `Depends()` system. Protected routes declare their prerequisite authorization dependencies within the function signature:
```python
@router.post("/", dependencies=[Depends(require_role("admin"))])
def create_record(...): ...
```
This isolates security logic, simplifies unit testing, and is inherently supported by OpenAPI. Inactive and suspended users are instantly rejected globally through token intercept verification.

### Feature Matrix

| Feature / Endpoint Group | Viewer | Analyst | Admin |
|--------------------------|-------|---------|-------|
| View records & basic summaries | [Yes] Allowed | [Yes] Allowed | [Yes] Allowed |
| Advanced analytical trends & categories | [No] Denied | [Yes] Allowed | [Yes] Allowed |
| Create, Update, Delete records | [No] Denied | [No] Denied | [Yes] Allowed |
| Create, Manage, Delete users | [No] Denied | [No] Denied | [Yes] Allowed |

## 5. Non-Functional Architecture

### 5.1 Tech Stack Justification
- **FastAPI vs Flask/Django**: Chosen specifically because it is an API-first framework integrating Pydantic validations intrinsically while exposing self-documenting endpoints.
- **SQLite Database Strategy**: Employs WAL (Write-Ahead Logging) via DB Pragma connecting limits blocking phenomena making it extremely efficient as an evaluation candidate without compromising data schema normalization logic that directly ports to PostgreSQL.
- **Testing**: Complete suite built using `pytest` interacting identically via `TestClient` and pure ephemeral in-memory database isolation pools per-run ensuring completely stateless evaluation pipelines.

## 6. Implementation & Delivery Rules
System modules enforce clean layered separation of concerns traversing logically down specific pipelines: `routers (REST API Layer) -> services (Business Logics & Authorization Safety checks) -> repositories (Direct DAL logic) -> Models (ORM layer)`. This code adheres to strict incremental development pushes utilizing real-world version control methodologies via GitHub.
