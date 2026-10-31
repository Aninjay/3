import json
import hashlib
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from backend.app.auth_middleware import require_roles
from backend.app.db.connection import transaction, get_db, fetch_one, fetch_all, execute_query
from backend.app.allocation.schemas import VolunteerInput, RequirementInput
from backend.app.allocation.greedy import run_greedy_allocation
from backend.app.allocation.ilp_optimizer import run_ilp_allocation
from backend.app.allocation.compare import compare_algorithms
from backend.app.allocation.shortages import analyze_shortages
from backend.app.allocation.recommendations import generate_recommendations

allocation_bp = Blueprint("allocations", __name__)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_snapshot_data(conn, event_id: int):
    # Fetch requirements
    req_rows = fetch_all(conn, """
        SELECT er.*, d.name as department_name
        FROM event_requirements er
        JOIN departments d ON er.department_id = d.id
        WHERE er.event_id = %s
    """, (event_id,))

    requirements = []
    for r in req_rows:
        sk_rows = fetch_all(conn, """
            SELECT s.name, rs.is_mandatory, rs.is_preferred
            FROM requirement_skills rs
            JOIN skills s ON rs.skill_id = s.id
            WHERE rs.requirement_id = %s
        """, (r["id"],))

        m_skills = {s["name"] for s in sk_rows if s["is_mandatory"]}
        p_skills = {s["name"] for s in sk_rows if s["is_preferred"]}

        requirements.append(RequirementInput(
            id=r["id"],
            event_id=event_id,
            department_name=r["department_name"],
            role_name=r["role_name"],
            headcount=r["headcount"],
            priority=r["priority"].lower(),
            mandatory_skills=m_skills,
            preferred_skills=p_skills,
            duration_hours=float(r["duration_hours"] or 8.0)
        ))

    # Fetch active volunteers and their availability for this event
    vol_rows = fetch_all(conn, """
        SELECT vp.*, va.available, va.availability_start, va.availability_end, va.max_hours as event_max_hours
        FROM volunteer_profiles vp
        LEFT JOIN volunteer_availability va ON vp.id = va.volunteer_id AND va.event_id = %s
        WHERE vp.active_status = 1
    """, (event_id,))

    volunteers = []
    for v in vol_rows:
        sk_rows = fetch_all(conn, """
            SELECT s.name FROM skills s
            JOIN volunteer_skills vs ON s.id = vs.skill_id
            WHERE vs.volunteer_id = %s AND s.status = 'approved'
        """, (v["id"],))
        skills_set = {s["name"] for s in sk_rows}

        pref_rows = fetch_all(conn, """
            SELECT department_name FROM volunteer_preferences
            WHERE volunteer_id = %s ORDER BY preference_rank ASC
        """, (v["id"],))
        prefs = [p["department_name"] for p in pref_rows]

        is_avail = bool(v.get("available") if v.get("available") is not None else True)
        m_hours = float(v.get("event_max_hours") or 8.0)

        volunteers.append(VolunteerInput(
            id=v["id"],
            student_id=v["student_id"],
            name=v["full_name"],
            active=bool(v["active_status"]),
            skills=skills_set,
            available=is_avail,
            max_hours=m_hours,
            preferences=prefs
        ))

    # Compute fingerprint
    raw_sig = f"event:{event_id}|reqs:{len(requirements)}|vols:{len(volunteers)}"
    fingerprint = hashlib.sha256(raw_sig.encode()).hexdigest()[:16]

    return volunteers, requirements, fingerprint

