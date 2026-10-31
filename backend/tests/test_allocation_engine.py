import pytest
from backend.app.allocation.schemas import VolunteerInput, RequirementInput
from backend.app.allocation.capacity import calculate_workload_capacity
from backend.app.allocation.eligibility import check_eligibility
from backend.app.allocation.greedy import run_greedy_allocation
from backend.app.allocation.ilp_optimizer import run_ilp_allocation
from backend.app.allocation.compare import compare_algorithms
from backend.app.allocation.shortages import analyze_shortages
from backend.app.allocation.recommendations import generate_recommendations
from backend.app.allocation.simulator import run_simulation

def test_capacity_calculation():
    # Workload = 160 items, service time = 0.5 hours, peak window = 20 hours
    # 160 * 0.5 / 20 = 4.0 -> ceil = 4
    res = calculate_workload_capacity(160, 0.5, 20)
    assert res["calculated_headcount"] == 4

    # 105 * 0.5 / 20 = 2.625 -> ceil = 3
    res2 = calculate_workload_capacity(105, 0.5, 20)
    assert res2["calculated_headcount"] == 3

    # Zero or negative peak window should raise ValueError
    with pytest.raises(ValueError):
        calculate_workload_capacity(100, 1.0, 0)

def test_eligibility_hard_rules():
    slot_dummy = RequirementInput(
        id=1, event_id=10, department_name="IT Support", role_name="Audio Visual",
        headcount=1, priority="high", mandatory_skills={"Networking"}, preferred_skills=set()
    )
    from backend.app.allocation.greedy import expand_slots
    slot = expand_slots([slot_dummy])[0]

    # Inactive volunteer
    v_inactive = VolunteerInput(id=1, student_id="V001", name="Inactive User", active=False, skills={"Networking"})
    ok, reason = check_eligibility(v_inactive, slot, set())
    assert not ok
    assert "inactive" in reason.lower()

    # Missing mandatory skill
    v_missing_skill = VolunteerInput(id=2, student_id="V002", name="Active No Skill", active=True, skills={"Event Coordination"})
    ok, reason = check_eligibility(v_missing_skill, slot, set())
    assert not ok
    assert "missing mandatory skills" in reason.lower()

    # Already assigned in event
    v_assigned = VolunteerInput(id=3, student_id="V003", name="Already Assigned", active=True, skills={"Networking"})
    ok, reason = check_eligibility(v_assigned, slot, {3})
    assert not ok
    assert "already assigned" in reason.lower()

    # Valid candidate
    v_valid = VolunteerInput(id=4, student_id="V004", name="Valid Candidate", active=True, skills={"Networking", "Technical Support"})
    ok, reason = check_eligibility(v_valid, slot, set())
    assert ok
    assert reason == "Eligible"

