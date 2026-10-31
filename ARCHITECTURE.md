---
title: "System Architecture"
project: "Cultural Committee Volunteer Management and Event Resource Allocation System"
status: "Design baseline"
---

# System Architecture

## 1. Architecture principles

1. **Python owns allocation decisions.** No frontend JavaScript or SQL procedure may independently assign volunteers.
2. Keep the allocation engine independent from Flask so it can be tested from unit tests and command-line fixtures.
3. Keep the database as the persistent source of truth.
4. Treat generated allocations as drafts until approved and published by an organizer.
5. Use versioned allocation snapshots; do not overwrite published history in place.
6. Apply authorization on the server, not only by hiding UI controls.
7. Keep what-if simulation isolated from live data.
8. Make every important decision explainable and auditable.

## 2. Proposed technology stack

| Layer | Technology | Responsibility | Status |
|---|---|---|---|
| Frontend | React + Vite | Organizer portal, volunteer portal, forms, tables, review screens, charts | Proposed, not yet confirmed |
| Backend/API | Python + Flask | HTTP API, sessions, role checks, validation, orchestration | Agreed direction |
| Data processing | Pandas + NumPy | Cleaning, tabular operations, calculations, summary metrics | Agreed |
| Optimization | PuLP | ILP model and solver interface | Agreed |
| Visualization | Matplotlib | Required/allocated, vacancies, utilization, algorithm comparison | Agreed |
| Optional charts | Seaborn | Heatmaps/distributions where useful | In original proposal; optional |
| Database | PostgreSQL | Persistent relational storage | Agreed direction |
| DB driver | psycopg | Parameterized PostgreSQL access and transactions | Agreed direction |
| Email | SMTP or approved email provider | OTP and recovery delivery | Open decision |

## 3. Logical architecture

```text
[Browser: Organizer / Volunteer]
              |
              | HTTPS / JSON requests
              v
         [Flask API]
          /    |     \
         /     |      \---- [Email provider: OTP/recovery]
        /      |
       v       v
[Application] [Python Allocation Service]
[services]      |-- validation / cleaning
                |-- eligibility / capacity
                |-- greedy baseline
                |-- PuLP ILP optimizer
                |-- metrics / shortage explanations
                |-- what-if simulator
                |-- comparison / recommendations
                       |
                       v
                 [PostgreSQL]
                 via psycopg
```

The diagram is logical, not a mandate to deploy separate servers. For a first local demo, the frontend, Flask app, and PostgreSQL can run on one development machine. Production deployment details are not decided.

## 4. Component responsibilities

### 4.1 Frontend
- Render role-appropriate screens.
- Collect event requirements, volunteer profile skills, preferences, and scenario inputs.
- Display draft allocation results, vacancies, eligible unassigned volunteers, warnings, reports, and charts.
- Ask for confirmation before regeneration or publication.
- Never calculate or silently change official assignments in the browser.
- Never assume that a hidden button is sufficient authorization.

### 4.2 Flask API
- Authenticate sessions and enforce role permissions.
- Validate incoming request schemas.
- Call application services and the Python allocation service.
- Use transactions for manual edits, approvals, publication, and version pointer changes.
- Return structured JSON with consistent errors.
- Avoid embedding algorithm logic directly in route functions.

### 4.3 Python allocation service
- Accept validated data structures for one event.
- Normalize/validate inputs and apply hard eligibility rules.
- Calculate workload-based or fixed staffing requirements.
- Run greedy and ILP methods using the agreed policy.
- Return proposed assignments, vacancies, metrics, solver status, and explanations.
- Never publish or persist assignments by itself; Flask/application services control persistence and workflow state.

### 4.4 Data-access layer
- Use psycopg and parameterized SQL.
- Keep SQL/data access out of allocation scoring modules.
- Use explicit transaction boundaries.
- Protect uniqueness and referential integrity with database constraints.

### 4.5 Reporting
- Produce department and individual views from saved allocation versions.
- Use Matplotlib for required-vs-allocated, vacancy, utilization, and algorithm comparison plots.
- Use Seaborn only if a skill heatmap or distribution plot improves analysis.
- Label assumed/simulated data clearly.

