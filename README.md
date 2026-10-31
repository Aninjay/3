# Cultural Committee Volunteer Management and Event Resource Allocation System
**Pilot Event:** Kala Fest  
**Institution:** T. A. Pai Management Institute (TAPMI), Manipal  
**Architecture:** Python + Flask + PuLP ILP Optimizer + PostgreSQL/SQLite + React + Vite  
**Visual System:** Minimal White & Warm Orange (`#E8752E`)

For beginner-friendly Docker, PostgreSQL, backend-hosting, and Netlify deployment steps, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

---

## 1. System Overview

This web-based decision-support system manages cultural committee volunteers and allocates them to departments and roles for cultural events (piloted with Kala Fest).

### Key Capabilities
- **Volunteer Management:** Register volunteers with unique University Student IDs, track approved skills, manage availability and active status.
- **Volunteer Self-Service Portal:** View published event assignments, manage approved skills catalog selections, and view assignment history.
- **Department Requirements & Staffing Capacity:** Define staffing requirements using either fixed headcount or the workload-based capacity formula:
  $$\text{Required Staff} = \left\lceil \frac{\text{Workload} \times \text{Service Time}}{\text{Peak Window}} \right\rceil$$
- **Real Python Allocation Engine:**
  - **Greedy Baseline:** Deterministic priority-first matching (Critical $\rightarrow$ High $\rightarrow$ Normal) with skill fit and preference scoring.
  - **PuLP ILP Optimizer:** Integer Linear Programming with binary decision variables $x_{v,p}$, respecting mandatory skills, volunteer uniqueness, and a balanced multi-criteria objective.
  - **Side-by-Side Algorithm Comparison:** Evaluates both algorithms on the exact same input snapshot and reports filled positions, vacancies, coverage, preference satisfaction, and runtimes.
- **Shortage Diagnostics & Evidence-Based Recommendations:** Identifies available unassigned volunteers as reallocation candidates and pinpoints genuine skill gaps.
- **Allocation Lifecycle & Versioning:** Enforces Draft $\rightarrow$ Review $\rightarrow$ Approval $\rightarrow$ Atomic Publication. Volunteers never see draft allocations.
- **What-If Scenario Simulator:** Tests surge demand, volunteer dropouts, and simulated cohorts on isolated deep copies without mutating live records (`Simulation · Not published`).
- **Campus Login Interface:** Fully opaque login panel rendered over the softened TAPMI campus background image (`Icon.jpg`).

---

## 2. Technology Stack

- **Backend:** Python 3.10+ / 3.13, Flask 3.1+, Flask-CORS, Werkzeug
- **Optimization:** PuLP 2.9.0 (CBC solver for binary integer programming)
- **Data & Numerical Processing:** NumPy, Pandas-compatible tabular processing
- **Visualization:** Matplotlib (rendered on backend without browser overhead)
- **Database:** PostgreSQL (with `psycopg` and pure-python `pg8000` driver support) and zero-config local standalone SQLite database support
- **Roster exports:** CSV and multi-sheet Excel files for the current published allocation
- **Frontend:** React 18, Vite 5, Lucide Line Icons, Custom White & Warm Orange Design System

---

## 3. Local Setup Instructions

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ and npm
- PostgreSQL (optional for local development; system includes automatic zero-config standalone fallback)

### Step 1: Clone & Configure Environment Variables
Copy the example environment configuration:
```bash
cp .env.example .env
```
Default `.env` settings:
```ini
FLASK_ENV=development
PORT=5001
SECRET_KEY=tapmi-cultural-committee-dev-secret-key-2026
DATABASE_URL=sqlite:///backend/cultural_committee.db
OTP_DELIVERY_MODE=development
PILOT_EVENT_NAME=Kala Fest
```
*(To use PostgreSQL, set `DATABASE_URL=postgresql://user:password@localhost:5432/cultural_committee`)*

---

### Step 2: Install Backend Dependencies
```bash
pip install -r backend/requirements.txt
```
*(Dependencies include: `flask`, `flask-cors`, `gunicorn`, `openpyxl`, `pulp==2.9.0`, `numpy`, `pg8000`, `pytest`, `werkzeug`, `matplotlib`)*

---

### Step 3: Run Database Migrations & Seed Pilot Data
The server applies migrations and seeds the catalog and pilot data at startup. The local `.env.example` enables demo data; production defaults to no demo accounts or sample records.

---

### Step 4: Install Frontend Dependencies & Build
In PowerShell/Bash:
```bash
cd frontend
npm install
npm run build
cd ..
```

---

### Step 5: Start the Full-Stack Application