def test_worked_example_five_positions_four_volunteers():
    """
    Test Plan Section 13 / Acceptance Criteria:
    Requirements:
    - IT Support: 2 positions; mandatory Networking; High priority.
    - Marketing: 2 positions; mandatory Marketing; Normal priority.
    - Logistics: 1 position; mandatory Logistics; Normal priority.
    Total = 5 positions.
    Available: only 4 eligible volunteers.
    Assert:
    - At most 4 assignments.
    - Exactly 1 vacancy reported.
    - No duplicate assignments.
    - Both Greedy and ILP report honest counts.
    """
    reqs = [
        RequirementInput(id=1, event_id=1, department_name="IT Support", role_name="Network Tech", headcount=2, priority="high", mandatory_skills={"Networking"}),
        RequirementInput(id=2, event_id=1, department_name="Marketing", role_name="Promotions", headcount=2, priority="normal", mandatory_skills={"Marketing"}),
        RequirementInput(id=3, event_id=1, department_name="Logistics", role_name="Equipment", headcount=1, priority="normal", mandatory_skills={"Logistics"})
    ]

    vols = [
        VolunteerInput(id=1, student_id="V001", name="Alice", skills={"Networking"}, active=True),
        VolunteerInput(id=2, student_id="V002", name="Bob", skills={"Networking"}, active=True),
        VolunteerInput(id=3, student_id="V003", name="Charlie", skills={"Marketing"}, active=True),
        VolunteerInput(id=4, student_id="V004", name="Diana", skills={"Marketing"}, active=True)
        # Note: No one has Logistics!
    ]

    # Run Greedy
    g_res = run_greedy_allocation(vols, reqs, "test_snapshot")
    assert g_res.total_required == 5
    assert g_res.total_allocated == 4
    assert g_res.total_vacancies == 1
    assert len(g_res.assignments) == 4
    assigned_ids = [a.volunteer_id for a in g_res.assignments]
    assert len(assigned_ids) == len(set(assigned_ids)), "Volunteer assigned twice!"

    # Run ILP
    i_res = run_ilp_allocation(vols, reqs, "test_snapshot")
    assert i_res.total_required == 5
    assert i_res.total_allocated == 4
    assert i_res.total_vacancies == 1
    i_assigned_ids = [a.volunteer_id for a in i_res.assignments]
    assert len(i_assigned_ids) == len(set(i_assigned_ids)), "Volunteer assigned twice in ILP!"

    # Check vacancy diagnostic for the Logistics vacancy
    shortages = analyze_shortages(g_res, vols, reqs)
    logistics_shortage = [s for s in shortages if s["department_name"] == "Logistics"][0]
    assert logistics_shortage["shortage_category"] == "GENUINE_SKILL_SHORTAGE"
    assert "Logistics" in logistics_shortage["mandatory_skills"]

def test_compare_algorithms():
    reqs = [
        RequirementInput(id=1, event_id=1, department_name="IT Support", role_name="AV", headcount=1, priority="critical", mandatory_skills={"Technical Support"}),
        RequirementInput(id=2, event_id=1, department_name="Stage", role_name="Backstage", headcount=1, priority="normal", mandatory_skills={"Stage & Backstage Management"})
    ]
    vols = [
        VolunteerInput(id=1, student_id="V001", name="Alice", skills={"Technical Support"}, preferences=["IT Support"], active=True),
        VolunteerInput(id=2, student_id="V002", name="Bob", skills={"Stage & Backstage Management"}, preferences=["Stage"], active=True)
    ]

    comp = compare_algorithms(vols, reqs, "test_snapshot")
    assert comp["total_required"] == 2
    assert comp["greedy"]["allocated"] == 2
    assert comp["ilp"]["allocated"] == 2
    assert comp["greedy"]["vacancies"] == 0
    assert comp["ilp"]["vacancies"] == 0

def test_simulator_does_not_mutate_baseline():
    reqs = [
        RequirementInput(id=1, event_id=1, department_name="IT Support", role_name="AV", headcount=1, priority="high", mandatory_skills={"Technical Support"})
    ]
    vols = [
        VolunteerInput(id=1, student_id="V001", name="Alice", skills={"Technical Support"}, active=True)
    ]

    # Run simulation with 2 simulated candidates added and headcount increased to 3
    adjustments = {
        "headcount_multipliers": {1: 3},
        "add_simulated_volunteers": [
            {"name": "Simulated Bob", "skills": ["Technical Support"]},
            {"name": "Simulated Charlie", "skills": ["Technical Support"]}
        ]
    }

    sim_res = run_simulation(vols, reqs, adjustments, algorithm="greedy")
    assert sim_res["is_simulation"] is True
    assert sim_res["status"] == "Simulation · Not published"
    assert sim_res["scenario"]["total_required"] == 3
    assert sim_res["scenario"]["total_allocated"] == 3
    assert sim_res["scenario"]["simulated_volunteers_assigned"] == 2

    # Verify baseline objects are untouched!
    assert reqs[0].headcount == 1
    assert len(vols) == 1
    assert vols[0].student_id == "V001"
