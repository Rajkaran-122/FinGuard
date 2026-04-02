# FinGuard — Finance Data Processing & Access Control Backend

A production-grade RESTful backend service powering a multi-role finance dashboard. FinGuard manages financial records, enforces strict role-based access control (RBAC), and provides aggregated analytics endpoints.

## 🚀 Features

- **Robust Authentication:** JWT-based stateless authentication with `bcrypt` password hashing.
- **Strict RBAC:** Role-based access control enforced gracefully at the API route level via FastAPI's `Depends` injection (Roles: `Viewer`, `Analyst`, `Admin`).
- **Data Integrity:** Fully ACID-compliant SQLite backend with WAL (Write-Ahead-Logging) mode enabled for read/write concurrency. Seamless upgrade path to PostgreSQL via SQLAlchemy.
- **Strict Validation:** Pydantic `v2` enforces type safety and boundaries on all inputs and outputs.
- **Interactive Documentation:** Automatically generated OpenAPI UI at `/docs`.
- **Analytics Ready:** High-performance database-layer aggregations for summaries, trends, and categorized breakdowns.

## 🛠️ Technology Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI
- **Database:** SQLite (local dev/testing) / PostgreSQL (production compatibility)
- **ORM:** SQLAlchemy 2.0
- **Validation:** Pydantic
- **Testing:** Pytest & HTTPX

## 🏎️ Quick Start (5-Minute Setup)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Rajkaran-122/FinGuard.git
   cd FinGuard
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize environment variables:**
   ```bash
   cp .env.example .env
   # Ensure you set a custom JWT_SECRET inside .env
   ```

5. **Seed the database:**
   Automatically creates tables, testing users, and 50 random financial records:
   ```bash
   python scripts/seed.py
   ```

   *Seeded Credentials:*
   - **Admin:** `admin@finance.dev` | `Admin@123`
   - **Analyst:** `analyst@finance.dev` | `Analyst@123`
   - **Viewer:** `viewer@finance.dev` | `Viewer@123`

6. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

7. **Explore the API:**
   Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) to access the interactive Swagger UI.

## 🏗️ Architecture Design

The project uses a clean layered architecture to enforce separation of concerns:

- **Routers (`app/routers/`):** REST API endpoints mapping to HTTP actions. They handle request routing and instantly delegate work to the service layer.
- **Services (`app/services/`):** Houses pure business logic, permissions bounding, and transactional orchestration.
- **Repositories (`app/repositories/`):** Encapsulates SQLAlchemy database logic. Provides direct data interaction APIs isolating SQL specifics from the business logic.
- **Schemas (`app/schemas/`):** Pydantic models for request/response serialization and structural validation.
- **Models (`app/models/`):** SQLAlchemy ORM declarative classes representing actual database schema.

## 🧪 Testing

The API features integration tests leveraging an isolated in-memory SQLite database.
Run the full suite using:
```bash
python -m pytest tests/ -v
```

## 📜 Assignment Context
This backend was built strictly adhering to the requirements provided in the *Finance Data Processing and Access Control Backend BRD*.
