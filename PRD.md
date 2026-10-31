---
title: "Product Requirements Document"
project: "Cultural Committee Volunteer Management and Event Resource Allocation System"
status: "Design baseline"
---

# Product Requirements Document (PRD)

## 1. Purpose

Build a web-based decision-support system for the Cultural Committee, piloted with Kala Fest. The system records volunteer capabilities and event staffing requirements, then uses **Python** to recommend event-specific volunteer assignments. It must help committee leaders distinguish a genuine shortage of suitable volunteers from poor utilization of people who are already available.

This is a decision-support tool. The Convener and Co-convener retain final authority over assignments.

## 2. Problem statement

For events such as Kala Fest, Rubaru, and inter-institute events, departments including Sponsorship, Marketing, Logistics, IT Support, Hospitality, and Registration need volunteers. Staffing decisions may rely on availability or personal familiarity, while skills, experience, preferences, capacity, and department demand are not held in one consistent place.

The system must answer:
- Who is available, and what can they do?
- What does each department need?
- Who is eligible for each role?
- Which positions are filled or vacant?
- Are capable volunteers left unassigned or underutilized?
- Can existing volunteers meet the requirement, or is a real skill/personnel gap present?
- How do the greedy baseline and ILP optimizer compare?

## 3. Goals

1. Maintain a standardized volunteer resource database.
2. Capture event, department, role, skill, priority, capacity, and staffing requirements.
3. Calculate required staffing from workload when usable workload data exists, or accept a fixed headcount.
4. Apply consistent eligibility checks.
5. Generate a transparent greedy baseline and a Python-based Integer Linear Programming (ILP) allocation using PuLP.
6. Report required, allocated, and vacant positions honestly.
7. Show eligible unassigned volunteers and explain why vacancies remain.
8. Let organizers manually edit allocations, approve them, and publish them.
9. Preserve manual edits unless an organizer explicitly regenerates the allocation.
10. Support isolated what-if scenarios without changing live event data.
11. Produce individual and department views, dashboard charts, and evidence-based recommendations.
12. Keep historical events, published allocation versions, and audit history.

## 4. Out of scope for the initial version

- General company-wide workforce planning. This is future scope.
- Shift-level scheduling or assigning one volunteer to multiple shifts. Initial rule: at most one role/assignment per volunteer per event.
- Automatic recruitment, contacting students, or assigning unregistered students without the organizer's intervention.
- Fully autonomous final decisions. Organizers must review and publish.
- Treating simulated data as real committee data.
- A promise that the optimizer always fills every position or always beats the baseline on every metric.

## 5. User roles

### Convener and Co-convener
They have equal permissions. They can manage events and requirements, create/deactivate volunteer records, approve skill suggestions, run allocation, manually edit assignments, review reports, approve and publish allocation versions, and archive completed events according to the finalized lifecycle policy.

### Volunteer
An organizer creates a volunteer account with the shared volunteer login email and an individual password. The password identifies which account is signing in; volunteer passwords must be distinct under the shared email. A volunteer may also use their unique student ID as a login alias. Volunteers maintain their own skills using the approved catalog, can suggest new skills, and see only their own published assignments and permitted event information. They cannot see the full roster or other volunteers' private profiles.

## 6. Core functional requirements

### FR-01: Organizer-created volunteer registration
- An organizer creates a volunteer account with full name, unique university student ID, optional personal contact email, and password.
- All volunteer accounts use the configured shared login email. Each password under that email must be unique so sign-in resolves to one account.
- Student IDs remain unique and may also be used as individual login aliases.
- Student ID is an identifier, not proof of identity by itself; the committee must ensure the account belongs to the intended student.
- Organizer accounts are provisioned separately; there is no public organizer self-registration.

### FR-02: Authentication and account security
- Provide separate role-aware login paths or clear role-aware entry points for Convener, Co-convener, and Volunteer.
- Hash passwords using a suitable password-hashing implementation; never store plaintext passwords.
- Passwords are individually hashed and never stored in plaintext.
- Volunteers sign in with `volunteer@tapmi.edu.in` and an individual password; their student ID is an alternate login alias. Core Committee members sign in with `core@tapmi.edu.in` and an individual password; each also has a unique login ID alias. Passwords must be distinct among accounts using the same shared email. Existing Convener and Co-convener accounts may continue using email and password.
- Provide a safe password recovery process before production rollout.
- Enforce permissions on the server for every protected operation.

