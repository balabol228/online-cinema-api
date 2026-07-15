# Online Cinema API

A REST API for an online cinema service. This project implements a selected subset of
the full Online Cinema specification — focused on quality (tests, documentation)
rather than quantity of features.

## Selected Features (7 out of 6-8 required)

| # | Feature | Description |
|---|---------|--------------|
| 1 | Authentication | Registration, login, JWT access/refresh tokens |
| 2 | Roles & Permissions | User / Moderator / Admin, protected endpoints |
| 3 | Movie Catalog | Admin CRUD, public browsing with filters/pagination |
| 4 | Shopping Cart | Add/remove movies |
| 5 | Orders & Payment | Stripe Checkout + webhook |
| 6 | Likes, Ratings & Comments | Nested comment replies |
| 7 | Favorites | "Watch later" list |

## Tech Stack

- **FastAPI** — web framework with automatic Swagger/ReDoc documentation
- **SQLAlchemy 2.0 (async)** + **asyncpg** — PostgreSQL access layer
- **Alembic** — database migrations
- **Pydantic v2** — data validation
- **JWT (python-jose)** — authentication (access + refresh tokens)
- **Passlib/bcrypt** — password hashing
- **Stripe** — order payment processing
- **Docker Compose** — Postgres, Redis, MailHog, and the app itself
- **pytest + pytest-asyncio + httpx** — unit and integration tests

## Quick Start

### Using Docker

```bash
cp .env.sample .env
docker compose up --build
```

The app will be available at `http://localhost:8000`.

### Running Locally (without Docker)

``````bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.sample .env
alembic upgrade head
uvicorn app.main:app --reload
``````

## API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Every custom endpoint includes a description of its parameters, response codes,
and business logic directly in Swagger.

### Implemented Endpoints

| Method | Path | Description |
|--------|------|--------------|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Log in, returns access/refresh tokens |
| POST | `/api/v1/auth/refresh` | Refresh the access token |
| GET | `/api/v1/users/me` | Get current user's profile |
| GET | `/api/v1/movies` | Browse movie catalog: pagination, filters, sorting |
| GET | `/api/v1/movies/{id}` | Movie details |
| POST | `/api/v1/movies` | Create a movie (Moderator/Admin) |
| PATCH | `/api/v1/movies/{id}` | Update a movie (Moderator/Admin) |
| DELETE | `/api/v1/movies/{id}` | Delete a movie (Admin only) |
| POST | `/api/v1/genres`, `/api/v1/actors` | Populate reference data |
| GET/POST/DELETE | `/api/v1/cart`, `/api/v1/cart/items/{id}` | Shopping cart |
| POST | `/api/v1/orders` | Checkout (Stripe Checkout session) |
| GET | `/api/v1/orders`, `/api/v1/orders/{id}` | Order history and details |
| POST | `/api/v1/payments/webhook` | Stripe webhook |
| POST | `/api/v1/movies/{id}/like` | Like/unlike a movie |
| POST/GET | `/api/v1/movies/{id}/rating` | Rate a movie / view rating |
| POST/GET | `/api/v1/movies/{id}/comments` | Comments with nested replies |
| POST | `/api/v1/movies/{id}/favorite` | Add/remove from favorites |
| GET | `/api/v1/favorites` | List favorite movies |

## Running Tests

``````bash
pytest app/tests -v --cov=app --cov-report=term-missing
``````

76 tests, 87% coverage (unit + integration tests across all features).

## Project Structure

app/
├── api/v1/endpoints/   # FastAPI routers
├── core/               # configuration, security (JWT, password hashing)
├── db/                 # SQLAlchemy async session setup
├── models/             # ORM models
├── schemas/            # Pydantic schemas
├── services/           # business logic layer
└── tests/
├── unit/
└── integration/

## Git Workflow

- `main` — stable branch