from typing import List, Dict, Any, Set
from backend.app.allocation.schemas import (
    VolunteerInput, RequirementInput, PositionSlot, AllocationResult
)
from backend.app.allocation.eligibility import check_eligibility

def analyze_shortages(
    allocation_result: AllocationResult,
    volunteers: List[VolunteerInput],
    requirements: List[RequirementInput]
) -> List[Dict[str, Any]]:
    """
    Analyzes each vacancy in the allocation result to provide factual, evidence-backed
    shortage diagnostics and distinguishes genuine shortages from unassigned capacity.
    """
    req_map = {r.id: r for r in requirements}
    assigned_vols_set = {a.volunteer_id for a in allocation_result.assignments}
    unassigned_active_vols = [v for v in volunteers if v.active and v.id not in assigned_vols_set]

    diagnostics = []

    for vac in allocation_result.vacancies:
        req = req_map.get(vac.requirement_id)
        if not req:
            continue

        slot = PositionSlot(
            slot_id=vac.slot_id,
            requirement_id=vac.requirement_id,
            slot_index=vac.slot_index,
            department_name=vac.department_name,
            role_name=vac.role_name,
            priority=vac.priority,
            mandatory_skills=set(vac.mandatory_skills),
            preferred_skills=set(req.preferred_skills),
            duration_hours=req.duration_hours
        )

        # 1. Check if ANY unassigned active volunteers are eligible for this vacant slot right now
        eligible_unassigned = []
        for u in unassigned_active_vols:
            is_ok, _ = check_eligibility(u, slot, set())
            if is_ok:
                eligible_unassigned.append({
                    "volunteer_id": u.id,
                    "student_id": u.student_id,
                    "name": u.name,
                    "skills": sorted(list(u.skills)),
                    "preferences": u.preferences,
                    "experience": u.experience_level
                })

        # 2. Check total committee volunteers with mandatory skills
        total_with_mandatory = [
            v for v in volunteers
            if v.active and slot.mandatory_skills.issubset(v.skills)
        ]

        if eligible_unassigned:
            category = "UNASSIGNED_AVAILABLE_CANDIDATES"
            summary = (
                f"{len(eligible_unassigned)} eligible unassigned volunteer(s) exist who meet all mandatory skills "
                f"({', '.join(vac.mandatory_skills) or 'None'}) and can be assigned manually."
            )
            action_recommendation = (
                f"Consider manually assigning eligible unassigned candidate "
                f"{eligible_unassigned[0]['name']} ({eligible_unassigned[0]['student_id']}) to fill this vacancy."
            )
        elif not total_with_mandatory:
            category = "GENUINE_SKILL_SHORTAGE"
            summary = (
                f"Zero active volunteers in the entire committee database possess the mandatory skill(s): "
                f"{', '.join(vac.mandatory_skills) or 'None'}."
            )
            action_recommendation = (
                f"Recruitment or specialized training is required for mandatory skill(s): "
                f"{', '.join(vac.mandatory_skills) or 'None'}, or consider relaxing this requirement."
            )
        else:
            category = "COMPETING_ROLE_ALLOCATION"
            assigned_roles = [
                f"{a.volunteer_name} -> {a.department_name} ({a.role_name})"
                for a in allocation_result.assignments
                if a.volunteer_id in [v.id for v in total_with_mandatory]
            ]
            summary = (
                f"All {len(total_with_mandatory)} volunteer(s) with required skills were prioritized and "
                f"allocated to other department roles."
            )
            action_recommendation = (
                f"If this position is critical, review current assignments: {'; '.join(assigned_roles[:2])}."
            )

        diagnostics.append({
            "slot_id": vac.slot_id,
            "department_name": vac.department_name,
            "role_name": vac.role_name,
            "priority": vac.priority,
            "mandatory_skills": vac.mandatory_skills,
            "shortage_category": category,
            "diagnostic_summary": summary,
            "action_recommendation": action_recommendation,
            "eligible_unassigned_candidates": eligible_unassigned
        })

    return diagnostics
