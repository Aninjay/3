---
title: "Database Schema"
project: "Cultural Committee Volunteer Management and Event Resource Allocation System"
status: "Proposed relational design"
---

# PostgreSQL Database Schema

## 1. Design goals

- Store volunteer resources, skills, events, department requirements, allocation runs, allocation versions, assignments, approvals, and audit history.
- Enforce uniqueness and relationships at the database level wherever possible.
- Preserve historical assignments when current skills or profiles change.
- Keep drafts separate from currently published assignments.
- Support one assignment per volunteer per event in the initial scope.
- Store simulated what-if data separately from real records.

The schema below is a design specification, not yet an executable migration. Finalize open policy decisions before writing migrations.

## 2. Entity relationship overview

```text
users 1---0..1 volunteer_profiles
users 1---many audit_log
volunteer_profiles many---many skills (via volunteer_skills)
volunteer_profiles 1---many volunteer_preferences
volunteer_profiles 1---many volunteer_availability
events 1---many event_requirements
departments 1---many event_requirements
event_requirements many---many skills (via requirement_skills)
events 1---many allocation_runs
events 1---many allocation_versions
allocation_versions 1---many assignments
allocation_versions 1---many allocation_approvals
events 1---1 current published_allocations pointer
```

## 3. Tables

### 3.1 `users`
Authentication identity for organizer and volunteer accounts.

| Column | Suggested type | Rules |
|---|---|---|
| `id` | BIGINT generated PK | Primary key |
| `email` | normalized TEXT | Contact address; may be shared |
| `login_id` | normalized TEXT | Unique after case folding; used for individual sign-in |
| `password_hash` | TEXT | Individually hashed; never store plaintext |
| `role` | TEXT/enum | `convener`, `co_convener`, `volunteer` |
| `status` | TEXT/enum | `pending_activation`, `active`, `locked`, `inactive` |
| `created_at`, `updated_at` | TIMESTAMPTZ | Server-generated timestamps |
| `last_login_at` | TIMESTAMPTZ nullable | Optional operational metadata |

Organizer accounts must be provisioned separately. No public endpoint may let a user self-select an organizer role.

### 3.2 `volunteer_profiles`
A volunteer account and profile are created by an organizer together.

| Column | Suggested type | Rules |
|---|---|---|
| `id` | BIGINT generated PK | Primary key |
| `user_id` | BIGINT UNIQUE FK to `users.id` | One account per volunteer |
| `student_id` | TEXT | Unique after normalization; also the volunteer's login ID |
| `full_name` | TEXT | Required |
| `email` | normalized TEXT | Contact address; may be shared |
| `active_status` | BOOLEAN | Inactive volunteers cannot be automatically or manually assigned |
| `created_by` | BIGINT FK to `users.id` | Organizer who created the record |
| `created_at`, `updated_at` | TIMESTAMPTZ | Audit timestamps |

Create the user and profile in one transaction. Enforce uniqueness on login IDs and student IDs, not contact email.

### 3.3 `skills`
Approved standardized skill catalog and pending skill suggestions.

| Column | Suggested type | Rules |
|---|---|---|
| `id` | BIGINT generated PK | Primary key |
| `name` | TEXT | Unique normalized skill name |
| `description` | TEXT nullable | Optional |
| `status` | TEXT/enum | `pending`, `approved`, `rejected`, `retired` |
| `created_by` | BIGINT FK to `users.id` | Volunteer or organizer who suggested it |
| `approved_by` | BIGINT nullable FK to `users.id` | Organizer approver |
| `approved_at` | TIMESTAMPTZ nullable | Set on approval |
| `created_at` | TIMESTAMPTZ | Timestamp |

Only approved, non-retired skills can be selected for official profiles and requirements. Volunteers may suggest skills; organizers approve/reject them.

### 3.4 `volunteer_skills`
Many-to-many relationship between profiles and approved skills.

- `volunteer_id` FK to `volunteer_profiles.id`
- `skill_id` FK to `skills.id`
- `created_at`, `updated_at`
- Optional `proficiency_level` only if the team defines how it is measured and verified.
- Composite primary key or unique constraint on (`volunteer_id`, `skill_id`).

