from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional, Any

@dataclass
class VolunteerInput:
    id: int
    student_id: str
    name: str
    active: bool = True
    skills: Set[str] = field(default_factory=set)
    available: bool = True
    availability_start: str = "09:00"
    availability_end: str = "21:00"
    max_hours: float = 8.0
    experience_level: str = "0 yrs"
    preferences: List[str] = field(default_factory=list) # Ranked department names
    is_simulated: bool = False

@dataclass
class RequirementInput:
    id: int
    event_id: int
    department_name: str
    role_name: str
    headcount: int
    priority: str # 'critical', 'high', 'normal'
    mandatory_skills: Set[str] = field(default_factory=set)
    preferred_skills: Set[str] = field(default_factory=set)
    duration_hours: float = 8.0
    requirement_source: str = "fixed_headcount" # 'fixed_headcount' or 'workload_calculation'
    workload_value: Optional[float] = None
    workload_unit: Optional[str] = None
    service_time_value: Optional[float] = None
    service_time_unit: Optional[str] = None
    peak_window_value: Optional[float] = None
    peak_window_unit: Optional[str] = None

@dataclass
class PositionSlot:
    slot_id: str # e.g. "req-1-slot-0"
    requirement_id: int
    slot_index: int
    department_name: str
    role_name: str
    priority: str
    mandatory_skills: Set[str]
    preferred_skills: Set[str]
    duration_hours: float

@dataclass
class AssignmentResult:
    slot_id: str
    requirement_id: int
    slot_index: int
    department_name: str
    role_name: str
    priority: str
    volunteer_id: int
    volunteer_student_id: str
    volunteer_name: str
    assignment_source: str # 'greedy', 'ilp', 'manual'
    skill_fit_score: float = 1.0
    preferred_skills_matched: List[str] = field(default_factory=list)
    preference_rank: Optional[int] = None
    skill_override: bool = False
    override_reason: Optional[str] = None
    is_simulated: bool = False

@dataclass
class VacancyResult:
    slot_id: str
    requirement_id: int
    slot_index: int
    department_name: str
    role_name: str
    priority: str
    mandatory_skills: List[str]
    reason: str
    eligible_unassigned_candidates: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AllocationResult:
    algorithm: str # 'greedy' or 'ilp'
    snapshot_fingerprint: str
    total_required: int
    total_allocated: int
    total_vacancies: int
    coverage_pct: float
    assignments: List[AssignmentResult]
    vacancies: List[VacancyResult]
    department_metrics: Dict[str, Dict[str, Any]]
    priority_metrics: Dict[str, Dict[str, Any]]
    unassigned_volunteers: List[Dict[str, Any]]
    shortage_reasons: List[Dict[str, Any]]
    solver_status: Optional[str] = None
    objective_value: Optional[float] = None
    runtime_seconds: float = 0.0
