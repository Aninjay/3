# TAPMI CRM on Vercel

This guide deploys the existing React/Vite frontend and Flask API as **two Vercel projects** connected to the same Git repository. PostgreSQL remains the application database. The repository backend is Flask (not FastAPI); the Python Vercel runtime supports the current Flask app, so deployment does not require a framework rewrite.

## What is configured

- The API entry point is the repository-root `index.py`, which exposes the existing Flask app to Vercel's Python runtime.
- Root `requirements.txt` installs the runtime dependencies. `.python-version` selects Python 3.12.
- Production/Vercel startup now fails closed if `SECRET_KEY`, PostgreSQL `DATABASE_URL`, or an explicit non-wildcard `CORS_ORIGINS` value is missing.
- `backend/app/db/connection.py` reuses a bounded psycopg connection pool for PostgreSQL connections. The default pool maximum is one connection per warm function instance.
- The frontend remains a Vite build under `frontend/`; `frontend/vercel.json` sets the build and SPA fallback.
- The frontend uses `VITE_API_BASE_URL`, and Flask CORS uses `CORS_ORIGINS`. Authentication continues to use the existing bearer token and database-backed sessions.
- `vercel.json` keeps test, frontend, deliverable, and CSV files out of the Python function bundle.

Vercel currently supports Python 3.12, 3.13, and 3.14. This project pins 3.12 for a predictable runtime. The application is Flask, even though FastAPI was mentioned in the deployment request.

## Before you deploy

1. Push this branch to your Git provider after reviewing it.
2. Choose a managed PostgreSQL database with persistent storage and backups. Store its connection URL securely. Do not use a Vercel filesystem SQLite database for production; function filesystems are not the CRM's durable data store.
3. The project currently contains a local SQLite database with 809 records across 20 tables. Those records are not automatically visible to a newly provisioned PostgreSQL database. The included importer reads SQLite in read-only mode and refuses to merge into any non-empty PostgreSQL destination.
4. Generate unique values for `SECRET_KEY` and the initial organizer password. Never commit them.

## Create the backend Vercel project

1. In Vercel, add a project and import the TAPMI repository.
2. Set **Root Directory** to the repository root (`.`), not `frontend`.
3. Use the Python/Flask detection or leave the framework as detected from root `index.py` and `requirements.txt`. Do not configure a Node build command or output directory for this API project.
4. Add the backend environment variables below to every Vercel environment you intend to run. Production values are required; Preview/Development deployments also fail closed unless they have a PostgreSQL URL, secret, and trusted frontend origin. Prefer separate databases for non-production environments.
5. Deploy the selected branch. The API's public base URL will look like `https://your-api-project.vercel.app`.

### Backend environment variables

| Name | Required value |
|---|---|
| `DATABASE_URL` | PostgreSQL provider connection URL, preferably its private/pooler URL when available. |
| `SECRET_KEY` | Long, unique random value used by the application. |
| `FLASK_ENV` | `production` |
| `CORS_ORIGINS` | Exact frontend origin, e.g. `https://your-frontend.vercel.app`; comma-separate additional trusted origins. |
| `SEED_DEMO_DATA` | `false` |
| `BOOTSTRAP_CONVENER_EMAIL` | First organizer email, if setting up a new production database. |
| `BOOTSTRAP_CONVENER_PASSWORD` | Unique password of at least 12 characters, if setting up a new production database. |
| `PG_POOL_MAX_SIZE` | Optional. Defaults to `1` per function instance; coordinate with the database connection limit before increasing. |
| `PG_POOL_TIMEOUT` | Optional pool wait timeout in seconds; defaults to `10`. |
| `PILOT_EVENT_NAME` | Optional display label; defaults to `Kala Fest`. |

The legacy OTP activation endpoints also accept `OTP_EXPIRY_MINUTES` and `OTP_MAX_ATTEMPTS` (defaults: 15 and 5). The current frontend does not expose OTP activation. Although `.env.example` lists SMTP settings, this codebase does not send activation OTP messages through SMTP; it uses its development logging adapter. Do not expect OTP email delivery in production without implementing and verifying that adapter.

The Python runtime bundles the current API's reporting, spreadsheet, allocation, and database dependencies. Keep `requirements-vercel.txt` limited to runtime packages; pytest is not installed in the deployment bundle.