### FR-03: Volunteer profile and skills
- Volunteers can select multiple skills from an approved standardized catalog.
- Duplicate skill entries on one profile are prevented.
- Volunteers can suggest a skill that is not in the catalog. An organizer must approve it before it becomes selectable.
- Track active/inactive volunteer status. Deactivation blocks future allocation but preserves history.
- Current profile/skill edits must not rewrite historical assignment records.
- Experience/proficiency fields may be included only after the team defines reliable data and scoring rules.

### FR-04: Events and requirements
- Organizers create and edit events with name, description, date/time, venue, and lifecycle status.
- Organizers define department/role requirements for each event, including headcount, priority, mandatory skills, and optional preferred skills.
- Capture event-level availability and capacity/max-working-hours inputs if the finalized data collection supports them.
- Initial scope has no shift-level assignment. Duration/workload may still inform capacity calculations.
- Display upcoming, ongoing, completed, cancelled, and archived events as appropriate.
- New/relevant events appear first; the precise sorting rule is to be finalized.
- Archived events are read-only through ordinary workflows.
- Changing requirements after approval invalidates that approval. Changing a published allocation creates a new revision.

### FR-05: Staffing capacity calculator
- Allow fixed headcount where workload data is unavailable.
- Where workload data is available, calculate staffing using the proposal's formula: `Required Staff = ceil(Workload × Service Time ÷ Peak Window)`, after converting units consistently.
- Validate units and assumptions before using workload-based results.
- Clearly show whether a requirement came from fixed headcount or workload calculation.
- Do not invent workload or service-time values.

### FR-06: Eligibility and skill matching
- Automatic allocation considers active status, mandatory skills, event-level availability when captured, maximum working hours/capacity when configured, and the one-assignment-per-event rule.
- A volunteer missing a mandatory skill is ineligible for automatic assignment to that role.
- Manual skill mismatch is allowed only after a visible warning and a required organizer reason.
- Inactive volunteers and duplicate assignments remain blocked; a skill-mismatch override does not bypass those hard rules.
- Preference is a soft factor, not a hard eligibility requirement.

### FR-07: Allocation algorithms
- Implement a transparent greedy baseline in Python.
- Implement an ILP optimizer in Python using PuLP.
- Use the same validated event/volunteer input snapshot and hard eligibility rules for comparable runs.
- The allocation policy must consider staffing coverage, department priority, skill suitability, and fairness; preferences are considered when otherwise suitable and must not outrank staffing needs.
- Define and document objective weights and the measurable fairness metric before implementation. Do not bury arbitrary weights in code.
- Keep algorithm logic independent of Flask routes and UI code.

### FR-08: Allocation review and manual editing
- Automatic output is a draft and is not visible to volunteers as an official assignment.
- Organizers can add, remove, replace, or move assignments within an event.
- Manual changes update department totals and vacancies.
- Missing required skill triggers a warning and requires a reason.
- Manual edits persist unless an organizer explicitly requests regeneration.
- Regeneration shows a confirmation warning and creates a new generated draft/run; it must not silently overwrite a published version.
- Record actor, timestamp, old/new values, and reason where applicable.

### FR-09: Approval, publication, and versioning
- Only organizer-approved allocations can be published.
- Approval is tied to the exact allocation version reviewed.
- Any edit after approval invalidates approval.
- A change to a published allocation creates a new revision. The last published version remains visible to volunteers until the new revision is approved and published.
- Publishing must be atomic: volunteers should never see a half-written allocation.
- Draft/unapproved results are not shown as official volunteer assignments.

### FR-10: Vacancy handling
- The system reports actual required, allocated, and vacant positions.
- It does not automatically move a volunteer from another department to fill a vacancy.
- The Convener or Co-convener may manually assign an eligible unassigned volunteer or leave the vacancy open.
- The dashboard must not count a position as filled until an assignment exists in the relevant allocation version.
- Show eligible unassigned volunteers and reasons a position could not be filled.
- A new student must be registered and eligible before being assigned.
- Recommendations can suggest reallocation or recruitment, but must be grounded in actual skill, availability, capacity, and eligibility data.

