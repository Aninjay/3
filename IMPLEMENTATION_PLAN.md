---
title: "Implementation Plan"
project: "Cultural Committee Volunteer Management and Event Resource Allocation System"
status: "Phased plan"
---

# Implementation Plan

## 1. Implementation rule

Build in small, testable increments. Do not ask a coding agent to generate the entire application in one unverified pass. The Python allocation engine must be independently testable and must remain the sole source of automatic assignment decisions.

## 2. Repository layout

Proposed layout:

```text
project-root/
  PRD.md
  ARCHITECTURE.md
  DATABASE_SCHEMA.md
  API_SPEC.md
  ALLOCATION_ALGORITHM.md
  UI_UX_SPEC.md
  IMPLEMENTATION_PLAN.md
  TEST_PLAN.md
  backend/
  frontend/                  # if React + Vite is confirmed
  data/
    samples/
  docs/
  .env.example
  .gitignore
  requirements.txt           # or pyproject.toml, choose one
```

Do not put real volunteer data, passwords, OTPs, database credentials, email secrets, or `.env` in Git. Sample data must be clearly labelled as simulated.

## 3. Proposed backend dependencies

Core:
- Flask
- psycopg
- Pandas
- NumPy
- PuLP
- Matplotlib
- Seaborn (optional visualization)
- A suitable password-hashing/session solution, such as Werkzeug utilities for password hashing
- A test framework such as pytest

A database migration tool and email provider/library must be selected before those modules are implemented. Pin tested dependency versions once the environment is created; do not guess versions in this planning file.

Frontend:
- React + Vite is proposed but not confirmed.
- If selected, use a typed API client/service layer and keep business rules on the backend.

## 4. Milestones

### Phase 0: Close blocking design decisions
- Confirm frontend framework.
- Define objective weights, priority policy, and measurable fairness metric.
- Define event-level availability and maximum-hours rules.
- Decide whether skill proficiency/experience is captured and how it is verified.
- Select email OTP provider and configure expiry/retry/recovery policy.
- Define event lifecycle, sorting, completion, archive, and cancellation behavior.
- Decide exact simulator controls.

**Exit:** unresolved decisions affecting the next phase are documented and not contradicted by other files.

### Phase 1: Development environment and skeleton
- Create repository and Python virtual environment.
- Choose dependency manifest (`requirements.txt` or `pyproject.toml`).
- Create Flask application factory/configuration.
- Add environment-based configuration and `.env.example`.
- Create basic health endpoint and test command.
- Confirm PostgreSQL is reachable.

**Exit:** app starts locally; configuration/secrets are not committed; smoke test passes.

### Phase 2: PostgreSQL schema and data access
- Create migrations for core tables and constraints.
- Add a small simulated seed dataset for skills, departments, volunteers, and one event.
- Add psycopg connection/transaction handling and repository functions.
- Test unique IDs, foreign keys, assignment uniqueness, and publication pointer integrity.

**Exit:** database can be created reproducibly from migrations; integrity tests pass.

### Phase 3: Authentication and authorization
- Provision organizer accounts outside public registration.
- Implement organizer-created volunteer records.
- Implement email OTP activation, password hashing, session handling, logout, and recovery.
- Add role and ownership checks to all protected routes.
- Add rate limits and safe error responses.

**Exit:** activation and role tests pass; volunteers cannot access organizer endpoints or another volunteer's data.

### Phase 4: Volunteer profiles, skills, events, requirements
- Implement profile and approved skill catalog.
- Implement skill suggestion/approval.
- Implement event and department requirement CRUD.
- Implement fixed headcount and workload-based calculator with unit validation.
- Add availability/capacity fields only after their rules are confirmed.
- Implement event lifecycle restrictions.

**Exit:** data validation, role checks, and archive/cancel rules pass.

