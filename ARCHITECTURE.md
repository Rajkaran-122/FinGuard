# Architectural Trade-Offs & Senior Engineering Decisions

This document highlights the principal engineering evaluations justifying the design of the **FinGuard** backend framework demonstrating explicit awareness of production friction vs system scale parameters.

## 1. Why FastAPI? (Framework Choice)

### Trade-Off Evaluated: Django (Full-Battery) vs Flask (Micro) vs FastAPI (API-First)

- **The Decision:** **FastAPI**
- **Justification:** Enterprise finance requirements demand explicit schemas and predictable Input/Output serialization. Django is heavily bound to its internal ORM and monolithic template layouts making headless RESTful API microservices occasionally contentious. Flask lacks intrinsic typing constraints requiring extensive 3rd-party validation plugins (Marshmallow). 
- **The specific "Top 1%" Benefit:** FastAPI forces Pydantic integration at zero cost blocking malicious and malformed inputs prior to business logic execution. Furthermore, generating automated Swagger specifications reduces manual YAML documentation drift completely.

## 2. Why Layered Service/Repository Separation?

### Trade-Off Evaluated: Active Record (Routers touch DB directly) vs Data Mapper (Services/Repositories)

- **The Decision:** **Strict Layering (Routes → Services → Repositories)**
- **Justification:** In average API constructs, developers inject SQLAlchemy DB sessions directly inside `@router` controllers executing `db.query(...)`. If complex finance formula rules fluctuate, the developer is forced to mock extensive HTTP pipeline mechanics just to evaluate computation arrays. 
- **The specific "Top 1%" Benefit:** Relocating raw `DB` connectivity to `app/repositories/` ensures data mapping boundaries are completely respected. `app/services/` holds entirely agnostic business algorithms orchestrating multiple repositories together cleanly making core application behavior strictly isolated, deeply comprehensive, and trivially testable.

## 3. Why SQLite configured with WAL Parameters?

### Trade-Off Evaluated: Default SQLite vs Dockerized PostgreSQL

- **The Decision:** **SQLite (Enabled with Write-Ahead Logging via `PRAGMA journal_mode=WAL`)**
- **Justification:** Implementing PostgreSQL directly inside an isolated GitHub submission repository introduces massive infrastructure roadblocks simply blocking recruiters from booting the evaluation environment rapidly. 
- **The specific "Top 1%" Benefit:** By binding purely through generic SQLAlchemy abstractions and executing localized Database Pragma initialization (WAL modes), SQLite naturally mimics scalable multithreaded capabilities out-of-the-box supporting dashboard reporting `READs` while blocking `WRITE` starvation events. If production requirements scale beyond a local scope, altering connection credentials from `sqlite:///` to `postgresql+psycopg2://` immediately switches architectures seamlessly without altering any repository logic implementations.

## 4. Role-Based Access Control Middleware

### Trade-Off Evaluated: Embedded Logical Checks vs Application Injected Middleware

- **The Decision:** **FastAPI Framework Parameter Injection `Depends()`**
- **Justification:** Surrounding hundreds of endpoint functions with explicit evaluation matrices `if current_user.role not in ["admin"]: raise 403` breeds tremendous structural redundancy guaranteeing developer errors in large landscapes.
- **The specific "Top 1%" Benefit:** Security configurations are natively bound directly alongside endpoint schema definitions preventing the request from processing through any body parsers if authorization fails. Example: `Depends(require_role("admin"))` clearly surfaces the requirement logic outwardly allowing swagger parsing tools to instantly comprehend what endpoints have authorization barriers inherently.

## 5. Statistical Database Aggregation Execution 

### Trade-Off Evaluated: Executing Iteration Arrays Memory vs Leveraging Direct Database Functions 

- **The Decision:** **SQL Repository Component Aggregation**
- **Justification:** A dashboard demanding "Total YTD Expenses" fetching raw historical bounds across tens of thousands of generic rows simply to parse amounts into an array and sum `amount['totals']` cascades Memory exhaustion immediately globally scaling badly.
- **The specific "Top 1%" Benefit:** `record_repository.py` inherently utilizes direct connection bindings injecting raw `func.sum()` alongside localized `strftime` constraints shifting mathematical evaluation processes natively backwards downwards the pipeline forcing rapid C-compiled engines processing returns within generic milliseconds minimizing network transmission footprint boundaries inherently mitigating application bottlenecking scenarios.
