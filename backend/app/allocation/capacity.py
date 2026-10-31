import math
from typing import Dict, Any

def calculate_workload_capacity(
    workload_value: float,
    service_time_value: float,
    peak_window_value: float
) -> Dict[str, Any]:
    """
    Calculates staffing requirements using the formula:
    Required Staff = ceil(Workload * Service Time / Peak Window)
    """
    if workload_value is None or workload_value < 0:
        raise ValueError("Workload value must be non-negative.")
    if service_time_value is None or service_time_value < 0:
        raise ValueError("Service time value must be non-negative.")
    if peak_window_value is None or peak_window_value <= 0:
        raise ValueError("Peak window value must be greater than zero.")

    raw_demand = (workload_value * service_time_value) / peak_window_value
    headcount = math.ceil(raw_demand)
    return {
        "workload_value": workload_value,
        "service_time_value": service_time_value,
        "peak_window_value": peak_window_value,
        "raw_demand": round(raw_demand, 3),
        "calculated_headcount": headcount,
        "formula": "ceil(Workload * Service Time / Peak Window)"
    }
