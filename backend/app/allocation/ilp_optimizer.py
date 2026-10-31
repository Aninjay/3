import time
import pulp
from typing import List, Dict, Set, Tuple, Any
from backend.app.allocation.schemas import (
    VolunteerInput, RequirementInput, PositionSlot,
    AssignmentResult, VacancyResult, AllocationResult
)
from backend.app.allocation.eligibility import check_eligibility
from backend.app.allocation.greedy import expand_slots, parse_experience_years

PRIORITY_WEIGHTS = {
    "critical": 50.0,
    "high": 25.0,
    "normal": 10.0
}

def calculate_ilp_weight(vol: VolunteerInput, slot: PositionSlot) -> float:
    # 1. Base position filled reward
    weight = 100.0

    # 2. Priority weight
    weight += PRIORITY_WEIGHTS.get(slot.priority, 10.0)

    # 3. Preferred skills match bonus (normalized)
    if slot.preferred_skills:
        matched = slot.preferred_skills.intersection(vol.skills)
        ratio = len(matched) / len(slot.preferred_skills)
        weight += 10.0 * ratio

    # 4. Department preference bonus
    if slot.department_name in vol.preferences:
        rank = vol.preferences.index(slot.department_name) + 1
        if rank == 1:
            weight += 8.0
        elif rank == 2:
            weight += 4.0
        elif rank == 3:
            weight += 2.0

    # 5. Experience suitability
    weight += 0.5 * parse_experience_years(vol.experience_level)

    return weight

