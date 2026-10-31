---
title: "Test Plan and Acceptance Tests"
project: "Cultural Committee Volunteer Management and Event Resource Allocation System"
status: "Verification baseline"
---

# Test Plan

## 1. Testing goals

Verify that:
- allocation decisions are made in Python;
- hard eligibility constraints are respected;
- actual vacancies are reported accurately;
- organizer control and approval/publication rules are enforced;
- volunteers see only their own published assignments;
- history and audit data are preserved;
- greedy and ILP results are comparable and explainable;
- what-if simulation cannot mutate live data.

## 2. Test levels

### Unit tests
Test data cleaning, capacity calculations, eligibility, greedy selection, ILP constraints/objective, metrics, shortage explanations, and recommendation rules independently of Flask/PostgreSQL.

### Integration tests
Test Flask routes with the database layer, authentication, transactions, allocation run persistence, manual edits, approval/publication, and reports.

### Authorization/security tests
Test role separation, ownership checks, duplicate IDs, OTP abuse limits, password handling, rate limiting, and error responses.

### End-to-end tests
Exercise the full organizer and volunteer workflow from creating an event through publication and volunteer viewing.

### Regression tests
Keep a fixed, labelled fixture dataset and expected invariants so later changes do not reintroduce invalid assignments or incorrect vacancy counts.

## 3. Core invariants

These must hold for every automatic allocation:
1. No inactive volunteer is assigned.
2. No volunteer receives more than one assignment per event allocation version.
3. No automatic assignment violates a mandatory skill.
4. No requirement exceeds its headcount.
5. Capacity/availability rules are respected whenever those fields are enabled.
6. Vacancies are explicit and equal required positions minus valid assignments.
7. The engine never invents a volunteer.
8. Greedy and ILP use the same input snapshot and hard eligibility rules for a comparison.
9. Solver failure is not treated as a successful or approved allocation.
10. A draft is not visible as an official assignment.

## 4. Authentication and authorization cases

| ID | Scenario | Expected result |
|---|---|---|
| AUTH-01 | Duplicate student ID | Second volunteer record rejected |
| AUTH-02 | Duplicate normalized email | Duplicate rejected |
| AUTH-03 | Wrong OTP | Activation rejected; attempt counted |
| AUTH-04 | Expired OTP | Activation rejected |
| AUTH-05 | Reuse consumed OTP | Activation rejected |
| AUTH-06 | Exceed OTP retry limit | Further attempts rate-limited/blocked |
| AUTH-07 | Volunteer requests organizer endpoint | `403` or equivalent denial |
| AUTH-08 | Volunteer requests another volunteer's profile/assignment | Denied without leaking private data |
| AUTH-09 | Client sends a different role/user ID | Server ignores untrusted identity/role and uses session identity |
| AUTH-10 | Public user tries to create organizer account | Rejected |
| AUTH-11 | Password or OTP appears in logs/API response | Test fails; secrets must not be exposed |

## 5. Profile and skill cases

| ID | Scenario | Expected result |
|---|---|---|
| SKILL-01 | Volunteer selects several approved skills | All valid skills saved |
| SKILL-02 | Same skill selected twice | Duplicate prevented |
| SKILL-03 | Volunteer suggests a new skill | Skill remains pending |
| SKILL-04 | Pending skill used for automatic eligibility | Rejected/not considered approved |
| SKILL-05 | Organizer approves suggestion | Skill becomes selectable |
| SKILL-06 | Volunteer deactivated | Future assignment blocked; history preserved |
| SKILL-07 | Current skills change after a published event | Historical allocation record unchanged |

## 6. Capacity and requirements cases

| ID | Scenario | Expected result |
|---|---|---|
| CAP-01 | Fixed headcount entered | Fixed count used and source labelled |
| CAP-02 | Valid workload inputs with compatible units | Formula result calculated and shown |
| CAP-03 | Missing workload input | Calculation rejected or fixed-headcount path offered |
| CAP-04 | Zero/invalid peak window | Calculation rejected with clear error |
| CAP-05 | Negative headcount/duration/workload | Rejected |
| CAP-06 | Requirement changes after approval | Approval invalidated and a new revision is required |
| CAP-07 | Requirement edit on archived event | Rejected through normal API/UI |

## 7. Allocation algorithm cases

| ID | Scenario | Expected result |
|---|---|---|
| ALG-01 | Role requires Networking; volunteer lacks it | No automatic assignment to that role |
| ALG-02 | Volunteer inactive | Never assigned |
| ALG-03 | Volunteer already assigned to one role in event | Cannot receive second role in same event |
| ALG-04 | Five positions, four eligible volunteers | At most four assignments; one vacancy reported |
| ALG-05 | No eligible volunteer for a skill | Vacancy and missing-skill reason shown |
| ALG-06 | Eligible unassigned volunteers remain | Listed separately from ineligible volunteers |
| ALG-07 | Availability is enabled and volunteer unavailable | Volunteer excluded from automatic assignment |
| ALG-08 | Maximum-hours rule is enabled and would be exceeded | Candidate rejected by capacity constraint |
| ALG-09 | Greedy and ILP comparison requested | Same input snapshot and hard eligibility rules used |
| ALG-10 | ILP solver returns failure/timeout | Clear solver status; result not marked approved |
| ALG-11 | Preference conflicts with staffing priority | Preference does not override the documented staffing policy |
| ALG-12 | Tied candidates | Documented deterministic tie-break used |
| ALG-13 | Objective weights change | Metrics and resulting allocation reflect the documented configuration |
| ALG-14 | No volunteers exist | All required positions remain vacant; no fake assignments |

