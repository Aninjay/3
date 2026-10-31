---
title: "Python Allocation Algorithm Specification"
project: "Cultural Committee Volunteer Management and Event Resource Allocation System"
status: "Design specification; weights remain open"
---

# Python Allocation Algorithm Specification

## 1. Purpose

The Python allocation engine matches event positions with volunteers based on eligibility, skills, availability, capacity, experience (only if reliably collected), preferences, department priorities, and fair distribution. It must identify both shortages and underutilization.

The engine is a decision-support component. It proposes assignments; the Convener or Co-convener reviews, may edit, approves, and publishes them.

## 2. Required pipeline

`Collect → Clean → Categorize → Calculate → Match → Filter → Allocate → Optimize → Analyze → Recommend`

1. Define supply: volunteers, skills, experience if collected, availability, preferences, and capacity.
2. Define demand: departments, roles, required skills, headcount, priority, duration, workload.
3. Clean data: handle missing values, remove duplicates, standardize names, validate ranges/units, and check working-hour limits.
4. Categorize resources and requirements.
5. Calculate staffing demand from workload where possible, or use a fixed headcount.
6. Match volunteers to requirements.
7. Filter eligibility.
8. Run greedy baseline.
9. Run ILP optimization.
10. Analyze outcomes and compare algorithms.
11. Explain shortages, skill gaps, and underutilization.
12. Recommend reallocation, recruitment, skill development, or requirement review where evidence supports it.

## 3. Data structures

### Volunteer input
- `volunteer_id`
- active/inactive status
- approved skill IDs
- event-level availability, if collected
- maximum working hours/capacity, if collected
- experience, only if consistently collected and scoring is defined
- preference(s), if collected
- optional verified proficiency, only if the project defines a trustworthy measurement

### Requirement input
- `requirement_id`
- event ID
- department and role
- headcount
- priority: Critical, High, Normal
- mandatory skills
- preferred skills (optional)
- duration/workload inputs when available
- requirement source: fixed headcount or workload calculation

### Policy input
- one assignment per volunteer per event
- active-account hard constraint
- mandatory-skill rule
- event availability/capacity rules
- priority scoring
- preference scoring
- fairness metric
- tie-break policy
- manual override rules

## 4. Staffing capacity calculator

Two supported modes:

### Mode A: Fixed headcount
Organizer enters the required number of people. This is the fallback when reliable workload inputs are unavailable.

### Mode B: Workload-based
The original proposal gives:

`Required Staff = ceil(Workload × Service Time ÷ Peak Window)`

Before using this formula, the implementation must define what each quantity means and ensure units are compatible. Validate missing/zero peak-window values and avoid invented assumptions. Display the input values, unit conversions, formula, and result.

The no-shift-scheduling rule does not remove event-level duration or maximum-working-hours calculations. It only means the system does not create multiple shift assignments for a volunteer in the initial scope.

## 5. Eligibility rules

### Hard rules for automatic allocation
1. Volunteer account/profile must be active.
2. Volunteer must have every mandatory skill for the requirement.
3. If event-level availability is collected, volunteer must be available for the event under the documented rule.
4. If maximum hours/capacity is collected, assignment must respect that limit.
5. Volunteer may receive at most one assignment per event.
6. Requirement must have an open position and belong to the event being allocated.
7. Skill catalog entries used for matching must be approved.

### Manual assignment
- Missing mandatory skill: show a clear warning and require a non-empty organizer reason to proceed.
- Inactive volunteer: blocked.
- Duplicate assignment in the same event: blocked.
- Other hard constraints: blocked unless a separate explicit policy is approved. A skill mismatch override does not override every rule.

### Soft factors
- Department priority.
- Skill suitability beyond mandatory eligibility, if defined.
- Preference fit.
- Fair distribution/coverage.
- Experience or proficiency only if reliable data and scoring are explicitly defined.

## 6. Greedy baseline

The original proposal specifies a transparent baseline that processes department priorities in Critical → High → Normal order and considers preference when choosing eligible, unassigned volunteers. Keep this behavior documented as the baseline, while the overall project also evaluates the balanced ILP result.

Suggested procedure:
1. Expand headcounts into open positions.
2. For each priority tier, consider requirements in a deterministic order.
3. For each position, build the currently eligible candidate set.
4. Score eligible candidates using the documented within-tier rules, such as skill fit and preference fit; use a stable tie-breaker.
5. Assign the best candidate and remove them from the available pool for this event.
6. If no eligible candidate remains, leave the position vacant and record why.
7. Continue through remaining requirements.
8. Return assignments, vacancies, eligible unassigned volunteers, metrics, and explanations.

Do not claim this baseline is globally optimal. Its purpose is to be transparent, explainable, and comparable to ILP.

## 7. ILP optimization with PuLP

Use a binary decision variable:

`x[v, p] = 1` if volunteer `v` is assigned to position `p`; otherwise `0`.

For a requirement with multiple positions, either expand positions into slots or use an integer count variable with equivalent constraints. The chosen formulation must be documented and tested.

