from typing import Tuple, List, Set
from backend.app.allocation.schemas import VolunteerInput, RequirementInput, PositionSlot

def check_eligibility(
    volunteer: VolunteerInput,
    slot: PositionSlot,
    assigned_volunteer_ids: Set[int]
) -> Tuple[bool, str]:
    """
    Checks if a volunteer meets all hard eligibility criteria for a given position slot.
    Returns (is_eligible, reason_if_not).
    """
    # Rule 1: Account must be active
    if not volunteer.active:
        return False, "Volunteer account is inactive"

    # Rule 2: At most one assignment per event
    if volunteer.id in assigned_volunteer_ids:
        return False, "Volunteer is already assigned to another role in this event"

    # Rule 3: Event availability
    if not volunteer.available:
        return False, "Volunteer is marked unavailable for this event"

    # Rule 4: Capacity / max hours check
    if slot.duration_hours > volunteer.max_hours:
        return False, f"Role duration ({slot.duration_hours}h) exceeds volunteer max capacity ({volunteer.max_hours}h)"

    # Rule 5: Mandatory skills must all be present
    missing_mandatory = slot.mandatory_skills - volunteer.skills
    if missing_mandatory:
        missing_str = ", ".join(sorted(missing_mandatory))
        return False, f"Missing mandatory skills: {missing_str}"

    return True, "Eligible"

def get_eligible_candidates(
    volunteers: List[VolunteerInput],
    slot: PositionSlot,
    assigned_volunteer_ids: Set[int]
) -> List[VolunteerInput]:
    """
    Filters the volunteer pool down to those who meet all hard eligibility rules for the slot.
    """
    candidates = []
    for vol in volunteers:
        is_ok, _ = check_eligibility(vol, slot, assigned_volunteer_ids)
        if is_ok:
            candidates.append(vol)
    return candidates