## 8. Manual editing and lifecycle cases

| ID | Scenario | Expected result |
|---|---|---|
| MAN-01 | Organizer adds/removes/replaces assignment | Counts and vacancies update consistently |
| MAN-02 | Manual assignment lacks mandatory skill | Warning displayed |
| MAN-03 | Organizer confirms skill mismatch without reason | Rejected |
| MAN-04 | Organizer confirms skill mismatch with reason | Allowed if all other hard rules pass; audited |
| MAN-05 | Manual assignment to inactive volunteer | Blocked |
| MAN-06 | Manual duplicate assignment | Blocked |
| MAN-07 | Ordinary refresh after manual edit | Edit persists; no regeneration |
| MAN-08 | Explicit regeneration requested | Confirmation required; new run/draft and audit record |
| MAN-09 | Draft exists but is not published | Volunteer does not see it as official |
| MAN-10 | Approved version edited | Approval invalidated |
| MAN-11 | Published allocation changed | New draft revision; old published version remains visible |
| MAN-12 | New version approved and published | New version becomes current official version atomically |
| MAN-13 | Two organizers edit same stale version | Conflict detected; no silent lost update |
| MAN-14 | One organizer approves while version has changed | Approval of stale version rejected |
| MAN-15 | Event cancelled | New allocation/publication blocked according to policy; history preserved |
| MAN-16 | Event archived | Normal editing/regeneration blocked |

## 9. Vacancy and recommendation cases

| ID | Scenario | Expected result |
|---|---|---|
| VAC-01 | Required 5, assigned 4 | UI reports required=5, allocated=4, vacant=1 |
| VAC-02 | Eligible unassigned volunteer could fill vacancy | Shown as an option; not auto-transferred |
| VAC-03 | Organizer chooses to leave vacancy open | Vacancy remains accurately reported |
| VAC-04 | Organizer manually fills vacancy with eligible volunteer | Count updates; action audited |
| VAC-05 | A manual move would create a vacancy elsewhere | Both affected departments recalculate and show actual counts |
| VAC-06 | Skill missing among all available volunteers | Recommendation may suggest recruitment/training, with evidence |
| VAC-07 | Suitable eligible volunteer remains unassigned | Recommendation must consider that person before claiming recruitment is required |

## 10. What-if simulator cases

| ID | Scenario | Expected result |
|---|---|---|
| SIM-01 | Increase scenario volunteer count | Scenario output recalculates |
| SIM-02 | Change scenario headcount/priority/duration | Scenario output reflects inputs |
| SIM-03 | Add simulated candidate, if supported | Candidate is clearly labelled simulated |
| SIM-04 | Run simulation | Live event requirements unchanged |
| SIM-05 | Run simulation | Real volunteer profiles and skills unchanged |
| SIM-06 | Run simulation | Published allocation pointer and assignments unchanged |
| SIM-07 | Compare baseline and scenario | Metrics and differences displayed side by side |

## 11. Reporting and visualization cases

- Required/allocated/vacant totals match the selected allocation version.
- Department charts label the event and version.
- Greedy/ILP comparison uses comparable runs.
- Skill heatmaps use approved/valid data only.
- Simulated data is visibly labelled.
- No chart or recommendation fabricates missing values.
- Individual views explain assignments without exposing other volunteers' private data.

## 12. Data integrity and transaction tests

- Foreign-key violations are rejected.
- Duplicate student IDs and skills are rejected.
- Assignment insert with requirement from another event is rejected by application validation.
- Publishing an unapproved version fails.
- Publishing a version for the wrong event fails.
- Failure during multi-row publication leaves the previous published pointer intact.
- Failure during assignment replacement does not leave partial staffing counts.
- Historical published version remains unchanged after later profile edits.
- Audit records are written for privileged changes and do not contain passwords, OTP values, or session secrets.

## 13. Sample acceptance fixture

Use a clearly labelled simulated event:
- IT Support: 2 positions; mandatory Networking; High priority.
- Marketing: 2 positions; agreed mandatory skill rule; Normal priority.
- Logistics: 1 position; mandatory Event Management; Normal priority.

Create five positions and only four eligible volunteers. Verify:
- no more than four volunteers are assigned;
- one position is vacant;
- each automatic assignment meets mandatory skills;
- no volunteer is assigned twice;
- department counts sum to the event total;
- the organizer can manually assign an eligible unassigned volunteer or leave the vacancy open;
- the volunteer portal shows only the caller's published assignment after approval/publication.

Do not treat this fixture as real Cultural Committee data.

## 14. Release gate

Do not call the application ready for demonstration until:
- core authorization and privacy tests pass;
- assignment constraints and vacancy counts pass;
- publication/versioning/audit tests pass;
- greedy and ILP results can be reproduced and explained;
- simulation is isolated;
- all demo data is labelled as real, assumed, or simulated accurately;
- setup instructions and known limitations are documented.
