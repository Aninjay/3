# TAPMI CRM Deployment Guide

This project has a React + Vite frontend, a Flask API, and PostgreSQL storage. Netlify hosts the frontend; a Docker-compatible service (such as Render or Railway) hosts the API. Use the included Docker Compose stack to run the complete application locally.

## 1. Run locally with Docker Compose

Prerequisites: install Docker Desktop and make sure Docker is running.

From the project root, create your private environment file:

```bash
cp .env.compose.example .env
```

Edit `.env` and set unique values for:

- `POSTGRES_PASSWORD`: long URL-safe random value (letters and numbers are easiest).
- `SECRET_KEY`: a different long random value.
- `BOOTSTRAP_CONVENER_EMAIL` and `BOOTSTRAP_CONVENER_PASSWORD`: the first convener sign-in. Password must be at least 12 characters.
- `CORS_ORIGINS`: use `http://localhost:5000` for local Docker testing. Replace it with your exact Netlify origin for deployment.
- Keep `SEED_DEMO_DATA=false` unless you are creating an isolated demo environment.

Start the app and PostgreSQL:

```bash
docker compose up --build
```

Open [http://localhost:5000](http://localhost:5000). The API and frontend share this origin. Stop with Ctrl+C. Run in the background with `docker compose up --build -d`; view logs with `docker compose logs -f app` and `docker compose logs -f db`.

PostgreSQL data is stored in the named `postgres_data` volume and survives normal container restarts and `docker compose down`. **Do not use `docker compose down -v` if you need the database data**; the `-v` option removes that volume.

The backend container applies migrations and seeds the catalog at startup. With `SEED_DEMO_DATA=false`, it does not create demo users, volunteers, or pilot event records. The bootstrap convener is created only if the email is not already present; changing its environment password later does not reset an existing account password.

## 2. Build and run the Docker image

Build from the repository root:

```bash
docker build -t tapmi-crm .
```

The image contains the built React app and Flask API. For local full-stack use, Compose is recommended because it also starts PostgreSQL and wires the database connection. The image listens on container port 5000 by default and honors a hosting platform's `PORT` environment variable.

## 3. Deploy the Flask backend and PostgreSQL

Create a PostgreSQL database on your chosen host (Render or Railway, for example). Create a Docker web service from this repository using the root `Dockerfile`. Attach the managed database and use its **private/internal connection URL** when the provider supports it.

Set these environment variables in the backend service's dashboard. Do not put actual secrets in this repository or in Netlify:

| Variable | Value |
|---|---|
| `FLASK_ENV` | `production` |
| `PORT` | Use the port assigned by the hosting provider; the image defaults to `5000`. |
| `DATABASE_URL` | Provider's PostgreSQL connection URL. |
| `SECRET_KEY` | A unique random secret, separate from the database password. |
| `SEED_DEMO_DATA` | `false` |
| `BOOTSTRAP_CONVENER_EMAIL` | First organizer's email address. |
| `BOOTSTRAP_CONVENER_PASSWORD` | Unique password, at least 12 characters. |
| `CORS_ORIGINS` | Exact Netlify origin, for example `https://your-site.netlify.app` (no trailing slash/path). |
| `PILOT_EVENT_NAME` | Optional display/default name; currently `Kala Fest`. |

The container runs migrations before starting Gunicorn. Do not add a separate database reset or drop command. Keep the PostgreSQL service and its backups enabled. If the platform provides a connection URL requiring special escaping, use the provider's documented URL format.

You can generate random secrets locally with:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Run it separately for `SECRET_KEY` and `POSTGRES_PASSWORD`. Keep the generated values in your hosting provider's private environment settings.

## 4. Deploy the frontend to Netlify

The repository's `netlify.toml` uses base directory `frontend`, build command `npm run build`, and publish directory `dist` (Netlify interprets that as `frontend/dist`). Connect the repository to Netlify and leave these build settings in place.

In Netlify's site environment variables, add:

```text
VITE_API_BASE_URL=https://YOUR-BACKEND-HOST/api/v1
```

Use the public HTTPS address of the Flask service and include `/api/v1`. This value is public and is not a secret. Set the backend's `CORS_ORIGINS` to the exact Netlify site origin. Then trigger a fresh Netlify build because Vite embeds `VITE_API_BASE_URL` at build time.

For deploy previews or a custom domain, add each actual frontend origin to the backend `CORS_ORIGINS` value as a comma-separated list, and restart/redeploy the backend. Do not use a wildcard in production.

## 5. Verify deployment

1. Open `https://YOUR-BACKEND-HOST/api/v1/health`. Confirm the JSON says `"status":"healthy"` and `"database":{"connected":true}`.
2. Open the Netlify site and check that the login page loads.
3. Sign in with the bootstrap convener account created from the backend environment variables.
4. In browser developer tools, inspect Network requests if API calls fail. Check the request URL, CORS origin, backend logs, and database health.
5. Confirm the backend database is a managed persistent PostgreSQL database, not a local SQLite file.

A successful local image build does not mean the app has been deployed. Deployment is complete only after the hosted health endpoint and site sign-in have been verified.

## 6. Environment files and data safety

- `.env.example` is for local development and enables demo data. Do not use its values in production.
- `.env.compose.example` contains placeholders only; copy it to `.env` and replace the values.
- `.env` and other environment-specific files are ignored by Git and excluded from the Docker build context.
- The local SQLite database file is ignored by Git and Docker. Existing project data is not copied into the production image.
- Production must use `SEED_DEMO_DATA=false`; demo passwords and sample CSV records are never needed for production sign-in.
