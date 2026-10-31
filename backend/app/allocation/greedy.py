import time
from typing import List, Dict, Set, Any
from backend.app.allocation.schemas import (
    VolunteerInput, RequirementInput, PositionSlot,
    AssignmentResult, VacancyResult, AllocationResult
)
from backend.app.allocation.eligibility import check_eligibility, get_eligible_candidates

PRIORITY_TIERS = {
    "critical": 0,
    "high": 1,
    "normal": 2
}

def expand_slots(requirements: List[RequirementInput]) -> List[PositionSlot]:
    slots = []
    # Sort requirements deterministically: priority tier first, then requirement id
    sorted_reqs = sorted(
        requirements,
        key=lambda r: (PRIORITY_TIERS.get(r.priority.lower(), 99), r.id)
    )
    for req in sorted_reqs:
        for idx in range(req.headcount):
            slots.append(PositionSlot(
                slot_id=f"req-{req.id}-slot-{idx}",
                requirement_id=req.id,
                slot_index=idx,
                department_name=req.department_name,
                role_name=req.role_name,
                priority=req.priority.lower(),
                mandatory_skills=set(req.mandatory_skills),
                preferred_skills=set(req.preferred_skills),
                duration_hours=req.duration_hours
            ))
    return slots

def parse_experience_years(exp_str: str) -> float:
    try:
        cleaned = exp_str.replace("yrs", "").replace("yr", "").replace("+", "").strip()
        return float(cleaned)
    except Exception:
        return 0.0

def score_candidate(vol: VolunteerInput, slot: PositionSlot) -> float:
    """
    Candidate scoring within a priority tier:
    - Preferred skill matches: +10 points each
    - Department preference rank:
        Rank 1: +15 points
        Rank 2: +10 points
        Rank 3: +5 points
    - Experience in years: +1 point per year
    """
    score = 100.0 # Base eligible score
    # Preferred skills match
    matched_pref = slot.preferred_skills.intersection(vol.skills)
    score += len(matched_pref) * 10.0

    # Department preference match
    if slot.department_name in vol.preferences:
        rank = vol.preferences.index(slot.department_name) + 1
        if rank == 1:
            score += 15.0
        elif rank == 2:
            score += 10.0
        elif rank == 3:
            score += 5.0

    score += parse_experience_years(vol.experience_level)
    return score

def run_greedy_allocation(
    volunteers: List[VolunteerInput],
    requirements: List[RequirementInput],
    snapshot_fingerprint: str = ""
) -> AllocationResult:
    start_time = time.perf_counter()
    slots = expand_slots(requirements)
    assigned_vols: Set[int] = set()
    assignments: List[AssignmentResult] = []
    vacancies: List[VacancyResult] = []

    # Process slots in strict priority order (Critical -> High -> Normal)
    for slot in slots:
        candidates = get_eligible_candidates(volunteers, slot, assigned_vols)
        if candidates:
            # Deterministic sorting: highest score descending, then tie-break by student_id
            candidates.sort(key=lambda c: (-score_candidate(c, slot), c.student_id))
            chosen = candidates[0]
            assigned_vols.add(chosen.id)

            matched_preferred = sorted(list(slot.preferred_skills.intersection(chosen.skills)))
            pref_rank = None
            if slot.department_name in chosen.preferences:
                pref_rank = chosen.preferences.index(slot.department_name) + 1

            assignments.append(AssignmentResult(
                slot_id=slot.slot_id,
                requirement_id=slot.requirement_id,
                slot_index=slot.slot_index,
                department_name=slot.department_name,
                role_name=slot.role_name,
                priority=slot.priority,
                volunteer_id=chosen.id,
                volunteer_student_id=chosen.student_id,
                volunteer_name=chosen.name,
                assignment_source="greedy",
                skill_fit_score=1.0 + (len(matched_preferred) * 0.1),
                preferred_skills_matched=matched_preferred,
                preference_rank=pref_rank,
                skill_override=False,
                is_simulated=chosen.is_simulated
            ))
        else:
            # Vacancy analysis: Why is this slot unfilled?
            # Check how many active volunteers have the mandatory skills but were assigned elsewhere
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
                    # Unassigned but disqualified by hours or availability
                    reasons_list = []
                    for u in unassigned_avail:
                        _, why = check_eligibility(u, slot, set())
                        reasons_list.append(f"{u.student_id}: {why}")
                    reason = f"Eligible volunteers disqualified by constraints ({'; '.join(reasons_list[:2])})"
                else:
                    reason = f"All {len(active_with_skills)} suitable volunteer(s) were assigned to higher-priority roles"

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

    # Calculate unassigned volunteers
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

    # Department breakdown
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

    # Priority breakdown
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

    runtime = round(time.perf_counter() - start_time, 4)

    return AllocationResult(
        algorithm="greedy",
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
        solver_status="Success",
        objective_value=None,
        runtime_seconds=runtime
    )