## 5. Core request flows

### 5.1 Generate allocation
1. Organizer requests an allocation run for an event.
2. Flask checks role, event status, and input version.
3. Data-access code reads the event requirements, volunteers, approved skills, event availability/capacity, and preferences.
4. The engine validates the snapshot and computes eligibility.
5. Greedy and/or ILP methods run against that same snapshot.
6. Metrics and explanations are generated.
7. Flask stores the run and proposed allocation as a new draft version in a transaction.
8. API returns the draft summary to the organizer.
9. The draft remains invisible as an official assignment to volunteers.

### 5.2 Manual edit
1. Organizer edits a draft assignment.
2. Server checks current version and hard constraints.
3. If a mandatory skill is missing, return a warning that requires explicit confirmation and a reason.
4. Inactive volunteers and duplicate assignments remain blocked.
5. Persist the edit and audit record transactionally.
6. Recalculate staffing totals and invalidate approval if the version was approved.
7. If editing an already published allocation, create a new draft revision; do not mutate the currently published version.

### 5.3 Publish
1. Organizer requests publication of a specific approved version.
2. Server verifies the version belongs to the event, has valid approval, and has not changed since approval.
3. In one transaction, update the current published-version pointer and record publication metadata.
4. Volunteers see the new version only after transaction success.
5. Preserve the prior published version as history.

### 5.4 What-if simulation
1. Organizer selects baseline inputs and scenario changes.
2. Create an in-memory or isolated scenario copy.
3. Rerun capacity and allocation logic.
4. Return side-by-side metrics.
5. Do not write scenario changes to real volunteer profiles, event requirements, assignments, or the published-version pointer.

## 6. Suggested Python package layout

```text
backend/
  app/
    __init__.py
    config.py
    routes/
      auth.py
      volunteers.py
      skills.py
      events.py
      requirements.py
      allocations.py
      reports.py
      simulations.py
    services/
      auth_service.py
      event_service.py
      allocation_service.py
      publication_service.py
      report_service.py
    repositories/
      users_repository.py
      volunteers_repository.py
      events_repository.py
      allocations_repository.py
    allocation/
      data_loader.py
      validation.py
      eligibility.py
      capacity.py
      greedy.py
      ilp_optimizer.py
      metrics.py
      shortages.py
      compare.py
      simulator.py
      recommendations.py
      schemas.py
    db/
      connection.py
      migrations/
    tests/
frontend/                 # only if React + Vite is confirmed
  src/
    pages/
    components/
    services/
    types/
```

This is a proposed structure, not an instruction to generate every file at once. Build in small verified increments.

## 7. Data and trust boundaries

- Browser input is untrusted.
- User role and volunteer identity must come from the authenticated server-side session.
- Email OTPs and passwords are secrets; never log them.
- Database credentials and email credentials belong in environment variables or an appropriate secret store, not Git.
- Only approved skills are selectable for official profile/requirement use.
- A draft allocation is not an official assignment.
- Simulation results are not real assignments.
- Historical published versions must remain immutable.
- Audit logs should be append-only at the application level and should not store unnecessary sensitive data.

## 8. Reliability and concurrency

- Use transactions for changes that affect several assignments or the published pointer.
- Add optimistic concurrency control, such as a version number or `updated_at` check, to detect stale organizer edits.
- Approval must reference an exact allocation version.
- If event requirements or volunteer eligibility change after a run, mark the run as based on an older snapshot and require a deliberate refresh/regeneration before publication.
- A failed ILP run must return an explicit status. Do not treat a solver error or incomplete result as an approved allocation.
- Backups and restore procedures must be documented before real committee data is used.

## 9. Unresolved architecture decisions

- Confirm frontend framework.
- Choose email OTP provider and recovery approach.
- Decide database migration tool and deployment environment.
- Set expected user count/performance target.
- Decide whether charts are rendered as static images from Matplotlib or computed by backend and displayed by the frontend.