### FR-11: Volunteer dashboard
- Show the volunteer's own published assignments with event, date/time, venue, department, and role.
- Show own permitted assignment history.
- Do not reveal other volunteers' private profiles or the complete roster.
- Changes appear after publication of the relevant version.
- Skill changes do not silently alter published assignments.

### FR-12: Dashboard, reporting, and recommendations
- Department view: required headcount, allocated headcount, vacancies, coverage, priority, and skill gaps.
- Individual view: profile, assignment, and reason/fit explanation where appropriate.
- Report eligible unassigned volunteers, underutilization, bottlenecks, and skill gaps.
- Compare greedy and ILP metrics.
- Use Matplotlib for required-versus-allocated, shortage, utilization, and algorithm-comparison charts. Seaborn may be used for skill-by-department heatmaps or distributions if it adds value.
- Clearly distinguish actual data from assumed/simulated data.
- Recommendations must explain their basis and must not claim recruitment is necessary if suitable eligible volunteers remain available but unassigned.

### FR-13: What-if simulator
- Allow organizers to change scenario-only inputs such as attendance, volunteer count/availability, duration, requirements/headcount, or priorities, then rerun the allocation.
- Show results against a baseline.
- Simulation must not mutate real event data, actual volunteer profiles, or published allocations.
- Label scenario-only simulated volunteers and values clearly.
- Exact simulator controls and simulated-candidate behavior are design decisions to finalize before implementation.

### FR-14: Event history and archive
- Preserve completed event requirements, published assignments, allocation versions, and audit records.
- Archived events are read-only in normal workflows.
- Cancellation stops new allocation/publication as defined by the event lifecycle but preserves historical records.
- The exact rule for who marks an event completed and when it becomes archived must be finalized.

## 7. Non-functional requirements

- Security: password hashing, protected sessions, server-side role checks, rate limiting, secret management.
- Privacy: volunteers can only access their own private information and published assignments.
- Integrity: unique student IDs, valid foreign keys, no duplicate assignment per event version, atomic publication.
- Auditability: record manual changes, overrides, approvals, publications, regeneration, deactivation, and archive actions.
- Reliability: transactions for multi-row updates; documented backup/recovery procedure.
- Maintainability: separate web/API, data access, and Python allocation modules.
- Explainability: show why vacancies exist and which factors influenced assignments.
- Usability: accessible forms, clear errors, readable tables/charts, responsive layout.
- Performance and scale targets are not yet specified; measure locally and set targets after expected usage is known.

## 8. Acceptance criteria

- Duplicate student IDs are rejected.
- Duplicate contact emails are permitted when login IDs are distinct; duplicate login IDs are rejected.
- Volunteers cannot access organizer endpoints or another volunteer's private records.
- Automatic allocation never assigns an inactive volunteer, duplicates an event assignment, or violates mandatory skills.
- Manual skill mismatch shows a warning, requires a reason, and is audited.
- Five positions with four eligible volunteers results in at most four valid assignments and one vacancy.
- Organizer can manually fill a vacancy or leave it open.
- Ordinary page refresh/view does not regenerate or erase manual edits.
- Explicit regeneration requires confirmation.
- Drafts are not visible as official assignments.
- A new published revision replaces the prior published view only after approval and publication.
- Archived events cannot be edited through ordinary workflows.
- Greedy and ILP are compared on the same input snapshot.
- What-if simulation does not change live records.
- Actual and simulated data are visibly distinguished.

## 9. Original proposal deliverables that must remain in scope

1. Volunteer resource database.
2. Department requirements module.
3. Data cleaning and categorization scripts.
4. Workload-based and fixed-headcount staffing calculator.
5. Eligibility and skill-matching engine.
6. Greedy baseline allocation.
7. ILP-optimized allocation and comparison.
8. Department and individual views.
9. What-if simulator.
10. Analysis dashboard.
11. Recommendation engine.
12. Process flowchart.
13. Final project report and live demo using Kala Fest data.

## 10. Open decisions (do not silently assume)

- Frontend framework: React + Vite is proposed but not yet confirmed.
- Objective weights and measurable fairness definition.
- Whether skill proficiency/experience affects scoring and how it is verified.
- Exact event-level availability and maximum-hours data model.
- Password recovery process and contact email verification policy.
- Organizer account provisioning/recovery details.
- Event sorting, completion, archive, and cancellation transition policy.
- Exact what-if controls and whether simulated candidates can be added.
- Deployment target, expected user count, and operational backup frequency.
