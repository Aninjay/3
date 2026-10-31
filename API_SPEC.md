---
title: "API Specification"
project: "Cultural Committee Volunteer Management and Event Resource Allocation System"
status: "Proposed REST API contract"
---

# Flask API Specification

## 1. Conventions

- Base path: `/api/v1`
- Format: JSON request/response bodies.
- Authentication: secure server-side session or another explicitly chosen secure mechanism. Do not trust a role or user ID sent in a request body.
- Role names: `convener`, `co_convener`, `volunteer`.
- Convener and Co-convener have equal permissions.
- All organizer-only routes must enforce authorization on the server.
- All database writes must validate input and use transactions where several rows/state changes must remain consistent.
- This is a proposed contract. Exact implementation details can change, but access rules and workflow semantics must not.

## 2. Standard response and error shape

Success:
```json
{
  "data": {},
  "meta": {}
}
```

Error:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request could not be processed.",
    "details": {}
  }
}
```

Suggested status codes:
- `200` successful read/update/action
- `201` created
- `204` successful operation with no body
- `400` malformed request
- `401` unauthenticated
- `403` authenticated but unauthorized
- `404` not found or not accessible
- `409` conflict, duplicate ID, stale version, invalid workflow transition
- `422` well-formed request that violates business validation
- `429` rate limited
- `500` unexpected server error without leaking secrets

Never return stack traces, password hashes, OTP hashes, tokens, or other secret values to clients.

## 3. Authentication and account activation

### `POST /auth/login`
Authenticates a user.
- Input: `{ "login_id": "...", "password": "..." }`. Existing organizer email login IDs remain valid.
- Contact emails can be shared; when an email matches multiple accounts, require the person's unique login ID.
- Result: authenticated session and minimal user identity/role.
- Do not allow the client to choose or elevate its role.

### `POST /auth/logout`
Invalidates the session.

### `POST /auth/activation/request`
Legacy compatibility endpoint for OTP activation. New volunteer accounts are created with a unique student-ID login and password by an organizer; this endpoint is not used by the login interface.
- Input: `{ "student_id": "...", "email": "..." }` or a non-enumerating invitation token, depending on final design.
- Apply rate limits and avoid revealing whether arbitrary IDs/emails exist.
- The OTP is sent by the configured email provider; never return the OTP in the API response.

### `POST /auth/activation/verify`
Verifies the activation OTP.
- Input: activation reference + OTP.
- Reject incorrect, expired, consumed, or over-limit OTPs.

### `POST /auth/activation/complete`
Sets the volunteer password after successful verification.
- Input: activation reference + password.
- Activate the account only after successful verification and password setup.

### `POST /auth/password-reset/request`
Requests recovery without revealing whether the account exists.

### `POST /auth/password-reset/complete`
Completes recovery with a valid, single-use recovery challenge.

Legacy OTP expiry, retry limits, delivery provider, and recovery rules apply only if the compatibility endpoints are enabled.

## 4. Volunteer and profile endpoints

### `POST /volunteers` — organizer only
Creates a volunteer account and profile.
- Input: full name, student ID, optional personal contact email, and password.
- The server assigns the configured shared volunteer login email. Reject duplicate student IDs/login IDs and passwords already used by another account under that shared email.
- Hash the password and activate the account in the same transaction.

### `GET /volunteers` — organizer only
Lists/searches volunteers and relevant profile/skill/status fields. Paginate results.

### `GET /volunteers/{volunteer_id}` — organizer only
Reads one volunteer profile.

### `PATCH /volunteers/{volunteer_id}` — organizer only
Updates permitted administrative profile fields or active status. Deactivation must preserve history and be audited.

### `PUT /volunteers/{volunteer_id}/password` — Convener/Co-convener only
Sets or resets the volunteer's password, creating an account for an imported volunteer profile if needed. Enforce a unique password among accounts using the shared volunteer login email. Store only a password hash and write an audit event without the password value.

### `PUT /core-committee/members/{user_id}/password` — Convener/Co-convener only
Sets or resets the member's password for the shared `core@tapmi.edu.in` login. Enforce a unique password among Core Committee accounts using that email, store only a password hash, and audit without the password value.

### `GET /me`
Returns the authenticated user's minimal own profile.

### `GET /me/skills` — volunteer
Returns the caller's own approved skills.

### `PUT /me/skills` — volunteer
Replaces or updates the caller's skill selections using approved catalog IDs. Reject duplicates and unapproved skills. The server identifies the profile from the session; do not accept a different volunteer ID as authority.

## 5. Skills endpoints

### `GET /skills`
Returns approved, non-retired skills available for selection. Organizers may request additional statuses.

### `POST /skills/suggestions` — authenticated user
Submits a new skill suggestion.
- Input: name and optional description.
- New suggestion is pending and is not selectable for official allocation until approved.
- Prevent duplicate normalized skill names.

### `GET /skills/suggestions` — organizer only
Lists pending suggestions.

### `POST /skills/suggestions/{skill_id}/approve` — organizer only
Approves a pending suggestion and records approver/time.

### `POST /skills/suggestions/{skill_id}/reject` — organizer only
Rejects a pending suggestion and records the action.

## 6. Event and requirement endpoints

### `GET /events`
Returns events the caller is permitted to view. Define public volunteer-facing event fields separately from private organizer fields. Support sorting and pagination. New/relevant events should appear first according to the finalized sort rule.

### `POST /events` — organizer only
Creates an event with name, description, dates, venue, and status.

### `GET /events/{event_id}`
Returns the event fields permitted for the current role.

### `PATCH /events/{event_id}` — organizer only
Edits event metadata. Reject invalid status transitions and edits to archived events.

### `POST /events/{event_id}/cancel` — organizer only
Marks an event cancelled, prevents new allocation/publication, and preserves history.

### `POST /events/{event_id}/archive` — organizer only
Archives an eligible completed event. Read-only afterward through ordinary workflows. Exact lifecycle policy must be finalized.

### `GET /events/{event_id}/requirements` — organizer only
Returns staffing requirements.

### `PUT /events/{event_id}/requirements` — organizer only
Creates/replaces event requirement rows, including department, role, headcount, priority, mandatory/preferred skills, duration, and workload inputs where applicable.
- Validate nonnegative values and approved skill IDs.
- If the event has an approved or published allocation, record that a new allocation revision is required; do not silently change the published snapshot.

### `POST /events/{event_id}/requirements/calculate` — organizer only
Calculates proposed headcount from workload inputs using consistent units, or validates a fixed headcount. Return the formula inputs and output for transparency. Do not persist until the organizer confirms the requirement.

## 7. Allocation endpoints

### `POST /events/{event_id}/allocations/runs` — organizer only
Runs the selected algorithm(s).
- Input example:
```json
{
  "algorithms": ["greedy", "ilp"],
  "compare": true
}
```
- Server fetches a consistent input snapshot.
- Return run IDs, solver status, metrics, vacancies, and a draft version ID.
- This endpoint must not publish results.

### `GET /events/{event_id}/allocations`
Returns permitted allocation versions and their states to organizers.

### `GET /allocations/{allocation_version_id}` — organizer only
Returns the draft/version details, assignments, vacancies, metrics, warnings, and run provenance.

### `PATCH /allocations/{allocation_version_id}/assignments` — organizer only
Applies a manual assignment change to a draft revision.
- Input should specify operation (`add`, `remove`, `replace`) and required IDs.
- Include expected version/row version for stale-update detection.
- If mandatory skill mismatch occurs, first return a warning/confirmation response; require a non-empty reason to proceed.
- Block inactive volunteers and duplicate assignments.
- Record before/after data and actor in audit history.
- Editing an approved version invalidates approval. Editing a published version creates a new draft revision.

### `POST /allocations/{allocation_version_id}/regenerate` — organizer only
Explicitly regenerates an allocation after confirmation.
- Input includes confirmation flag and algorithm(s).
- Must create a new run/draft; never silently erase a published version.
- Preserve manual edits unless this explicit action is requested.
- Audit the action.

### `POST /allocations/{allocation_version_id}/approve` — organizer only
Approves the exact version reviewed.
- Reject if stale, changed after review, or invalid.
- Record approver and timestamp.
- Approval is invalidated by any subsequent edit.

### `POST /allocations/{allocation_version_id}/reject` — organizer only
Rejects a version with an optional reason.

### `POST /allocations/{allocation_version_id}/publish` — organizer only
Publishes an approved version.
- Transactionally update the current published pointer.
- Keep the previous published version visible until this transaction succeeds.
- Reject if approval is absent/stale or the version belongs to another event.

### `GET /me/assignments`
Returns only the authenticated volunteer's own assignments from currently published versions, with event, date, venue, department, and role.

### `GET /me/assignment-history`
Returns the caller's own permitted historical assignments. Must not expose the complete roster.

## 8. Reporting endpoints

### `GET /events/{event_id}/reports/staffing` — organizer only
Returns required, allocated, vacant, coverage, department priority, and skill gaps.

### `GET /events/{event_id}/reports/underutilization` — organizer only
Returns eligible unassigned volunteers and a clear explanation of the eligibility/selection factors. Do not imply a volunteer is suitable if mandatory skill/availability rules are not met.

### `GET /events/{event_id}/reports/algorithm-comparison` — organizer only
Returns greedy vs. ILP metrics from comparable input snapshots, including filled positions, vacancies, priority coverage, skill fit, preference fit, fairness metric, solver status, and runtime where available.

### `GET /events/{event_id}/reports/recommendations` — organizer only
Returns evidence-based recommendations with reasons and supporting counts. The organizer decides whether to act.

## 9. What-if simulator endpoints

### `POST /events/{event_id}/simulations` — organizer only
Creates a scenario copy and runs selected allocation algorithms.
- Input may adjust attendance, volunteer count/availability, duration, headcount/requirements, or priorities.
- Simulated candidates, if supported, must be explicitly labelled.
- Return baseline and scenario metrics.
- Must not change live profiles, event requirements, assignment versions, or published pointer.

### `GET /simulations/{simulation_id}` — organizer only
Returns scenario inputs and results. Simulation storage policy is open; if persisted, keep it separate from official allocation records.

## 10. Authorization summary

| Operation | Convener | Co-convener | Volunteer |
|---|---:|---:|---:|
| Manage events and requirements | Yes | Yes | No |
| Create/deactivate volunteer records | Yes | Yes | No |
| Submit/update own skills | If also a volunteer profile | If also a volunteer profile | Yes |
| Suggest a skill | Yes | Yes | Yes |
| Approve skill suggestions | Yes | Yes | No |
| Generate/edit/approve/publish allocation | Yes | Yes | No |
| View full roster/private profiles | Yes | Yes | No |
| View own published assignments/history | If assigned as volunteer | If assigned as volunteer | Yes |

## 11. API implementation rules

- Validate all inputs server-side.
- Use parameterized database queries.
- Enforce ownership checks on every personal endpoint.
- Apply rate limits to login, OTP, and recovery endpoints.
- Use generic responses where account enumeration is a risk.
- Never expose draft assignments as official assignments.
- Record audit events for privileged state changes.
- Use consistent transaction handling for versioning and publication.