def run_ilp_allocation(
    volunteers: List[VolunteerInput],
    requirements: List[RequirementInput],
    snapshot_fingerprint: str = ""
) -> AllocationResult:
    start_time = time.perf_counter()
    slots = expand_slots(requirements)

    prob = pulp.LpProblem("Cultural_Committee_Resource_Allocation", pulp.LpMaximize)

    # Determine eligible pairs (vol, slot)
    # Binary decision variables x[(vol.id, slot.slot_id)]
    x_vars: Dict[Tuple[int, str], pulp.LpVariable] = {}
    eligible_slots_for_vol: Dict[int, List[str]] = {v.id: [] for v in volunteers}
    eligible_vols_for_slot: Dict[str, List[VolunteerInput]] = {s.slot_id: [] for s in slots}

    for slot in slots:
        for vol in volunteers:
            is_ok, _ = check_eligibility(vol, slot, set())
            if is_ok:
                var_name = f"x_v{vol.id}_s{slot.requirement_id}_{slot.slot_index}"
                x_var = pulp.LpVariable(var_name, cat=pulp.LpBinary)
                x_vars[(vol.id, slot.slot_id)] = x_var
                eligible_slots_for_vol[vol.id].append(slot.slot_id)
                eligible_vols_for_slot[slot.slot_id].append(vol)

    # Objective function
    prob += pulp.lpSum([
        x_vars[(vol.id, slot.slot_id)] * calculate_ilp_weight(vol, slot)
        for slot in slots
        for vol in eligible_vols_for_slot[slot.slot_id]
    ])

    # Constraint 1: Each slot can be assigned to at most 1 volunteer
    for slot in slots:
        vars_for_slot = [x_vars[(v.id, slot.slot_id)] for v in eligible_vols_for_slot[slot.slot_id]]
        if vars_for_slot:
            prob += pulp.lpSum(vars_for_slot) <= 1, f"SlotCapacity_{slot.slot_id}"

    # Constraint 2: Each volunteer can receive at most 1 assignment in the event
    for vol in volunteers:
        vars_for_vol = [x_vars[(vol.id, s_id)] for s_id in eligible_slots_for_vol[vol.id]]
        if vars_for_vol:
            prob += pulp.lpSum(vars_for_vol) <= 1, f"VolunteerUniqueness_{vol.id}"

    # Solve with CBC
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=30)
    solver_status_code = prob.solve(solver)
    solver_status_name = pulp.LpStatus.get(solver_status_code, "Unknown")

    assigned_vols: Set[int] = set()
    assignments: List[AssignmentResult] = []
    vacancies: List[VacancyResult] = []

    vol_dict = {v.id: v for v in volunteers}

    for slot in slots:
        assigned_to_slot = None
        for vol in eligible_vols_for_slot[slot.slot_id]:
            val = pulp.value(x_vars[(vol.id, slot.slot_id)])
            if val is not None and val > 0.5:
                assigned_to_slot = vol
                break

        if assigned_to_slot:
            assigned_vols.add(assigned_to_slot.id)
            matched_pref = sorted(list(slot.preferred_skills.intersection(assigned_to_slot.skills)))
            pref_rank = None
            if slot.department_name in assigned_to_slot.preferences:
                pref_rank = assigned_to_slot.preferences.index(slot.department_name) + 1

            assignments.append(AssignmentResult(
                slot_id=slot.slot_id,
                requirement_id=slot.requirement_id,
                slot_index=slot.slot_index,
                department_name=slot.department_name,
                role_name=slot.role_name,
                priority=slot.priority,
                volunteer_id=assigned_to_slot.id,
                volunteer_student_id=assigned_to_slot.student_id,
                volunteer_name=assigned_to_slot.name,
                assignment_source="ilp",
                skill_fit_score=1.0 + (len(matched_pref) * 0.1),
                preferred_skills_matched=matched_pref,
                preference_rank=pref_rank,
                skill_override=False,
                is_simulated=assigned_to_slot.is_simulated
            ))
        else:
            # Shortage analysis for ILP vacancy
            active_with_skills = [
                v for v in volunteers
                if v.active and slot.mandatory_skills.issubset(v.skills)
            ]
            if not active_with_skills:
                reason = f"No active volunteer possesses mandatory skills: {', '.join(sorted(slot.mandatory_skills)) or 'None'}"
            else:
                assigned_away = [v for v in active_with_skills if v.id in assigned_vols]
                unassigned_avail = [v for v in active_with_skills if v.id not in assigned_vols]
                if unassigned_avail:
                    reasons_list = []
                    for u in unassigned_avail:
                        _, why = check_eligibility(u, slot, set())
                        reasons_list.append(f"{u.student_id}: {why}")
                    reason = f"Eligible volunteers disqualified by constraints ({'; '.join(reasons_list[:2])})"
                else:
                    reason = f"All {len(active_with_skills)} suitable volunteer(s) were assigned to other roles to maximize overall objective"

            vacancies.append(VacancyResult(
                slot_id=slot.slot_id,
                requirement_id=slot.requirement_id,
                slot_index=slot.slot_index,
                department_name=slot.department_name,
                role_name=slot.role_name,
                priority=slot.priority,
                mandatory_skills=sorted(list(slot.mandatory_skills)),
                reason=reason
            ))

    unassigned = [
        {
            "id": v.id,
            "student_id": v.student_id,
            "name": v.name,
            "active": v.active,
            "skills": sorted(list(v.skills)),
            "preferences": v.preferences,
            "is_simulated": v.is_simulated
        }
        for v in volunteers
        if v.id not in assigned_vols and v.active
    ]

    total_req = len(slots)
    total_alloc = len(assignments)
    total_vac = len(vacancies)
    coverage = round((total_alloc / total_req * 100.0), 1) if total_req > 0 else 0.0

    dept_metrics = {}
    for slot in slots:
        d = slot.department_name
        if d not in dept_metrics:
            dept_metrics[d] = {"required": 0, "allocated": 0, "vacant": 0}
        dept_metrics[d]["required"] += 1
    for a in assignments:
        dept_metrics[a.department_name]["allocated"] += 1
    for v in vacancies:
        dept_metrics[v.department_name]["vacant"] += 1
    for d, m in dept_metrics.items():
        m["coverage_pct"] = round((m["allocated"] / m["required"] * 100.0), 1) if m["required"] > 0 else 0.0

    prio_metrics = {}
    for p in ["critical", "high", "normal"]:
        prio_metrics[p] = {"required": 0, "allocated": 0, "vacant": 0, "coverage_pct": 0.0}
    for slot in slots:
        prio_metrics[slot.priority]["required"] += 1
    for a in assignments:
        prio_metrics[a.priority]["allocated"] += 1
    for v in vacancies:
        prio_metrics[v.priority]["vacant"] += 1
    for p, m in prio_metrics.items():
        m["coverage_pct"] = round((m["allocated"] / m["required"] * 100.0), 1) if m["required"] > 0 else 0.0

    obj_val = None
    try:
        obj_val = round(pulp.value(prob.objective), 2) if prob.objective else None
    except Exception:
        pass

    runtime = round(time.perf_counter() - start_time, 4)

    return AllocationResult(
        algorithm="ilp",
        snapshot_fingerprint=snapshot_fingerprint,
        total_required=total_req,
        total_allocated=total_alloc,
        total_vacancies=total_vac,
        coverage_pct=coverage,
        assignments=assignments,
        vacancies=vacancies,
        department_metrics=dept_metrics,
        priority_metrics=prio_metrics,
        unassigned_volunteers=unassigned,
        shortage_reasons=[{"slot_id": v.slot_id, "role": v.role_name, "reason": v.reason} for v in vacancies],
        solver_status=solver_status_name,
        objective_value=obj_val,
        runtime_seconds=runtime
    )
