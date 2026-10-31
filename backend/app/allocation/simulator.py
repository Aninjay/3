import copy
from typing import List, Dict, Any, Optional
from backend.app.allocation.schemas import VolunteerInput, RequirementInput, AllocationResult
from backend.app.allocation.greedy import run_greedy_allocation
from backend.app.allocation.ilp_optimizer import run_ilp_allocation

def run_simulation(
    baseline_volunteers: List[VolunteerInput],
    baseline_requirements: List[RequirementInput],
    scenario_adjustments: Dict[str, Any],
    algorithm: str = "ilp"
) -> Dict[str, Any]:
    """
    Runs an isolated what-if scenario on a deep copy of baseline records.
    Never modifies live database records. Clearly labels all outputs as SIMULATION.

    Supported scenario_adjustments:
    - headcount_multipliers: dict {req_id: new_headcount}
    - priority_overrides: dict {req_id: new_priority}
    - add_simulated_volunteers: list of dicts with {name, skills, preferences}
    - volunteer_drop_rate_pct: float (e.g. 20.0 to simulate 20% volunteer absenteeism)
    """
    # 1. Create isolated deep copies
    sim_volunteers = copy.deepcopy(baseline_volunteers)
    sim_requirements = copy.deepcopy(baseline_requirements)

    # 2. Apply scenario adjustments to requirements
    hc_overrides = scenario_adjustments.get("headcount_multipliers", {})
    prio_overrides = scenario_adjustments.get("priority_overrides", {})

    for req in sim_requirements:
        if str(req.id) in hc_overrides:
            req.headcount = int(hc_overrides[str(req.id)])
        elif req.id in hc_overrides:
            req.headcount = int(hc_overrides[req.id])

        if str(req.id) in prio_overrides:
            req.priority = prio_overrides[str(req.id)].lower()
        elif req.id in prio_overrides:
            req.priority = prio_overrides[req.id].lower()

    # 3. Apply volunteer absenteeism / drop rate if configured
    drop_pct = float(scenario_adjustments.get("volunteer_drop_rate_pct", 0.0))
    if drop_pct > 0:
        # Mark drop_pct of volunteers as unavailable
        num_to_drop = int(len(sim_volunteers) * (drop_pct / 100.0))
        for i in range(min(num_to_drop, len(sim_volunteers))):
            sim_volunteers[i].available = False

    # 4. Add simulated volunteer cohorts if requested
    added_sim = scenario_adjustments.get("add_simulated_volunteers", [])
    max_id = max([v.id for v in sim_volunteers], default=1000)
    for idx, s_v in enumerate(added_sim, start=1):
        sim_id = max_id + idx
        sim_volunteers.append(VolunteerInput(
            id=sim_id,
            student_id=f"SIM-{idx:03d}",
            name=f"[Simulated] {s_v.get('name', f'Candidate {idx}')}",
            active=True,
            skills=set(s_v.get("skills", [])),
            available=True,
            availability_start="09:00",
            availability_end="21:00",
            max_hours=8.0,
            experience_level=s_v.get("experience_level", "1 yr"),
            preferences=s_v.get("preferences", []),
            is_simulated=True
        ))

    # 5. Run baseline and scenario allocations
    if algorithm.lower() == "greedy":
        baseline_res = run_greedy_allocation(baseline_volunteers, baseline_requirements, "baseline")
        scenario_res = run_greedy_allocation(sim_volunteers, sim_requirements, "scenario")
    else:
        baseline_res = run_ilp_allocation(baseline_volunteers, baseline_requirements, "baseline")
        scenario_res = run_ilp_allocation(sim_volunteers, sim_requirements, "scenario")

    # 6. Compare outcomes
    delta_allocated = scenario_res.total_allocated - baseline_res.total_allocated
    delta_vacancies = scenario_res.total_vacancies - baseline_res.total_vacancies
    delta_coverage = round(scenario_res.coverage_pct - baseline_res.coverage_pct, 1)

    return {
        "status": "Simulation · Not published",
        "algorithm": algorithm,
        "is_simulation": True,
        "adjustments_applied": scenario_adjustments,
        "baseline": {
            "total_required": baseline_res.total_required,
            "total_allocated": baseline_res.total_allocated,
            "vacancies": baseline_res.total_vacancies,
            "coverage_pct": baseline_res.coverage_pct,
            "department_metrics": baseline_res.department_metrics,
            "priority_metrics": baseline_res.priority_metrics
        },
        "scenario": {
            "total_required": scenario_res.total_required,
            "total_allocated": scenario_res.total_allocated,
            "vacancies": scenario_res.total_vacancies,
            "coverage_pct": scenario_res.coverage_pct,
            "department_metrics": scenario_res.department_metrics,
            "priority_metrics": scenario_res.priority_metrics,
            "simulated_volunteers_assigned": sum(1 for a in scenario_res.assignments if a.is_simulated)
        },
        "delta": {
            "allocated_diff": delta_allocated,
            "vacancies_diff": delta_vacancies,
            "coverage_pct_diff": delta_coverage
        },
        "scenario_assignments": [
            {
                "slot_id": a.slot_id,
                "department": a.department_name,
                "role": a.role_name,
                "priority": a.priority,
                "volunteer_id": a.volunteer_id,
                "volunteer_name": a.volunteer_name,
                "volunteer_student_id": a.volunteer_student_id,
                "is_simulated": a.is_simulated
            }
            for a in scenario_res.assignments
        ],
        "scenario_vacancies": [
            {
                "slot_id": v.slot_id,
                "department": v.department_name,
                "role": v.role_name,
                "priority": v.priority,
                "reason": v.reason
            }
            for v in scenario_res.vacancies
        ]
    }
