# RBAC Dashboard Platform

A multi-tenant, role-based web application built with **FastAPI** (async
SQLAlchemy + SQLite + JWT) and **React** (Vite + TypeScript).

Superadmins run the platform, organization admins run their organizations,
and developers/viewers work inside individual dashboards.

---

## Roles & scopes

Roles are **fixed** (each role's permission set is hardcoded); what is
**dynamic** is the assignment of users to roles within a scope — done at
runtime by superadmins (application scope) and admins (organization scope).

| Role | Scope | Can do |
| --- | --- | --- |
| **superadmin** | Application | Everything. Creates organizations, manages all users, assigns admins, full access to every dashboard. |
| **admin** | Organization | All permissions **within their organization(s)**: edit org info, manage admins, manage **DB connections**, create/delete dashboards, grant developer/viewer access. A user can be admin of one or many organizations. |
| **developer** | Dashboard | Browse their org(s) → dashboards; read **and edit** a dashboard they've been granted. |
| **viewer** | Dashboard | Browse their org(s) → dashboards; read-only on a dashboard they've been granted. |

**Navigation (viewer / developer):** they see their organization(s) as cards,
click into one, see the dashboards **they can access** in that org as cards, and
open a dashboard. Superadmins and admins get the same cards but with full
management inside each organization.

Key rules from the spec, enforced in the API:

- Only a **superadmin** can create or delete organizations.
- **Creating a user assigns a role**, and optionally attaches them to a scope:
  - `superadmin` → application scope (no org needed).
  - `admin` → **requires an organization** (added as an org admin).
  - `developer` / `viewer` → optionally granted a specific dashboard at creation
    (these roles are per-dashboard), otherwise granted later.
- **Creating an organization requires at least one admin** — you assign the
  founding admin(s) (existing users by email, or new users) in the same request.
- A **dashboard can only be created inside an organization** (it always carries
  an `organization_id`, and only that org's admins/superadmin can create it).
- A user can belong to **multiple organizations** (as admin) and have access to
  **multiple dashboards** (as developer or viewer).
- Each organization owns its own set of dashboards.
- Organizations carry minimal info: `name`, `email`, `contact_person`, `country`.

The full role → permission mapping lives in
[`backend/app/core/permissions.py`](backend/app/core/permissions.py).

---

## Data model

```
User ──< OrganizationMembership >── Organization ──< Dashboard >── DashboardAccess >── User
        (role = admin)                                            (role = developer | viewer)
```

- `User` — has an `is_superadmin` flag (application scope).
- `OrganizationMembership` — links a user to an org as **admin**.
- `Dashboard` — belongs to one organization.
- `DashboardAccess` — grants a user **developer** or **viewer** on one dashboard.
- `DBConnection` — a database connection owned by an org (type `postgres` /
  `mysql` / `mssql`, host, port, database, username, password). An org can have
  many. The **password is encrypted at rest** (Fernet) and never returned by
  the API — responses expose only a `has_password` flag; updates rotate it only
  when a new value is supplied.

---

## Project layout

```
backend/
  app/
    core/         config, database, security (JWT/bcrypt), permissions
    models/       SQLAlchemy models
    schemas/      Pydantic request/response models
    api/
      deps.py     auth + per-scope authorization dependencies
      routes/     auth, me, users, organizations, dashboards
    services.py   shared helpers (get-or-create user)
    seed.py       bootstraps the first superadmin
    main.py       app factory + router wiring
  tests/          end-to-end RBAC tests (pytest)
frontend/
  src/
    api/          typed fetch client + shared types
    auth/         AuthContext (login/session/permissions)
    components/   Layout, small UI primitives
    pages/        Login, Home, Organizations, OrganizationDetail,
                  Dashboards, DashboardDetail, Users
```

---

## Running locally

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit JWT_SECRET and the superadmin creds
uvicorn app.main:app --reload --port 8000
```

On first start the app creates the SQLite schema and a bootstrap superadmin
(defaults: `admin@example.com` / `Admin@12345` — **change these in `.env`**).

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 2. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api → :8000)
```

Sign in with the superadmin credentials, then create organizations, assign
admins, build dashboards, and grant developer/viewer access.

### 3. Tests

```bash
cd backend
source .venv/bin/activate
pytest                # 10 end-to-end RBAC tests
```

---

## API overview

All endpoints are under `/api`. Auth is a Bearer JWT access token
(30 min TTL) with a refresh token (7 days).

| Method & path | Scope | Purpose |
| --- | --- | --- |
| `POST /auth/login` | public | Email + password → access & refresh tokens |
| `POST /auth/refresh` | public | Refresh token → new access token |
| `GET /me` | any user | Profile, primary role, permissions, memberships, grants |
| `GET /users` | superadmin | List users |
| `POST /users` | superadmin | Create a user with a `role` (+ optional `organization_id` / `dashboard_id`) |
| `PATCH/DELETE /users/{id}` | superadmin | Update / delete a user |
| `GET /organizations` | any user | Orgs the caller can see |
| `POST /organizations` | superadmin | Create an org with ≥1 `admins` |
| `GET /organizations/{id}` | org member | Read org info (admins, or viewers/developers with a dashboard grant in it) |
| `PATCH /organizations/{id}` | org admin | Update org info |
| `DELETE /organizations/{id}` | superadmin | Delete an organization |
| `GET/POST/DELETE /organizations/{id}/members` | org admin | Manage org admins |
| `GET/POST/PATCH/DELETE /organizations/{id}/connections` | org admin | Manage the org's DB connections |
| `GET /dashboards` | any user | Dashboards the caller can access |
| `POST /dashboards` | org admin | Create a dashboard in an org |
| `GET /dashboards/{id}` | viewer+ | Read a dashboard |
| `PATCH /dashboards/{id}` | developer+ | Edit a dashboard |
| `DELETE /dashboards/{id}` | org admin | Delete a dashboard |
| `GET/POST/PATCH/DELETE /dashboards/{id}/access` | org admin | Manage developer/viewer grants |

"org admin" = superadmin **or** an admin member of that organization.
Dashboard scope resolves as: superadmin / org-admin → full; direct grant →
developer or viewer.

---

## Security notes

- Passwords hashed with **bcrypt**; tokens signed with **HS256** (`JWT_SECRET`).
- CORS is restricted to the configured frontend origins.
- The `.env` `JWT_SECRET` and bootstrap superadmin password **must** be changed
  before any non-local deployment.
- SQLite is used for zero-setup local development; the async SQLAlchemy layer
  swaps to PostgreSQL by changing `DATABASE_URL` (add a migration tool such as
  Alembic for production).
