from typing import List, Dict, Any
from backend.app.allocation.schemas import VolunteerInput, RequirementInput, AllocationResult
from backend.app.allocation.greedy import run_greedy_allocation
from backend.app.allocation.ilp_optimizer import run_ilp_allocation

def compare_algorithms(
    volunteers: List[VolunteerInput],
    requirements: List[RequirementInput],
    snapshot_fingerprint: str = ""
) -> Dict[str, Any]:
    """
    Executes both Greedy and ILP algorithms on the exact same input snapshot and
    returns a rigorous, factual side-by-side comparison.
    """
    greedy_res = run_greedy_allocation(volunteers, requirements, snapshot_fingerprint)
    ilp_res = run_ilp_allocation(volunteers, requirements, snapshot_fingerprint)

    # Department comparison table
    dept_names = sorted(list(set(
        list(greedy_res.department_metrics.keys()) + list(ilp_res.department_metrics.keys())
    )))
    dept_comp = []
    for d in dept_names:
        g_m = greedy_res.department_metrics.get(d, {"required": 0, "allocated": 0, "vacant": 0, "coverage_pct": 0.0})
        i_m = ilp_res.department_metrics.get(d, {"required": 0, "allocated": 0, "vacant": 0, "coverage_pct": 0.0})
        dept_comp.append({
            "department": d,
            "required": g_m["required"],
            "greedy_allocated": g_m["allocated"],
            "greedy_coverage_pct": g_m["coverage_pct"],
            "ilp_allocated": i_m["allocated"],
            "ilp_coverage_pct": i_m["coverage_pct"],
            "diff_allocated": i_m["allocated"] - g_m["allocated"]
        })

    # Priority comparison table
    prio_comp = []
    for p in ["critical", "high", "normal"]:
        g_p = greedy_res.priority_metrics.get(p, {"required": 0, "allocated": 0, "coverage_pct": 0.0})
        i_p = ilp_res.priority_metrics.get(p, {"required": 0, "allocated": 0, "coverage_pct": 0.0})
        prio_comp.append({
            "priority": p,
            "required": g_p["required"],
            "greedy_allocated": g_p["allocated"],
            "greedy_coverage_pct": g_p["coverage_pct"],
            "ilp_allocated": i_p["allocated"],
            "ilp_coverage_pct": i_p["coverage_pct"],
            "diff_allocated": i_p["allocated"] - g_p["allocated"]
        })

    # Preference satisfaction
    greedy_pref_satisfied = sum(1 for a in greedy_res.assignments if a.preference_rank is not None and a.preference_rank <= 2)
    ilp_pref_satisfied = sum(1 for a in ilp_res.assignments if a.preference_rank is not None and a.preference_rank <= 2)

    # Analytical notes based strictly on numbers
    notes = []
    if ilp_res.total_allocated > greedy_res.total_allocated:
        notes.append(f"ILP optimizer filled {ilp_res.total_allocated - greedy_res.total_allocated} more position(s) overall than greedy baseline.")
    elif ilp_res.total_allocated < greedy_res.total_allocated:
        notes.append(f"Greedy baseline filled {greedy_res.total_allocated - ilp_res.total_allocated} more position(s) than ILP optimizer.")
    else:
        notes.append("Both algorithms achieved identical total headcount fill counts.")

    if ilp_pref_satisfied > greedy_pref_satisfied:
        notes.append(f"ILP satisfied top-2 preferences for {ilp_pref_satisfied} volunteers compared to {greedy_pref_satisfied} under greedy.")
    elif ilp_pref_satisfied < greedy_pref_satisfied:
        notes.append(f"Greedy satisfied top-2 preferences for {greedy_pref_satisfied} volunteers compared to {ilp_pref_satisfied} under ILP.")

    notes.append(f"Runtime: Greedy took {greedy_res.runtime_seconds}s; ILP took {ilp_res.runtime_seconds}s.")

    return {
        "snapshot_fingerprint": snapshot_fingerprint,
        "total_required": greedy_res.total_required,
        "greedy": {
            "allocated": greedy_res.total_allocated,
            "vacancies": greedy_res.total_vacancies,
            "coverage_pct": greedy_res.coverage_pct,
            "runtime_seconds": greedy_res.runtime_seconds,
            "preference_top2_satisfied": greedy_pref_satisfied,
            "solver_status": greedy_res.solver_status
        },
        "ilp": {
            "allocated": ilp_res.total_allocated,
            "vacancies": ilp_res.total_vacancies,
            "coverage_pct": ilp_res.coverage_pct,
            "runtime_seconds": ilp_res.runtime_seconds,
            "preference_top2_satisfied": ilp_pref_satisfied,
            "solver_status": ilp_res.solver_status,
            "objective_value": ilp_res.objective_value
        },
        "department_comparison": dept_comp,
        "priority_comparison": prio_comp,
        "evaluation_notes": notes,
        "greedy_result": greedy_res,
        "ilp_result": ilp_res
    }