@allocation_bp.route("/events/<int:event_id>/allocations/runs", methods=["POST"])
@require_roles("convener", "co_convener")
def run_allocation(event_id):
    data = request.get_json() or {}
    algo = data.get("algorithm", "ilp").lower() # 'greedy', 'ilp', or 'compare'
    actor_id = g.current_user["user_id"]
    ts = now_iso()

    with transaction() as conn:
        ev = fetch_one(conn, "SELECT * FROM events WHERE id = %s", (event_id,))
        if not ev:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404

        if ev["status"] in ("cancelled", "archived"):
            return jsonify({"error": {"code": "INVALID_STATE", "message": f"Cannot run allocation on {ev['status']} events."}}), 409

        vols, reqs, fingerprint = load_snapshot_data(conn, event_id)

        if not reqs:
            return jsonify({"error": {"code": "NO_REQUIREMENTS", "message": "No department requirements defined for this event."}}), 400

        # Execute algorithm
        if algo == "greedy":
            result = run_greedy_allocation(vols, reqs, fingerprint)
            comparison_data = None
        elif algo == "compare":
            comp = compare_algorithms(vols, reqs, fingerprint)
            result = comp["ilp_result"]
            comparison_data = comp
            algo = "ilp"
        else:
            result = run_ilp_allocation(vols, reqs, fingerprint)
            comparison_data = None

        # Shortages & recommendations
        shortages = analyze_shortages(result, vols, reqs)
        recommendations = generate_recommendations(result, vols, reqs)

        # 1. Save allocation run
        execute_query(conn, """
            INSERT INTO allocation_runs (
                event_id, algorithm, input_snapshot, input_fingerprint, solver_status,
                metrics, result_summary, run_by, created_at, is_simulation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
        """, (
            event_id, algo,
            json.dumps({"req_count": len(reqs), "vol_count": len(vols)}),
            fingerprint, result.solver_status or "Success",
            json.dumps({
                "coverage_pct": result.coverage_pct,
                "total_required": result.total_required,
                "total_allocated": result.total_allocated,
                "total_vacancies": result.total_vacancies,
                "runtime_seconds": result.runtime_seconds,
                "objective_value": result.objective_value
            }),
            json.dumps({"shortages": shortages, "recommendations": recommendations}),
            actor_id, ts
        ))
        run_row = fetch_one(conn, "SELECT id FROM allocation_runs WHERE event_id = %s ORDER BY id DESC LIMIT 1", (event_id,))
        run_id = run_row["id"]

        # 2. Determine version number
        last_ver = fetch_one(conn, "SELECT MAX(version_number) as m FROM allocation_versions WHERE event_id = %s", (event_id,))
        next_ver = (last_ver["m"] or 0) + 1

        # 3. Create draft allocation version
        execute_query(conn, """
            INSERT INTO allocation_versions (
                event_id, version_number, source_run_id, status, created_by, created_at, updated_at, change_summary, row_version
            ) VALUES (%s, %s, %s, 'draft', %s, %s, %s, %s, 1)
        """, (
            event_id, next_ver, run_id, actor_id, ts, ts,
            f"Generated via {algo.upper()} algorithm (Run #{run_id})"
        ))
        ver_row = fetch_one(conn, "SELECT id FROM allocation_versions WHERE event_id = %s AND version_number = %s", (event_id, next_ver))
        ver_id = ver_row["id"]

        # 4. Insert assignments
        for a in result.assignments:
            execute_query(conn, """
                INSERT INTO assignments (
                    allocation_version_id, requirement_id, volunteer_id, assigned_by,
                    assignment_source, skill_override, created_at
                ) VALUES (%s, %s, %s, %s, %s, 0, %s)
            """, (ver_id, a.requirement_id, a.volunteer_id, actor_id, a.assignment_source, ts))

        # 5. Audit
        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, after_data, reason, created_at)
            VALUES (%s, 'ALLOCATION_GENERATED', 'allocation_versions', %s, %s, %s, %s)
        """, (actor_id, ver_id, f"Generated version {next_ver} using {algo}", "Automated allocation execution", ts))

    return jsonify({
        "data": {
            "version_id": ver_id,
            "version_number": next_ver,
            "status": "draft",
            "algorithm": algo,
            "total_required": result.total_required,
            "total_allocated": result.total_allocated,
            "total_vacancies": result.total_vacancies,
            "coverage_pct": result.coverage_pct,
            "runtime_seconds": result.runtime_seconds,
            "solver_status": result.solver_status,
            "objective_value": result.objective_value,
            "comparison": comparison_data
        },
        "meta": {"message": f"Draft allocation version {next_ver} created successfully."}
    }), 201

@allocation_bp.route("/events/<int:event_id>/allocations", methods=["GET"])
@require_roles("convener", "co_convener")
def list_event_allocations(event_id):
    with get_db() as conn:
        versions = fetch_all(conn, """
            SELECT av.*, ar.algorithm, ar.solver_status,
                   u.email as creator_email,
                   (SELECT COUNT(*) FROM assignments a WHERE a.allocation_version_id = av.id) as allocated_count,
                   (SELECT COALESCE(SUM(headcount), 0) FROM event_requirements er WHERE er.event_id = av.event_id) as required_count,
                   pa.published_at
            FROM allocation_versions av
            LEFT JOIN allocation_runs ar ON av.source_run_id = ar.id
            LEFT JOIN users u ON av.created_by = u.id
            LEFT JOIN published_allocations pa ON av.id = pa.allocation_version_id
            WHERE av.event_id = %s
            ORDER BY av.version_number DESC
        """, (event_id,))

        for v in versions:
            v["vacant_count"] = max(0, v["required_count"] - v["allocated_count"])
            v["coverage_pct"] = round((v["allocated_count"] / v["required_count"] * 100.0), 1) if v["required_count"] > 0 else 0.0

    return jsonify({"data": versions}), 200

@allocation_bp.route("/allocations/<int:version_id>", methods=["GET"])
@require_roles("convener", "co_convener")
def get_allocation_version(version_id):
    with get_db() as conn:
        ver = fetch_one(conn, """
            SELECT av.*, ar.algorithm, ar.solver_status, ar.metrics, ar.result_summary,
                   e.id as event_id, e.name as event_name, e.status as event_status,
                   pa.published_at
            FROM allocation_versions av
            JOIN events e ON av.event_id = e.id
            LEFT JOIN allocation_runs ar ON av.source_run_id = ar.id
            LEFT JOIN published_allocations pa ON av.id = pa.allocation_version_id
            WHERE av.id = %s
        """, (version_id,))
        if not ver:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Allocation version not found."}}), 404

        # Assignments
        assignments = fetch_all(conn, """
            SELECT a.*, vp.student_id, vp.full_name as volunteer_name,
                   er.role_name, er.priority, er.headcount, d.name as department_name
            FROM assignments a
            JOIN volunteer_profiles vp ON a.volunteer_id = vp.id
            JOIN event_requirements er ON a.requirement_id = er.id
            JOIN departments d ON er.department_id = d.id
            WHERE a.allocation_version_id = %s
            ORDER BY d.name, er.role_name, vp.full_name
        """, (version_id,))

        # Department staffing totals
        reqs = fetch_all(conn, """
            SELECT er.id, er.role_name, er.headcount, er.priority, d.name as department_name
            FROM event_requirements er
            JOIN departments d ON er.department_id = d.id
            WHERE er.event_id = %s
            ORDER BY d.name, er.role_name
        """, (ver["event_id"],))

        dept_summary = {}
        for r in reqs:
            d = r["department_name"]
            if d not in dept_summary:
                dept_summary[d] = {"department": d, "required": 0, "allocated": 0, "vacant": 0}
            dept_summary[d]["required"] += r["headcount"]

        assigned_req_ids = [a["requirement_id"] for a in assignments]
        for a in assignments:
            d = a["department_name"]
            if d in dept_summary:
                dept_summary[d]["allocated"] += 1

        for d, s in dept_summary.items():
            s["vacant"] = max(0, s["required"] - s["allocated"])
            s["coverage_pct"] = round((s["allocated"] / s["required"] * 100.0), 1) if s["required"] > 0 else 0.0

        # Unassigned active volunteers
        assigned_vol_ids = [a["volunteer_id"] for a in assignments]
        all_active_vols = fetch_all(conn, """
            SELECT vp.id, vp.student_id, vp.full_name, vp.email
            FROM volunteer_profiles vp
            WHERE vp.active_status = 1
        """)
        unassigned = [v for v in all_active_vols if v["id"] not in assigned_vol_ids]

        ver["assignments"] = assignments
        ver["department_summary"] = list(dept_summary.values())
        ver["unassigned_volunteers"] = unassigned
        ver["total_required"] = sum(s["required"] for s in dept_summary.values())
        ver["total_allocated"] = len(assignments)
        ver["total_vacancies"] = max(0, ver["total_required"] - ver["total_allocated"])
        ver["coverage_pct"] = round((ver["total_allocated"] / ver["total_required"] * 100.0), 1) if ver["total_required"] > 0 else 0.0

    return jsonify({"data": ver}), 200

@allocation_bp.route("/allocations/<int:version_id>/assignments", methods=["PATCH"])
@require_roles("convener", "co_convener")
def edit_assignment(version_id):
    """
    Manual editing of draft assignments.
    Hard rules:
    - Inactive volunteer -> 422 blocked
    - Volunteer duplicate assignment in this version -> 422 blocked
    - Mandatory skill mismatch -> requires skill_override=True and non-empty override_reason
    - Editing an approved version invalidates approval -> status reverts to 'draft'
    - Editing a published version -> creates a new draft revision automatically
    """
    data = request.get_json() or {}
    operation = data.get("operation") # 'add', 'remove', 'replace'
    req_id = data.get("requirement_id")
    vol_id = data.get("volunteer_id")
    replacement_vol_id = data.get("replacement_volunteer_id")
    skill_override = bool(data.get("skill_override", False))
    override_reason = (data.get("override_reason") or "").strip()

    ts = now_iso()
    actor_id = g.current_user["user_id"]

    with transaction() as conn:
        ver = fetch_one(conn, "SELECT * FROM allocation_versions WHERE id = %s", (version_id,))
        if not ver:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Allocation version not found."}}), 404

        target_version_id = version_id

        # If already published, create a new draft revision rather than mutating published history
        if ver["status"] == "published":
            last_ver = fetch_one(conn, "SELECT MAX(version_number) as m FROM allocation_versions WHERE event_id = %s", (ver["event_id"],))
            new_v_num = last_ver["m"] + 1
            execute_query(conn, """
                INSERT INTO allocation_versions (
                    event_id, version_number, parent_version_id, source_run_id, status, created_by, created_at, updated_at, change_summary, row_version
                ) VALUES (%s, %s, %s, %s, 'draft', %s, %s, %s, %s, 1)
            """, (ver["event_id"], new_v_num, ver["id"], ver["source_run_id"], actor_id, ts, ts, f"Revision from published version {ver['version_number']}"))
            new_v = fetch_one(conn, "SELECT id FROM allocation_versions WHERE event_id = %s AND version_number = %s", (ver["event_id"], new_v_num))
            target_version_id = new_v["id"]

            # Copy existing assignments
            existing_assns = fetch_all(conn, "SELECT * FROM assignments WHERE allocation_version_id = %s", (ver["id"],))
            for ea in existing_assns:
                execute_query(conn, """
                    INSERT INTO assignments (allocation_version_id, requirement_id, volunteer_id, assigned_by, assignment_source, skill_override, override_reason, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (target_version_id, ea["requirement_id"], ea["volunteer_id"], ea["assigned_by"], ea["assignment_source"], ea["skill_override"], ea["override_reason"], ts))

        # Check candidate volunteer status
        candidate_id = replacement_vol_id if operation == "replace" else vol_id

        if operation in ("add", "replace"):
            c_prof = fetch_one(conn, "SELECT * FROM volunteer_profiles WHERE id = %s", (candidate_id,))
            if not c_prof:
                return jsonify({"error": {"code": "NOT_FOUND", "message": "Volunteer profile not found."}}), 404

            if not c_prof["active_status"]:
                return jsonify({
                    "error": {
                        "code": "INACTIVE_VOLUNTEER_BLOCKED",
                        "message": f"Volunteer {c_prof['student_id']} is inactive. Inactive volunteers cannot be assigned."
                    }
                }), 422

            # Check uniqueness in this version
            assigned_check = fetch_one(conn, """
                SELECT a.id, er.role_name, d.name as department_name
                FROM assignments a
                JOIN event_requirements er ON a.requirement_id = er.id
                JOIN departments d ON er.department_id = d.id
                WHERE a.allocation_version_id = %s AND a.volunteer_id = %s
            """, (target_version_id, candidate_id))

            if assigned_check:
                return jsonify({
                    "error": {
                        "code": "DUPLICATE_ASSIGNMENT_BLOCKED",
                        "message": f"Volunteer is already assigned to {assigned_check['department_name']} ({assigned_check['role_name']}) in this event version."
                    }
                }), 422

            # Check mandatory skills
            mand_skills = fetch_all(conn, """
                SELECT s.name FROM requirement_skills rs
                JOIN skills s ON rs.skill_id = s.id
                WHERE rs.requirement_id = %s AND rs.is_mandatory = 1
            """, (req_id,))

            vol_skills = fetch_all(conn, """
                SELECT s.name FROM volunteer_skills vs
                JOIN skills s ON vs.skill_id = s.id
                WHERE vs.volunteer_id = %s
            """, (candidate_id,))

            mand_set = {s["name"] for s in mand_skills}
            vol_set = {s["name"] for s in vol_skills}
            missing = mand_set - vol_set

            if missing:
                if not skill_override:
                    return jsonify({
                        "warning": {
                            "code": "SKILL_MISMATCH_CONFIRMATION_REQUIRED",
                            "message": f"Volunteer {c_prof['student_id']} lacks mandatory skill(s): {', '.join(sorted(missing))}. An organizer override and non-empty reason are required to proceed.",
                            "missing_skills": list(missing)
                        }
                    }), 400

                if not override_reason:
                    return jsonify({
                        "error": {
                            "code": "OVERRIDE_REASON_REQUIRED",
                            "message": "A non-empty override reason is required when manually overriding a mandatory skill mismatch."
                        }
                    }), 422

        # Perform operation
        if operation == "remove":
            execute_query(conn, "DELETE FROM assignments WHERE allocation_version_id = %s AND requirement_id = %s AND volunteer_id = %s", (target_version_id, req_id, vol_id))
            execute_query(conn, """
                INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
                VALUES (%s, 'MANUAL_ASSIGNMENT_REMOVE', 'assignments', %s, %s, %s)
            """, (actor_id, target_version_id, f"Removed volunteer {vol_id} from requirement {req_id}", ts))

        elif operation == "add":
            execute_query(conn, """
                INSERT INTO assignments (
                    allocation_version_id, requirement_id, volunteer_id, assigned_by,
                    assignment_source, skill_override, override_reason, created_at
                ) VALUES (%s, %s, %s, %s, 'manual', %s, %s, %s)
            """, (target_version_id, req_id, candidate_id, actor_id, 1 if skill_override else 0, override_reason or None, ts))
            execute_query(conn, """
                INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
                VALUES (%s, 'MANUAL_ASSIGNMENT_ADD', 'assignments', %s, %s, %s)
            """, (actor_id, target_version_id, f"Added volunteer {candidate_id} to requirement {req_id}. Reason: {override_reason or 'Direct assignment'}", ts))

        elif operation == "replace":
            execute_query(conn, "DELETE FROM assignments WHERE allocation_version_id = %s AND requirement_id = %s AND volunteer_id = %s", (target_version_id, req_id, vol_id))
            execute_query(conn, """
                INSERT INTO assignments (
                    allocation_version_id, requirement_id, volunteer_id, assigned_by,
                    assignment_source, skill_override, override_reason, created_at
                ) VALUES (%s, %s, %s, %s, 'manual', %s, %s, %s)
            """, (target_version_id, req_id, replacement_vol_id, actor_id, 1 if skill_override else 0, override_reason or None, ts))
            execute_query(conn, """
                INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
                VALUES (%s, 'MANUAL_ASSIGNMENT_REPLACE', 'assignments', %s, %s, %s)
            """, (actor_id, target_version_id, f"Replaced volunteer {vol_id} with {replacement_vol_id}. Reason: {override_reason or 'Manual replacement'}", ts))

        # Invalidate approval if version was previously approved
        if ver["status"] == "approved":
            execute_query(conn, "UPDATE allocation_versions SET status = 'draft', change_summary = 'Approval invalidated due to manual edit' WHERE id = %s", (target_version_id,))

        execute_query(conn, "UPDATE allocation_versions SET updated_at = %s, row_version = row_version + 1 WHERE id = %s", (ts, target_version_id))

    return jsonify({
        "data": {"version_id": target_version_id},
        "meta": {"message": "Assignment successfully updated."}
    }), 200

