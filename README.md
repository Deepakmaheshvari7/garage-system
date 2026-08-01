# Bike Showroom & Service Center Inventory System

Full-stack implementation of the architecture spec: FastAPI + PostgreSQL backend,
Streamlit frontend, JWT auth with role-based access control (Admin / Mechanic / Desk),
Excel/CSV bulk inventory import, atomic stock deduction, and PDF invoice generation.

## Project layout

```
garage-system/
├── backend/                  # FastAPI app
│   ├── app/
│   │   ├── core/             # config, db session, JWT/password helpers, auth deps
│   │   ├── models/           # SQLAlchemy models (Users, Inventory, JobCards, JobParts)
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── routers/          # auth, inventory, job_cards, billing, dashboard, users
│   │   ├── templates/        # invoice.html (Jinja2, rendered to PDF)
│   │   ├── create_first_admin.py   # one-time setup script
│   │   └── main.py           # app entrypoint
│   ├── requirements.txt
│   ├── Procfile              # for Render/Heroku-style deploys
│   └── .env.example
└── frontend/                  # Streamlit app
    ├── pages/                 # Admin Dashboard, Inventory, Job Cards, My Job Cards, Billing
    ├── api_client.py          # thin REST client wrapper
    ├── auth_guard.py          # per-page role guard (defense-in-depth)
    ├── main.py                # entrypoint; builds role-filtered sidebar nav
    ├── requirements.txt
    └── .env.example
```

## Local setup

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set DATABASE_URL to your local Postgres, and SECRET_KEY to a random value
# (python -c "import secrets; print(secrets.token_hex(32))")
```

You need a running PostgreSQL instance. Quickest way locally:

```bash
docker run --name garage-db -e POSTGRES_USER=garage_user -e POSTGRES_PASSWORD=garage_pass \
  -e POSTGRES_DB=garage_db -p 5432:5432 -d postgres:16
```

Then create the first Admin account (tables are auto-created on first run too,
but this script makes sure they exist before prompting):

```bash
python -m app.create_first_admin
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive Swagger API docs.

### 2. Frontend

```bash
cd frontend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # defaults to http://localhost:8000, change if needed
streamlit run main.py
```

Visit `http://localhost:8501`, log in with the Admin account you just created.
From there, use the **Inventory** page to add parts (or bulk-import a catalog),
and the **Job Cards** page to register Mechanic/Desk accounts via the API or by
asking your Admin to use `POST /api/auth/register`.

## Deployment (Render / Heroku-style)

### Backend
- New Web Service from this repo's `backend/` directory.
- Build command: `pip install -r requirements.txt`
- Start command: from the `Procfile` (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`)
- Provision a managed PostgreSQL add-on and set `DATABASE_URL` from it.
- Set environment variables: `SECRET_KEY` (required — app refuses to boot in
  production without it), `ENV=production`, `STANDARD_LABOR_RATE`, `TAX_PERCENTAGE`,
  `FRONTEND_ORIGIN` (your deployed Streamlit URL, for CORS).
- After first deploy, run `python -m app.create_first_admin` once via a one-off
  shell/console on the platform (it's interactive, so it isn't wired into the
  Procfile's release phase).
- **WeasyPrint system dependencies**: WeasyPrint needs Pango, Cairo, and
  GDK-PixBuf at the OS level. Most buildpacks for Python web services on
  Render/Heroku need an `Aptfile` (Heroku) or a Docker-based build to install
  these — check your platform's docs for "WeasyPrint system dependencies" if
  invoice generation 500s in production with an ImportError.

### Frontend
- New Web Service from `frontend/`, same build command pattern.
- Set `API_BASE_URL` to your deployed backend's URL.
- Streamlit Community Cloud also works directly if you don't need Render/Heroku
  for the frontend specifically — point it at `main.py` as the entrypoint.

## Roles

| Role | Can do |
|---|---|
| **Admin** | Everything: see cost_price/margins, manage inventory, dashboards, all job cards, billing, register new users |
| **Desk** | Create job cards, assign mechanics, view inventory (no cost_price), generate invoices |
| **Mechanic** | View only their assigned job cards, add parts (triggers stock deduction), log labor hours, update job status |

## Notable implementation details & bugs found during testing

This was built and then actually run end-to-end (curl + real browser automation),
not just written from the spec. A few real issues surfaced and were fixed:

1. **Race condition on concurrent stock deduction** — the spec explicitly calls
   this out as critical. The initial implementation used only
   `SELECT ... FOR UPDATE`, which is correct on PostgreSQL but is a silent no-op
   on some other backends. Fixed by adding a second layer: an atomic
   `UPDATE ... WHERE stock_quantity >= requested` that only succeeds if there's
   still enough stock at the moment of the write. Verified by firing 5
   concurrent requests against 1 unit of stock — exactly 1 succeeded, the rest
   got a clean `409 Insufficient stock`, and final stock was `0`, never negative.
2. **WeasyPrint/pydyf version conflict** — `weasyprint==62.3` doesn't pin an
   upper bound on its `pydyf` dependency, so a fresh `pip install` pulls
   `pydyf>=0.11.0`, which has a breaking API change and crashes PDF generation
   with `AttributeError: 'super' object has no attribute 'transform'`. Fixed by
   pinning `pydyf==0.10.0` in requirements.txt.
3. **bcrypt/passlib version conflict** — `bcrypt>=4.1` removed an attribute
   `passlib==1.7.4` uses for version detection, breaking all password hashing.
   Fixed by pinning `bcrypt==4.0.1`.
4. **Excel import crash on missing price** — a row with a blank `Price` cell
   parsed as `NaN`, which passed Python validation (`float(NaN)` doesn't raise)
   but then failed the database's `NOT NULL` constraint, aborting the *entire*
   batch insert, not just that row. Fixed by explicitly checking `pd.isna()` on
   required numeric fields before insert, so bad rows are now cleanly skipped
   and reported instead of taking down the whole import.
5. **Inline-edit save sent spurious updates** — the Streamlit admin inventory
   grid diffs edited rows against the original data to decide what to PATCH.
   Because pandas represents missing `cost_price` values as `NaN` once the
   column is numeric, and `NaN != NaN` is always `True` in Python, every row
   without a cost price was flagged as "changed" on every save, even with zero
   edits. Fixed with an explicit NaN-aware comparison.
6. **Sidebar leaked page links across roles** — the default Streamlit
   multipage sidebar lists every file in `pages/` regardless of who's logged
   in, so a Desk user saw an "Admin Dashboard" link that just errored out when
   clicked. The actual data was never exposed (every page re-checks role
   server-side), but it was a poor experience. Rebuilt navigation using
   `st.navigation`/`st.Page` so the sidebar itself is built per-role.

## Known limitations / good next steps

- `create_all()` is used for schema creation, which is fine to get started but
  doesn't handle schema migrations over time — move to Alembic before this
  goes near production data.
- No automated test suite yet (everything above was verified via manual
  end-to-end runs against a live server + browser automation during this
  build). Worth adding `pytest` + `httpx.AsyncClient` tests for the inventory
  deduction and billing math specifically, since those are the highest-stakes
  code paths.
- The Job Cards page on the Desk/Admin side could use comments/notes per job
  and an "edit vehicle reg" option — not in the original spec, but a common ask.
