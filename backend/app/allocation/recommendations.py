from typing import List, Dict, Any
from backend.app.allocation.schemas import AllocationResult, VolunteerInput, RequirementInput
from backend.app.allocation.shortages import analyze_shortages

def generate_recommendations(
    allocation_result: AllocationResult,
    volunteers: List[VolunteerInput],
    requirements: List[RequirementInput]
) -> List[Dict[str, Any]]:
    """
    Produces actionable, grounded recommendations for committee leadership based on
    actual shortages, priority levels, and unassigned volunteer capabilities.
    """
    shortage_diag = analyze_shortages(allocation_result, volunteers, requirements)
    recommendations = []

    # 1. Actionable unassigned volunteers who can fill open vacancies
    realloc_slots = [s for s in shortage_diag if s["shortage_category"] == "UNASSIGNED_AVAILABLE_CANDIDATES"]
    if realloc_slots:
        for s in realloc_slots:
            best_cand = s["eligible_unassigned_candidates"][0]
            recommendations.append({
                "type": "MANUAL_ASSIGNMENT_OPPORTUNITY",
                "priority": s["priority"],
                "department": s["department_name"],
                "role": s["role_name"],
                "title": f"Assign {best_cand['name']} to open {s['department_name']} slot",
                "description": (
                    f"Volunteer {best_cand['name']} ({best_cand['student_id']}) is currently active and unassigned, "
                    f"and meets all mandatory skills ({', '.join(s['mandatory_skills']) or 'None'}) for {s['role_name']}."
                ),
                "evidence": f"{len(s['eligible_unassigned_candidates'])} eligible unassigned candidates exist.",
                "candidate_id": best_cand["volunteer_id"]
            })

    # 2. Critical vacancies with competing assignments
    competing_critical = [s for s in shortage_diag if s["shortage_category"] == "COMPETING_ROLE_ALLOCATION" and s["priority"] == "critical"]
    if competing_critical:
        for s in competing_critical:
            recommendations.append({
                "type": "CRITICAL_BOTTLENECK",
                "priority": "critical",
                "department": s["department_name"],
                "role": s["role_name"],
                "title": f"Critical vacancy in {s['department_name']} due to competing priorities",
                "description": s["diagnostic_summary"],
                "evidence": s["action_recommendation"],
                "candidate_id": None
            })

    # 3. Genuine skill gaps requiring training or recruitment
    genuine_gaps = [s for s in shortage_diag if s["shortage_category"] == "GENUINE_SKILL_SHORTAGE"]
    if genuine_gaps:
        gap_skills = sorted(list(set(sk for s in genuine_gaps for sk in s["mandatory_skills"])))
        recommendations.append({
            "type": "SKILL_RECRUITMENT_OR_TRAINING",
            "priority": "high",
            "department": "Committee-wide",
            "role": "Multiple Roles",
            "title": f"Skill gap identified in: {', '.join(gap_skills)}",
            "description": (
                f"Zero active committee volunteers have mandatory skills for {len(genuine_gaps)} unfilled role(s). "
                f"Targeted volunteer recruitment or workshop training should be organized."
            ),
            "evidence": f"Unfilled roles: {', '.join(set(s['role_name'] for s in genuine_gaps))}",
            "candidate_id": None
        })

    return recommendations