#### Option A: Unified Full-Stack Server (Recommended)
Because the Flask application serves both the API and the compiled React production frontend directly:
```bash
python backend/run.py
```
Open **[http://localhost:5001](http://localhost:5001)** in your browser.

### Production-style Docker Compose deployment

The Compose stack builds the React frontend into the Flask image and runs Flask with Gunicorn beside PostgreSQL. PostgreSQL data persists in a named volume. The app waits for the database health check, applies migrations at startup, and then starts the web server. The API rejects startup if `SECRET_KEY` is missing in production, and Compose requires an explicit allowed frontend origin.

Create a private environment file and replace all placeholders before starting:

```powershell
Copy-Item .env.compose.example .env
```

Use unique secrets. `POSTGRES_PASSWORD` should be URL-safe because it is included in `DATABASE_URL`. Set `CORS_ORIGINS` to the exact public frontend origin (for example `https://your-site.netlify.app`, with no path). Keep `SEED_DEMO_DATA=false` in production. Set both `BOOTSTRAP_CONVENER_EMAIL` and `BOOTSTRAP_CONVENER_PASSWORD` to provision the first organizer account. The catalog is seeded, while predictable demo logins, volunteers, and Kala Fest sample records remain disabled. Set `SEED_DEMO_DATA=true` only for an isolated demo environment; it creates the known test accounts and sample records.

Generate secret values with `python -c "import secrets; print(secrets.token_hex(32))"` (run it once for each secret). Use that value for `POSTGRES_PASSWORD` and a separate random value for `SECRET_KEY`. Set a unique organizer password with at least 12 characters.

Start the services:

```powershell
docker compose up --build -d
```

Open **[http://localhost:5000](http://localhost:5000)**. Follow service logs with `docker compose logs -f app`, and stop the stack with `docker compose down`. `docker compose down -v` also deletes the persistent database volume.

The Compose stack provides a production-style single-host deployment. Before exposing it to committee users, configure HTTPS at a reverse proxy, back up PostgreSQL, and provision unique credentials. Legacy OTP activation endpoints are not used by the login interface.

#### Option B: Standalone Vite Dev Server
Run the Flask API backend in one terminal:
```bash
python backend/run.py
```
In a second terminal, start the Vite dev server:
```bash
cd frontend
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser (API calls are automatically proxied to port 5001).

---

## 4. Running Automated Tests

Run the complete test suite with pytest:
```bash
python -m pytest backend/tests
```
15 test suites verify:
1. `test_capacity_calculation`: Unit formula `ceil(Workload × Service Time ÷ Peak Window)`.
2. `test_eligibility_hard_rules`: Inactive volunteers, missing mandatory skills, duplicate event assignment blocked.
3. `test_worked_example_five_positions_four_volunteers`: 5 positions, 4 volunteers $\rightarrow$ exactly 4 assignments, 1 vacancy, 0 duplicates.
4. `test_compare_algorithms`: Identical snapshot comparison between Greedy and ILP.
5. `test_simulator_does_not_mutate_baseline`: Verifies deep copy isolation.
6. `test_health_endpoint`: Checks database connection and pilot event configuration.
7. `test_auth_login_convener_and_co_convener`: Equal permissions for Convener and Co-convener.
8. `test_unauthenticated_protected_route_fails`: 401 Unauthorized verification.
9. `test_volunteer_forbidden_from_organizer_endpoints`: 403 Forbidden role boundary enforcement.
10. `test_duplicate_student_id_and_email_rejected`: 409 Conflict integrity protection.
11. `test_volunteer_activation_otp_workflow`: OTP challenge, attempt limiting, verification, password creation, and volunteer login.
12. `test_full_allocation_lifecycle_and_publication`: Run $\rightarrow$ Draft $\rightarrow$ Approval $\rightarrow$ Publication $\rightarrow$ Volunteer sees only their published assignment.
13. `test_manual_edit_skill_override_requires_reason`: Skill mismatch warning, required non-empty reason, and audit trail.
14. `test_archived_event_modifications_blocked`: 409 Conflict when editing archived events.
15. `test_simulation_does_not_mutate_live_data`: Live database records unchanged after running scenarios.

---

## 5. Demo Credentials

The database comes pre-seeded with test accounts:

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Convener** | `convener@tapmi.edu.in` | `convener123` | Full organizer authority |
| **Co-convener** | `coconvener@tapmi.edu.in` | `coconvener123` | Full organizer authority (equal permissions) |
| **Volunteer (Aarohi Anchal)** | `volunteer@tapmi.edu.in` (shared login email) | `volunteer123` | Published assignments, skills catalog |
| **Volunteer (Anaya Rupani)** | `volunteer@tapmi.edu.in` (shared login email) | `volunteer124` | Published assignments, skills catalog |

*(Quick prefill buttons are provided on the login page for instantaneous demo access)*

---

## 6. Troubleshooting

- **PowerShell Execution Policy Error on npm:**  
  On Windows systems where script execution is restricted, run `npm.cmd` instead of `npm`, e.g.:
  ```powershell
  npm.cmd install
  npm.cmd run build
  ```
- **Windows Application Control (AppLocker) DLL Blocking:**  
  The system uses pure-Python `pg8000` for PostgreSQL connectivity and pure-Python `pulp 2.9.0` with CBC solver, avoiding unsigned C/Rust DLL blocks in Windows user AppData directories.
