# FinGuard Backend API

FinGuard is a RESTful API backend service built with FastAPI for managing organizational financial records. It provides secure endpoints for transaction management, database-driven dashboard aggregations, and role-based access control (RBAC).

## 🏗️ Architecture

The project strictly follows a layered architecture to maintain clear separation of concerns and testability:
- **API/Router Layer:** Handles HTTP requests, input validation (Pydantic), and dependency injection.
- **Service Layer:** Contains core business logic and orchestrates data flow.
- **Repository Layer:** Manages all data access and complex SQL aggregations.
- **Database:** SQLAlchemy ORM interfacing with SQLite (WAL mode).

## ✨ Core Features

- **Role-Based Access Control:** JWT-driven authentication with tiered roles (Admin, Analyst, Viewer).
- **Optimized Aggregations:** Dashboard metrics (summaries, trends) are calculated inside the database engine to prevent Python-space memory bottlenecks.
- **Immutable Audit Trails:** State changes (Updates/Soft Deletes) automatically generate immutable audit logs for compliance.
- **Caching Strategy:** Cache-aside implementation for high-frequency read endpoints.
- **Rate Limiting:** IP-based request throttling on sensitive endpoints (e.g., authentication) using `slowapi`.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Rajkaran-122/FinGuard.git
   cd FinGuard
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```
   *Update the `.env` file with your local configurations.*

4. **Seed the Database:**
   Provisions the database with test accounts and 50 randomized financial records.
   ```bash
   python scripts/seed.py
   ```
   *Admin Credentials: `admin@finance.dev` / `Admin@123`*

5. **Run the Application:**
   ```bash
   uvicorn app.main:app --reload
   ```
   *API Documentation is automatically generated and accessible at: `http://localhost:8000/docs`*

## 🧪 Testing

The project uses `pytest` with decoupled in-memory database scoping to ensure isolated testing contexts.

```bash
python -m pytest tests/ -v
```

## 🗺️ API Highlights

- `POST /api/auth/login`: Authenticate and receive a JWT.
- `GET /api/dashboard/summary`: Retrieve aggregated income, expenses, and net balance.
- `GET /api/records`: Fetch transaction records using cursor-based pagination.
- `POST /api/records`: Create a new financial record.

## 📄 License & Documentation

For deeper dives into architectural decisions and tradeoffs, please see [ARCHITECTURE.md](ARCHITECTURE.md). A Postman collection (`FinGuard_Postman_Collection.json`) is also included in the repository for immediate endpoint testing.