### Core constraints
- Each position receives at most one volunteer.
- Each volunteer receives at most one assignment per event.
- Ineligible volunteer-position pairs are forbidden for automatic allocation.
- Assigned count for a requirement cannot exceed its headcount.
- Optional maximum-hours/capacity constraints apply if those fields are in scope and validated.
- Vacancies are allowed; never fabricate a volunteer to force full coverage.
- Skill mismatch overrides apply only to manual changes after the optimizer; automatic allocation must respect mandatory skills.

### Objective
The user's selected policy is balanced: consider overall staffing coverage, skill suitability, department priority, and fair distribution rather than blindly filling one department. Preferences may help distinguish otherwise suitable assignments, but staffing needs take precedence.

The exact objective weights and fairness metric are not yet decided. They must be documented in configuration and tested before coding. A candidate objective may combine:
- valid filled positions,
- priority-weighted coverage,
- suitability score,
- preference fit,
- measurable fairness across departments or equally eligible volunteers.

Use explicit, normalized scales. Ensure preference bonuses cannot outweigh the policy's intended staffing priorities. Avoid arbitrary constants without a written rationale.

### Solver handling
- Record solver name/status, objective value, and runtime if available.
- If solver fails or returns no usable solution, report the failure and do not treat it as approved.
- Do not promise ILP always beats greedy on every metric. Compare results under the defined objective and report trade-offs.

## 8. Balanced policy and priority handling

The project's final recommended allocation should consider all relevant departments and the defined weighted objective. The greedy baseline retains the original proposal's Critical → High → Normal sequence for comparison. This is intentional: the two methods should illustrate how a simple priority-first baseline compares with a global optimization approach.

Before implementation, define:
- priority values and weight mapping,
- whether minimum coverage guarantees exist for critical departments,
- the exact fairness metric,
- preference influence,
- tie-break rules,
- treatment of equally scored volunteers.

Do not hard-code the weights in multiple modules. Store them in one validated configuration object.

## 9. Metrics for comparison

Both methods must use the same input snapshot and hard eligibility rules. Report:
- total positions required,
- total positions allocated,
- vacancies,
- coverage percentage,
- department-level coverage,
- priority-weighted coverage,
- automatic mandatory-skill violations (must be zero),
- number of eligible unassigned volunteers,
- preference-fit metric (if preferences are collected),
- fairness metric,
- capacity violations (must be zero),
- runtime and solver status where available.

A higher fill count alone does not prove a better allocation if it violates eligibility or hides critical shortages.

## 10. Shortage and recommendation logic

For each vacancy, explain the evidence:
- no active volunteers;
- no volunteer with the required mandatory skill;
- eligible volunteers unavailable for the event;
- capacity limits;
- eligible volunteers exist but were allocated elsewhere by the policy;
- headcount exceeds eligible supply.

Show eligible unassigned volunteers separately from ineligible volunteers. Recommendations may include:
- manually consider an eligible unassigned volunteer;
- leave the position vacant;
- recruit or train for a missing skill;
- review an unrealistic headcount or workload assumption.

Do not automatically transfer someone from another department to fill a vacancy. The Convener or Co-convener may manually make changes or leave the vacancy open. Report actual counts.

## 11. What-if simulator

The simulator runs the same engine on a scenario copy. Possible scenario variables from the proposal:
- attendance;
- volunteer count/availability;
- event duration;
- requirements/headcount;
- priorities;
- workload or capacity assumptions.

Return baseline vs. scenario metrics and explain changes. Do not mutate real volunteer profiles, event requirements, assignments, or the published pointer. If simulated candidates are allowed, label them clearly and keep them scenario-only.

## 12. Worked example

Requirements:
- IT Support: 2 positions, mandatory Networking, High priority.
- Marketing: 2 positions, relevant approved marketing/design skill, Normal priority.
- Logistics: 1 position, mandatory Event Management, Normal priority.

If only four eligible volunteers exist for five positions:
- assign no more than four volunteers;
- leave one position vacant;
- show required = 5, allocated = 4, vacant = 1;
- show eligible unassigned people if any;
- do not create a fake fifth assignment;
- let the organizer manually fill the vacancy with an eligible unassigned volunteer or leave it open.

The exact assignment depends on the real volunteer dataset and finalized objective weights. This example does not define those weights.

## 13. Recommended module boundaries

- `validation.py`: input validation and cleaning.
- `eligibility.py`: hard eligibility checks shared by both algorithms.
- `capacity.py`: workload/fixed-headcount calculations.
- `greedy.py`: baseline method.
- `ilp_optimizer.py`: PuLP model.
- `metrics.py`: comparable metrics.
- `shortages.py`: vacancy causes.
- `compare.py`: greedy/ILP comparison.
- `simulator.py`: isolated what-if runs.
- `recommendations.py`: explainable recommendations.
- `schemas.py`: stable input/output structures.

All decision logic should be unit-testable without running Flask or a browser.
