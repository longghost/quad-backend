# Quad Backend (Python / FastAPI)

REST API for the Quad student marketplace front-end, built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**.

## Setup

1. **Create a virtual environment and install dependencies**
   ```
   python3 -m venv .venv
   source .venv/bin/activate        # on Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create a database** and copy `.env.example` to `.env`, filling in your own values:
   ```
   cp .env.example .env
   ```
   - `DATABASE_URL` — your Postgres connection string, e.g. `postgresql://postgres:yourpassword@localhost:5432/quad`
   - `JWT_SECRET` — any long random string (`python -c "import secrets; print(secrets.token_hex(32))"`)
   - `CORS_ORIGIN` — the origin your front-end runs on (e.g. `http://127.0.0.1:5500` for VS Code Live Server)

3. **Run the schema migration**
   ```
   python -m app.db.init_db
   ```
   Creates all tables and seeds the five categories.

4. **(Optional) Seed sample data** — matches the front-end's original mock listings:
   ```
   python -m app.db.seed
   ```
   Sample login: `ama.owusu@knust.edu.gh` / `Password123!`
   Admin login: `admin@quad.app` / `Password123!`

5. **Run the server**
   ```
   uvicorn app.main:app --reload
   ```
   API runs at `http://localhost:8000`. Interactive docs (try every endpoint from the browser) at `http://localhost:8000/docs`.

## Project structure
```
quad-backend-py/
├─ requirements.txt
├─ app/
│  ├─ main.py            — app entry point, middleware, router mounting
│  ├─ config.py           — settings from environment variables
│  ├─ database.py         — SQLAlchemy engine/session
│  ├─ models.py           — ORM models (mirrors schema.sql)
│  ├─ schemas.py          — Pydantic request/response schemas
│  ├─ security.py         — password hashing, JWT
│  ├─ dependencies.py     — auth guards (get_current_user, require_admin)
│  ├─ limiter.py          — rate limiter (used on /api/reports)
│  ├─ routers/            — one file per resource
│  └─ db/
│     ├─ schema.sql       — table definitions (same schema either language)
│     ├─ init_db.py       — runs schema.sql
│     └─ seed.py          — sample data loader
└─ uploads/               — uploaded listing photos (served at /uploads/...)
```

## API reference

Same endpoints, same behavior as the Node version — only the implementation changed. Full interactive reference is auto-generated at `/docs` once the server is running, but in short:

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/listings` (search, category, sort, page, limit), `GET /api/listings/{id}`, `POST /api/listings` (multipart, up to 6 photos, owner), `PATCH /api/listings/{id}`, `DELETE /api/listings/{id}`
- `GET /api/categories`
- `POST /api/reviews`, `GET /api/reviews/seller/{seller_id}`
- `GET /api/messages/threads`, `GET /api/messages/thread/{other_user_id}?listing_id=`, `POST /api/messages`
- `POST /api/reports` (no auth, rate-limited to 10/15min), `GET /api/reports/{reference}`
- `GET /api/admin/reports?status=`, `PATCH /api/admin/reports/{id}` (admin only)

Auth routes: send the JWT as `Authorization: Bearer <token>`.

## Wiring up the front-end

Same idea as before: in `js/main.js`, replace `QUAD.data.listings` with `fetch('http://localhost:8000/api/listings')`, and point the `sell-form`, `report-form`, `login`, and `register` submit handlers at the matching endpoints. Store the JWT after login/register and attach it as a Bearer token on authenticated requests.

## Notes
- The `/docs` page is a fast way to sanity-check each endpoint (send a request, see the response) before wiring up the front-end at all.
- Promote a user to admin by hand: `UPDATE users SET role = 'admin' WHERE email = '...';` (or use the seeded admin account).
- Photos are saved to local disk — fine for coursework; swap for cloud storage if you deploy somewhere with an ephemeral filesystem.