Current profile changes must not rewrite the historical snapshot of a prior allocation run.

### 3.5 `volunteer_preferences`
Stores soft preferences, not hard eligibility rules.

- `id` PK
- `volunteer_id` FK
- `department_id` nullable FK or normalized preference type/value
- `skill_id` nullable FK if skill preference is supported
- `preference_rank` integer
- Unique constraint preventing duplicate preference rows for the same volunteer/type/value.

Finalize whether preferences mean department preference, role preference, skill preference, or a combination before implementing the table. Preferences must not outrank staffing needs.

### 3.6 `volunteer_availability`
Availability for the event, not shift-level scheduling.

- `id` PK
- `volunteer_id` FK
- `event_id` FK
- `availability_status` or `available` boolean
- optional notes
- Unique (`volunteer_id`, `event_id`) if there is one event-level availability response.

If availability windows are collected, define the exact event-level rule. Do not silently introduce shift scheduling into the initial scope.

### 3.7 `events`
- `id` PK
- `name`, `description`
- `starts_at`, `ends_at` as TIMESTAMPTZ
- `venue`
- `status`: proposed values `draft`, `upcoming`, `ongoing`, `completed`, `cancelled`, `archived`
- `created_by`, `updated_by` FKs to users
- `created_at`, `updated_at`
- Optional `version` integer for optimistic concurrency.

Define valid status transitions and who can mark an event completed/archived. Cancelled events preserve history and do not accept new allocation/publication.

### 3.8 `departments`
Reusable catalog such as IT Support, Marketing, Logistics, Hospitality, Registration, and Sponsorship.

- `id` PK
- `name` unique normalized
- `description` nullable
- `active` boolean

### 3.9 `event_requirements`
One row per event + department + role/requirement.

- `id` PK
- `event_id` FK
- `department_id` FK
- `role_name`
- `headcount` integer CHECK >= 0
- `priority` constrained to `critical`, `high`, `normal`
- `duration_hours` numeric nullable, CHECK >= 0
- `workload_value` numeric nullable, CHECK >= 0
- `workload_unit` TEXT nullable
- `service_time_value` numeric nullable
- `service_time_unit` TEXT nullable
- `peak_window_value` numeric nullable
- `peak_window_unit` TEXT nullable
- `requirement_source` constrained to `fixed_headcount` or `workload_calculation`
- `created_at`, `updated_at`

Do not use workload calculation unless units are consistent and required inputs are present. Fixed headcount is the fallback.

### 3.10 `requirement_skills`
- `requirement_id` FK to `event_requirements`
- `skill_id` FK to `skills`
- `is_mandatory` BOOLEAN
- `is_preferred` BOOLEAN optional
- Unique (`requirement_id`, `skill_id`).

For initial automatic allocation, all mandatory skills must be present. A missing mandatory skill excludes the volunteer from automatic assignment.

### 3.11 `allocation_runs`
Metadata for each algorithm run.

- `id` PK
- `event_id` FK
- `algorithm` (`greedy`, `ilp`, `comparison`, or `simulation`)
- `input_snapshot` JSONB or normalized snapshot reference
- `input_fingerprint` TEXT
- `solver_status` TEXT nullable
- `metrics` JSONB
- `result_summary` JSONB
- `run_by` FK to users
- `created_at`
- `is_simulation` BOOLEAN default false

Snapshot only the data needed to explain/reproduce the result. Avoid copying unnecessary personal information.

### 3.12 `allocation_versions`
Versioned allocation state for an event.

- `id` PK
- `event_id` FK
- `version_number` integer
- `parent_version_id` nullable FK to `allocation_versions.id`
- `source_run_id` nullable FK to `allocation_runs.id`
- `status`: `draft`, `approved`, `published`, `superseded`, `rejected`
- `created_by` FK to users
- `created_at`, `updated_at`
- `change_summary` TEXT nullable
- `row_version` integer for concurrency control

Unique (`event_id`, `version_number`). A version is not published merely because it exists. Published versions must not be mutated in place.

### 3.13 `assignments`
Assignment rows belonging to one allocation version.