@allocation_bp.route("/allocations/<int:version_id>/approve", methods=["POST"])
@require_roles("convener", "co_convener")
def approve_allocation(version_id):
    data = request.get_json() or {}
    comment = data.get("comment", "Approved by organizer")
    actor_id = g.current_user["user_id"]
    ts = now_iso()

    with transaction() as conn:
        ver = fetch_one(conn, "SELECT * FROM allocation_versions WHERE id = %s", (version_id,))
        if not ver:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Allocation version not found."}}), 404

        execute_query(conn, "UPDATE allocation_versions SET status = 'approved', updated_at = %s WHERE id = %s", (ts, version_id))
        execute_query(conn, """
            INSERT INTO allocation_approvals (allocation_version_id, approved_by, decision, comment, created_at)
            VALUES (%s, %s, 'approved', %s, %s)
        """, (version_id, actor_id, comment, ts))
        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
            VALUES (%s, 'ALLOCATION_APPROVED', 'allocation_versions', %s, %s, %s)
        """, (actor_id, version_id, comment, ts))

    return jsonify({"meta": {"message": f"Allocation version {ver['version_number']} approved."}}), 200

@allocation_bp.route("/allocations/<int:version_id>/reject", methods=["POST"])
@require_roles("convener", "co_convener")
def reject_allocation(version_id):
    data = request.get_json() or {}
    comment = data.get("comment", "Rejected by organizer")
    actor_id = g.current_user["user_id"]
    ts = now_iso()

    with transaction() as conn:
        ver = fetch_one(conn, "SELECT * FROM allocation_versions WHERE id = %s", (version_id,))
        if not ver:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Allocation version not found."}}), 404

        execute_query(conn, "UPDATE allocation_versions SET status = 'rejected', updated_at = %s WHERE id = %s", (ts, version_id))
        execute_query(conn, """
            INSERT INTO allocation_approvals (allocation_version_id, approved_by, decision, comment, created_at)
            VALUES (%s, %s, 'rejected', %s, %s)
        """, (version_id, actor_id, comment, ts))

    return jsonify({"meta": {"message": f"Allocation version {ver['version_number']} rejected."}}), 200

@allocation_bp.route("/allocations/<int:version_id>/publish", methods=["POST"])
@require_roles("convener", "co_convener")
def publish_allocation(version_id):
    """
    Publishes an approved allocation version.
    Transactionally updates the published_allocations pointer.
    Previous published version remains untouched in history.
    """
    actor_id = g.current_user["user_id"]
    ts = now_iso()

    with transaction() as conn:
        ver = fetch_one(conn, "SELECT * FROM allocation_versions WHERE id = %s", (version_id,))
        if not ver:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Allocation version not found."}}), 404

        if ver["status"] != "approved":
            return jsonify({
                "error": {
                    "code": "APPROVAL_REQUIRED",
                    "message": "Only approved allocation versions can be published. Please approve this version first."
                }
            }), 400

        event_id = ver["event_id"]

        # Mark any previous published version as superseded
        execute_query(conn, """
            UPDATE allocation_versions
            SET status = 'superseded', updated_at = %s
            WHERE event_id = %s AND status = 'published' AND id != %s
        """, (ts, event_id, version_id))

        # Update this version to published
        execute_query(conn, "UPDATE allocation_versions SET status = 'published', updated_at = %s WHERE id = %s", (ts, version_id))

        # Transactionally upsert published_allocations pointer
        existing_pub = fetch_one(conn, "SELECT * FROM published_allocations WHERE event_id = %s", (event_id,))
        if existing_pub:
            execute_query(conn, """
                UPDATE published_allocations
                SET allocation_version_id = %s, published_by = %s, published_at = %s
                WHERE event_id = %s
            """, (version_id, actor_id, ts, event_id))
        else:
            execute_query(conn, """
                INSERT INTO published_allocations (event_id, allocation_version_id, published_by, published_at)
                VALUES (%s, %s, %s, %s)
            """, (event_id, version_id, actor_id, ts))

        # Audit
        execute_query(conn, """
            INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, reason, created_at)
            VALUES (%s, 'ALLOCATION_PUBLISHED', 'allocation_versions', %s, 'Published official allocation version', %s)
        """, (actor_id, version_id, ts))

    return jsonify({"meta": {"message": f"Allocation version {ver['version_number']} is now officially published!"}}), 200

@allocation_bp.route("/allocations/<int:version_id>/regenerate", methods=["POST"])
@require_roles("convener", "co_convener")
def regenerate_allocation(version_id):
    """
    Explicitly regenerates an allocation after confirmation.
    Creates a new draft version.
    """
    data = request.get_json() or {}
    confirmed = bool(data.get("confirmed", False))
    algo = data.get("algorithm", "ilp").lower()

    if not confirmed:
        return jsonify({
            "error": {
                "code": "CONFIRMATION_REQUIRED",
                "message": "Explicit confirmation is required to regenerate an allocation."
            }
        }), 400

    with get_db() as conn:
        ver = fetch_one(conn, "SELECT event_id FROM allocation_versions WHERE id = %s", (version_id,))
        if not ver:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Allocation version not found."}}), 404
        event_id = ver["event_id"]

    # Call run_allocation directly to create new draft version
    return run_allocation(event_id)