## Prepare PostgreSQL and preserve the current records

Vercel function startup does **not** run migrations or seed operations. This avoids concurrent function cold starts racing to alter the database. For a new, empty production database, run the schema migration and then inspect a dry run of the local SQLite transfer from a trusted machine. With the database URL and other values set privately in the environment, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
export DATABASE_URL='YOUR_PRODUCTION_POSTGRESQL_URL'
export SECRET_KEY='YOUR_PRODUCTION_SECRET'
export FLASK_ENV=production
export SEED_DEMO_DATA=false
export BOOTSTRAP_CONVENER_EMAIL='organizer@example.edu'
export BOOTSTRAP_CONVENER_PASSWORD='YOUR_UNIQUE_PASSWORD_AT_LEAST_12_CHARACTERS'
python -m backend.app.db.migrate
python -m backend.app.db.transfer_sqlite_to_postgres 'backend/cultural_committee.db'
```

The dry run should report 809 source records across 20 tables (the current local snapshot). It makes no database writes. Review the counts and confirm the destination is the intended, empty PostgreSQL database. Only after review, apply the copy:

```bash
python -m backend.app.db.transfer_sqlite_to_postgres 'backend/cultural_committee.db' --apply
python -m backend.app.db.seed
```

The importer copies application tables and explicit record IDs, advances PostgreSQL sequences, and commits the transfer as one transaction. It reads the SQLite file read-only. If the destination has any application records, it refuses to proceed; it never merges, overwrites, or deletes rows. In that case, stop and plan a separate reviewed migration/merge. Do not point it at a production database with records unless the target has been backed up and the import has been explicitly approved. The seed step adds missing catalog/bootstrap data; with `SEED_DEMO_DATA=false` it does not add demo users, volunteers, or events. Seed does not reset an existing organizer password. Do not paste secrets into shell history; use secure environment handling or a private local env file excluded from Git.

## Create the frontend Vercel project

1. Add a second Vercel project from the same repository.
2. Set **Root Directory** to `frontend`.
3. Confirm the build command is `npm run build` and output directory is `dist` (also in `frontend/vercel.json`).
4. Set the frontend environment variable below for every frontend environment you intend to use. A preview build without it will default to same-origin `/api/v1`, which is not connected to the separate backend project.
5. Deploy after the backend is deployed and its CORS origin is configured. If changing this variable later, trigger a new build because Vite embeds it in the frontend bundle.

### Frontend environment variable

```text
VITE_API_BASE_URL=https://your-api-project.vercel.app/api/v1
```

This is a public URL, not a secret. Set the backend's `CORS_ORIGINS` to the exact deployed frontend origin. If using a custom domain, allow that origin too. For preview deployments, either add the exact preview origins or use a stable preview domain; do not set an unrestricted production wildcard.

## Verify the deployment

Use the backend domain for API checks:

1. Open `https://your-api-project.vercel.app/api/v1/health`. It should return `status: healthy`, `database.connected: true`, and `database.engine: PostgreSQL`.
2. Confirm the frontend URL loads and that browser Network requests target the backend domain under `/api/v1`.
3. Sign in on the frontend with the provisioned organizer account. Confirm the login request returns 200 and a token, then confirm an authenticated dashboard request returns 200. Sign out and confirm protected endpoints reject the old token.
4. Check a volunteer or core committee account only after those accounts are provisioned in the production database; do not use demo credentials.
5. Exercise every route listed by the Flask route map against a non-production database before the production launch. The existing tests cover key authentication, lifecycle, allocation, and committee behavior but do not constitute a production endpoint smoke test.
6. Review Vercel function logs and PostgreSQL connection metrics. The in-process pool is limited per function instance, so overall database connections can still grow with the number of warm instances. Use the database provider's pooler URL if its connection limit requires it.

The project is not considered deployed/verified until the hosted health endpoint, database connectivity, browser CORS requests, and real login flow have all been checked. This repository change does not deploy the project or run production database commands.

## Local checks and fallback

The existing Docker and Netlify deployment files remain available. These Vercel settings are additive. To test the frontend locally, run `npm ci && npm run build` from `frontend`. To run backend tests, install `backend/requirements.txt` and run `pytest backend/tests` with a disposable test database. Do not point tests at a production database.