### Phase 5: Allocation input pipeline and greedy baseline
- Build cleaning/validation and eligibility modules.
- Build the event-level input snapshot.
- Implement deterministic greedy baseline.
- Return vacancies, eligible unassigned volunteers, and reasons.
- Add unit tests with hand-calculated fixtures.

**Exit:** no automatic mandatory-skill violations, no inactive assignments, no duplicate event assignment; vacancy counts are correct.

### Phase 6: ILP optimizer and algorithm comparison
- Implement the PuLP model and documented objective.
- Add constraints for positions, volunteers, mandatory skills, availability, capacity, and no double-booking.
- Handle solver statuses and failures.
- Compare greedy and ILP using the same snapshot.
- Add Matplotlib charts and metrics.

**Exit:** test fixtures prove constraints; results and trade-offs are reproducible and explained.

### Phase 7: Allocation review, manual edits, audit, versioning
- Build draft allocation views.
- Implement manual add/remove/replace.
- Require reason for skill mismatch override.
- Add audit log entries.
- Implement explicit regeneration confirmation.
- Implement approval invalidation and publication pointer transactions.
- Add optimistic concurrency checks.

**Exit:** version lifecycle, audit, and publication tests pass.

### Phase 8: Dashboards and reports
- Build organizer dashboard, department/individual views, volunteer assignment dashboard.
- Add staffing/shortage/underutilization reports.
- Add charts with labels and simulated-data disclosure.

**Exit:** displayed counts match saved version data; volunteers only see their own published assignments.

### Phase 9: What-if simulator and recommendations
- Copy baseline input into isolated scenario data.
- Add supported scenario controls.
- Compare baseline and scenario metrics.
- Generate explainable recommendations.
- Verify no live-data mutation.

**Exit:** simulation is isolated and recommendations are backed by result metrics.

### Phase 10: End-to-end quality and demo
- Run unit, integration, authorization, concurrency, and regression tests.
- Test backup/restore process.
- Prepare a clearly labelled demo dataset based on confirmed or simulated values.
- Create a process flowchart and project report.
- Rehearse the live Kala Fest-style demonstration.

**Exit:** acceptance criteria in `TEST_PLAN.md` pass; limitations and assumptions are documented.

## 5. Data collection plan

Primary data should come from Cultural Committee records, volunteer forms, and interviews around Kala Fest, as the original proposal states. Collect only fields needed for staffing decisions:
- volunteer ID, name, skills, availability, maximum working hours, experience, preference;
- department/role, priority, capacity, duration, required skills, workload or fixed staffing requirement.

Clean and standardize skills and department names, remove duplicates, validate ranges and units, and document missing values. Never present assumed or simulated values as collected facts.

## 6. Git and code-quality workflow

- Commit small logical changes.
- Use branches or pull requests if working with multiple contributors.
- Add tests alongside each business module.
- Run formatter/linter and tests before considering a phase complete.
- Keep configuration and secrets outside source control.
- Do not mark a feature complete just because its page renders; verify data persistence, permissions, edge cases, and audit behavior.
- Keep the design documents synchronized when a requirement is deliberately changed.

## 7. Demo sequence

1. Organizer logs in.
2. Organizer creates/opens Kala Fest event and department requirements.
3. Show volunteer/skill dataset and indicate which data is real vs simulated.
4. Run capacity calculation.
5. Generate greedy baseline and ILP result.
6. Compare staffing coverage, vacancies, skill gaps, and eligible unassigned volunteers.
7. Demonstrate an honest vacancy.
8. Manually assign an eligible unassigned volunteer or leave the vacancy open.
9. Demonstrate skill-mismatch warning/reason if appropriate.
10. Approve and publish.
11. Log in as a volunteer and show only that volunteer's published assignment.
12. Run a what-if scenario and prove live data remains unchanged.
13. Show audit/version history and dashboard charts.

## 8. Immediate next action

Close only the blocking decisions in Phase 0, then start Phase 1. Do not begin by writing the full ILP model or by generating all frontend/backend files at once.