- `id` PK
- `allocation_version_id` FK
- `requirement_id` FK
- `volunteer_id` FK
- `assigned_by` FK to users nullable for system-generated rows
- `assignment_source`: `greedy`, `ilp`, `manual`, `imported`
- `skill_override` BOOLEAN default false
- `override_reason` TEXT nullable
- `created_at`
- Unique (`allocation_version_id`, `volunteer_id`) to enforce at most one role per volunteer per event version.
- Check: if `skill_override = true`, `override_reason` must be non-empty.

Application validation must also verify that the requirement belongs to the same event as the allocation version, that the volunteer is active, and that hard constraints hold. If these cross-table checks are not expressible as simple constraints, enforce them in a transaction and test them.

For auditability, preserve the skill/eligibility evidence used for a run or assignment in the run snapshot or a minimal decision snapshot. Current skill changes must not rewrite history.

### 3.14 `allocation_approvals`
- `id` PK
- `allocation_version_id` FK
- `approved_by` FK to users
- `decision`: `approved`, `rejected`
- `comment` nullable
- `created_at`
- Approval applies only to the exact version reviewed. Any edit creates/updates a draft revision and requires fresh approval.

### 3.15 `published_allocations`
Current official assignment version for each event.

- `event_id` PK/FK
- `allocation_version_id` FK UNIQUE
- `published_by` FK to users
- `published_at` TIMESTAMPTZ

Before updating this pointer, verify the allocation version belongs to the same event and has valid approval. Update the pointer and publication status in one transaction. This keeps the prior published version visible until the new one is ready.

### 3.16 `audit_log`
- `id` PK
- `actor_user_id` FK nullable for system events
- `action` TEXT
- `entity_type`, `entity_id`
- `before_data`, `after_data` JSONB nullable
- `reason` TEXT nullable
- `created_at` TIMESTAMPTZ

Record creation/deactivation, manual assignment edits, skill overrides, regeneration, approvals, publication, cancellation, archive actions, and relevant security events. Avoid logging passwords, OTP values, session tokens, or unnecessary personal data.

### 3.17 `otp_challenges`
- `id` PK
- `user_id` nullable FK or `volunteer_profile_id` FK, according to activation flow
- `purpose`: activation or recovery
- `otp_hash`
- `expires_at`
- `attempt_count`
- `consumed_at`
- `created_at`

Store a hash of the OTP rather than a reusable plaintext value. OTPs must expire, be single-use, and have rate/attempt limits. Exact values and delivery provider are open configuration decisions.

## 4. Integrity rules

1. Student IDs and case-insensitive login IDs are unique; contact emails may be shared.
2. All foreign keys are valid; no orphan assignments.
3. Headcount, duration, workload, and capacity inputs cannot be negative.
4. One volunteer has at most one assignment per event allocation version.
5. Inactive volunteers cannot be assigned.
6. Automatic allocation cannot violate mandatory skills.
7. Manual skill mismatch requires a reason and audit record.
8. Draft and unapproved versions are not visible as official assignments.
9. A published version belongs to the same event as the publication pointer.
10. Published versions are immutable; edits create a new revision.
11. Use transactions for multi-row edits and publication.
12. Concurrent edits must detect stale versions rather than silently overwrite them.

## 5. Indexes to consider

- Unique index on case-insensitive user login ID and student ID; non-unique contact-email indexes.
- Indexes on `events(status, starts_at)`.
- Indexes on `event_requirements(event_id, department_id)`.
- Indexes on `volunteer_skills(skill_id, volunteer_id)`.
- Indexes on `assignments(allocation_version_id, volunteer_id)` and `assignments(volunteer_id)`.
- Indexes on `allocation_versions(event_id, version_number)`.
- Indexes on `audit_log(entity_type, entity_id, created_at)`.

Add indexes based on actual query patterns and test data, not by indiscriminately indexing every column.

## 6. Data lifecycle

- Deactivation preserves profile and assignment history.
- Current skill changes do not alter historical allocation snapshots.
- A completed event is retained; archive is read-only in normal workflows.
- Cancellation preserves the event and its records while preventing new allocations/publication according to policy.
- What-if simulation must not write scenario-only volunteers or changes into the real volunteer, event, or assignment tables.
