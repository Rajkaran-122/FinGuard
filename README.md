# FinGuard — Production-Grade Finance API

**FinGuard** is a high-performance, enterprise-ready finance dashboard backend system built with Python, FastAPI, and PostgreSQL. It features robust role-based access control (RBAC), multi-token authentication, and a powerful analytics engine.

## 🚀 Key Features

*   **Enterprise Architecture**: Domain-driven design with layered Service-Repository pattern.
*   **Security First**: 
    *   Dual-token JWT (Access + Refresh) system with rotation and revocation.
    *   Enum-based Role-Based Access Control (Admin, Analyst, Viewer).
    *   Password hashing with `bcrypt` (12 rounds).
*   **Performance & Scalability**:
    *   Fully Asynchronous I/O using **SQLAlchemy 2.0 (Async)** and `asyncpg`.
    *   **Redis Caching** for dashboard analytics and trend calculations.
    *   Connection pooling and pre-ping for database stability.
*   **Observability**:
    *   Structured JSON logging with **Structlog**.
    *   Traceable Request IDs attached to every log entry.
    *   Latency-tracking middleware for every API call.
*   **Deep Analytics**:
    *   Monthly summaries with income/expense growth percentages.
    *   Automatic category distribution breakdowns.
    *   6-month time-series trend data.
*   **Developer Friendly**:
    *   Strict Pydantic V2 validation.
    *   Robust Seed script for local development.
    *   Production-ready Docker orchestration with Gunicorn/Uvicorn.

## 🛠 Tech Stack

*   **Core**: Python 3.12+, FastAPI, Uvicorn, Gunicorn
*   **Database**: PostgreSQL, SQLAlchemy 2.0 (Async), Alembic
*   **Caching**: Redis (aioredis)
*   **Security**: python-jose, passlib (bcrypt)
*   **Validation**: Pydantic V2
*   **Logging**: Structlog
*   **Rate Limiting**: SlowAPI

## 📖 API Documentation

Once running, access the interactive documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📦 Getting Started (Docker)

The fastest way to run the entire stack (API, PostgreSQL, Redis):

```bash
docker-compose up --build
```

## 🧪 Seeding Data

Populate your database with 180+ days of realistic financial data:

```bash
# Inside the container or local venv
python -m scripts.seed
```

### Test Credentials:
*   **Admin**: `admin@finguard.com` / `Admin@123`
*   **Analyst**: `analyst@finguard.com` / `Analyst@123`
*   **Viewer**: `viewer@finguard.com` / `Viewer@123`

## 📐 Project Structure

```text
app/
├── api/v1/         # Domain-specific route handlers
├── core/           # Infrastructure: security, database, logging, middleware
├── models/         # SQLAlchemy ORM models
├── repositories/   # Data access layer (async CRUD)
├── schemas/        # Pydantic V2 validation models
├── services/       # Business logic & analytics orchestration
└── main.py         # Application entrypoint & factory
```

## 📜 License

MIT License. Developed for enterprise-level financial data processing.
