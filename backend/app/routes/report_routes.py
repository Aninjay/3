import io
import json
import csv
import re
from flask import Blueprint, request, jsonify, send_file, g
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from werkzeug.utils import secure_filename
from backend.app.auth_middleware import require_roles
from backend.app.db.connection import get_db, fetch_one, fetch_all
from backend.app.allocation.compare import compare_algorithms
from backend.app.allocation.shortages import analyze_shortages
from backend.app.allocation.recommendations import generate_recommendations
from backend.app.allocation.ilp_optimizer import run_ilp_allocation
from backend.app.routes.allocation_routes import load_snapshot_data

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

report_bp = Blueprint("reports", __name__)

@report_bp.route("/events/<int:event_id>/reports/staffing", methods=["GET"])
@require_roles("convener", "co_convener")
def get_staffing_report(event_id):
    version_id = request.args.get("version_id")
    with get_db() as conn:
        published = fetch_one(conn, """
            SELECT pa.allocation_version_id, pa.published_at
            FROM published_allocations pa
            JOIN allocation_versions av ON av.id = pa.allocation_version_id
            WHERE pa.event_id = %s AND av.status = 'published'
        """, (event_id,))
        published_version_id = published["allocation_version_id"] if published else None
        if not version_id:
            # Default to published version, or latest draft version
            if published:
                version_id = published_version_id
            else:
                latest = fetch_one(conn, "SELECT id FROM allocation_versions WHERE event_id = %s ORDER BY version_number DESC LIMIT 1", (event_id,))
                if latest:
                    version_id = latest["id"]

        if not version_id:
            return jsonify({"data": {"message": "No allocation runs found for this event."}}), 200

        ver = fetch_one(conn, "SELECT * FROM allocation_versions WHERE id = %s", (version_id,))
        if not ver:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Allocation version not found."}}), 404

        # Requirements
        reqs = fetch_all(conn, """
            SELECT er.id, er.role_name, er.headcount, er.priority, d.name as department_name
            FROM event_requirements er
            JOIN departments d ON er.department_id = d.id
            WHERE er.event_id = %s
            ORDER BY d.name
        """, (event_id,))

        dept_map = {}
        for r in reqs:
            d = r["department_name"]
            if d not in dept_map:
                dept_map[d] = {"department": d, "required": 0, "allocated": 0, "vacant": 0}
            dept_map[d]["required"] += r["headcount"]

        assignments = fetch_all(conn, """
            SELECT a.*, d.name as department_name, er.priority
            FROM assignments a
            JOIN event_requirements er ON a.requirement_id = er.id
            JOIN departments d ON er.department_id = d.id
            WHERE a.allocation_version_id = %s
        """, (version_id,))

        prio_map = {
            "critical": {"required": 0, "allocated": 0, "vacant": 0},
            "high": {"required": 0, "allocated": 0, "vacant": 0},
            "normal": {"required": 0, "allocated": 0, "vacant": 0}
        }
        for r in reqs:
            prio_map[r["priority"].lower()]["required"] += r["headcount"]

        for a in assignments:
            d = a["department_name"]
            if d in dept_map:
                dept_map[d]["allocated"] += 1
            p = a["priority"].lower()
            if p in prio_map:
                prio_map[p]["allocated"] += 1

        for d, m in dept_map.items():
            m["vacant"] = max(0, m["required"] - m["allocated"])
            m["coverage_pct"] = round((m["allocated"] / m["required"] * 100.0), 1) if m["required"] > 0 else 0.0

        for p, m in prio_map.items():
            m["vacant"] = max(0, m["required"] - m["allocated"])
            m["coverage_pct"] = round((m["allocated"] / m["required"] * 100.0), 1) if m["required"] > 0 else 0.0

        total_req = sum(m["required"] for m in dept_map.values())
        total_alloc = len(assignments)

    return jsonify({
        "data": {
            "version_id": version_id,
            "version_number": ver["version_number"],
            "status": ver["status"],
            "published_version_id": published_version_id,
            "published_at": published["published_at"] if published else None,
            "can_export_roster": published_version_id is not None and str(version_id) == str(published_version_id),
            "total_required": total_req,
            "total_allocated": total_alloc,
            "total_vacancies": max(0, total_req - total_alloc),
            "coverage_pct": round((total_alloc / total_req * 100.0), 1) if total_req > 0 else 0.0,
            "department_breakdown": list(dept_map.values()),
            "priority_breakdown": prio_map
        }
    }), 200


def _safe_sheet_title(name, used_titles):
    base = re.sub(r"[\\/*?:\[\]]", " ", name).strip()[:31] or "Department"
    title = base
    suffix = 2
    while title.casefold() in used_titles:
        marker = f" {suffix}"
        title = f"{base[:31 - len(marker)]}{marker}"
        suffix += 1
    used_titles.add(title.casefold())
    return title


@report_bp.route("/events/<int:event_id>/reports/roster", methods=["GET"])
@require_roles("convener", "co_convener")
def export_published_roster(event_id):
    """Download the current published roster as a CSV or a multi-sheet Excel workbook."""
    output_format = request.args.get("format", "xlsx").strip().lower()
    if output_format not in {"csv", "xlsx"}:
        return jsonify({"error": {"code": "INVALID_FORMAT", "message": "Choose csv or xlsx."}}), 400

    with get_db() as conn:
        event = fetch_one(conn, "SELECT id, name FROM events WHERE id = %s", (event_id,))
        if not event:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Event not found."}}), 404

        published = fetch_one(conn, """
            SELECT pa.allocation_version_id, pa.published_at, av.version_number, av.status
            FROM published_allocations pa
            JOIN allocation_versions av ON av.id = pa.allocation_version_id
            WHERE pa.event_id = %s
        """, (event_id,))
        if not published or published["status"] != "published":
            return jsonify({
                "error": {
                    "code": "ALLOCATION_NOT_PUBLISHED",
                    "message": "Roster exports are available after an allocation has been published."
                }
            }), 409

        version_id = published["allocation_version_id"]
        departments = fetch_all(conn, """
            SELECT d.name AS department_name,
                   COALESCE(SUM(er.headcount), 0) AS required,
                   (
                       SELECT COUNT(*)
                       FROM assignments a
                       JOIN event_requirements assigned_er ON assigned_er.id = a.requirement_id
                       WHERE a.allocation_version_id = %s
                         AND assigned_er.event_id = %s
                         AND assigned_er.department_id = d.id
                   ) AS allocated
            FROM event_requirements er
            JOIN departments d ON d.id = er.department_id
            WHERE er.event_id = %s
            GROUP BY d.id, d.name
            ORDER BY d.name
        """, (version_id, event_id, event_id))
        assignments = fetch_all(conn, """
            SELECT d.name AS department_name, er.role_name, er.priority,
                   vp.full_name AS volunteer_name, vp.student_id
            FROM assignments a
            JOIN event_requirements er ON er.id = a.requirement_id
            JOIN departments d ON d.id = er.department_id
            JOIN volunteer_profiles vp ON vp.id = a.volunteer_id
            WHERE a.allocation_version_id = %s AND er.event_id = %s
            ORDER BY d.name, er.role_name, vp.full_name
        """, (version_id, event_id))

    safe_event_name = secure_filename(event["name"]).lower() or "event"
    version_number = published["version_number"]
    headers = ["Department", "Role", "Priority", "Volunteer Name", "Student ID"]
    roster_rows = [
        [row["department_name"], row["role_name"], row["priority"].title(), row["volunteer_name"], row["student_id"]]
        for row in assignments
    ]

    if output_format == "csv":
        text_buffer = io.StringIO(newline="")
        writer = csv.writer(text_buffer)
        writer.writerow(headers)
        writer.writerows(roster_rows)
        buffer = io.BytesIO(text_buffer.getvalue().encode("utf-8-sig"))
        filename = f"{safe_event_name}-roster-v{version_number}.csv"
        mimetype = "text/csv"
    else:
        workbook = Workbook()
        summary = workbook.active
        summary.title = "Roster Summary"
        summary["A1"] = f"{event['name']} Department Rosters"
        summary["A1"].font = Font(size=16, bold=True, color="242424")
        summary["A2"] = f"Published allocation version {version_number} · {published['published_at']}"
        summary_headers = ["Department", "Required", "Assigned", "Vacant", "Coverage"]
        for column, value in enumerate(summary_headers, start=1):
            cell = summary.cell(row=4, column=column, value=value)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(fill_type="solid", fgColor="E8752E")
        for row_index, department in enumerate(departments, start=5):
            required = int(department["required"] or 0)
            allocated = int(department["allocated"] or 0)
            values = [
                department["department_name"], required, allocated,
                max(0, required - allocated),
                allocated / required if required else 0,
            ]
            for column, value in enumerate(values, start=1):
                summary.cell(row=row_index, column=column, value=value)
            summary.cell(row=row_index, column=5).number_format = "0.0%"
        summary.freeze_panes = "A5"
        if departments:
            summary.auto_filter.ref = f"A4:E{4 + len(departments)}"
        for column, width in enumerate([38, 12, 12, 12, 14], start=1):
            summary.column_dimensions[get_column_letter(column)].width = width

        used_titles = {"roster summary"}
        assignments_by_department = {}
        for row in roster_rows:
            assignments_by_department.setdefault(row[0], []).append(row[1:])
        for department in departments:
            department_name = department["department_name"]
            sheet = workbook.create_sheet(_safe_sheet_title(department_name, used_titles))
            sheet["A1"] = f"{department_name} · {event['name']}"
            sheet["A1"].font = Font(size=15, bold=True, color="242424")
            sheet["A2"] = f"Published allocation version {version_number} · {published['published_at']}"
            for column, value in enumerate(headers[1:], start=1):
                cell = sheet.cell(row=4, column=column, value=value)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor="E8752E")
            rows = assignments_by_department.get(department_name, [])
            if rows:
                for row in rows:
                    sheet.append(row)
            else:
                sheet.cell(row=5, column=1, value="No volunteers assigned")
            sheet.freeze_panes = "A5"
            if rows:
                sheet.auto_filter.ref = f"A4:D{4 + len(rows)}"
            for column, width in enumerate([28, 14, 30, 18], start=1):
                sheet.column_dimensions[get_column_letter(column)].width = width

        workbook.properties.title = f"{event['name']} Department Rosters"
        workbook.properties.subject = f"Published allocation version {version_number}"
        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        filename = f"{safe_event_name}-department-rosters-v{version_number}.xlsx"
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    response = send_file(buffer, mimetype=mimetype, as_attachment=True, download_name=filename, max_age=0)
    response.headers["Cache-Control"] = "no-store"
    return response

@report_bp.route("/events/<int:event_id>/reports/underutilization", methods=["GET"])
@require_roles("convener", "co_convener")
def get_underutilization_report(event_id):
    version_id = request.args.get("version_id")
    with get_db() as conn:
        if not version_id:
            pub = fetch_one(conn, "SELECT allocation_version_id FROM published_allocations WHERE event_id = %s", (event_id,))
            if pub:
                version_id = pub["allocation_version_id"]
            else:
                latest = fetch_one(conn, "SELECT id FROM allocation_versions WHERE event_id = %s ORDER BY version_number DESC LIMIT 1", (event_id,))
                if latest:
                    version_id = latest["id"]

        assigned_vol_ids = set()
        if version_id:
            assns = fetch_all(conn, "SELECT volunteer_id FROM assignments WHERE allocation_version_id = %s", (version_id,))
            assigned_vol_ids = {a["volunteer_id"] for a in assns}

        all_active_vols = fetch_all(conn, """
            SELECT vp.*, va.available, va.max_hours
            FROM volunteer_profiles vp
            LEFT JOIN volunteer_availability va ON vp.id = va.volunteer_id AND va.event_id = %s
            WHERE vp.active_status = 1
        """, (event_id,))

        unassigned = []
        for v in all_active_vols:
            if v["id"] not in assigned_vol_ids:
                skills = fetch_all(conn, """
                    SELECT s.name FROM skills s
                    JOIN volunteer_skills vs ON s.id = vs.skill_id
                    WHERE vs.volunteer_id = %s
                """, (v["id"],))
                v["skills"] = [s["name"] for s in skills]
                unassigned.append(v)

    return jsonify({
        "data": {
            "total_active_volunteers": len(all_active_vols),
            "total_allocated": len(assigned_vol_ids),
            "total_unassigned": len(unassigned),
            "unassigned_volunteers": unassigned
        }
    }), 200

@report_bp.route("/events/<int:event_id>/reports/algorithm-comparison", methods=["GET"])
@require_roles("convener", "co_convener")
def get_algorithm_comparison(event_id):
    with get_db() as conn:
        vols, reqs, fingerprint = load_snapshot_data(conn, event_id)
        if not reqs:
            return jsonify({"error": {"code": "NO_REQUIREMENTS", "message": "No requirements found."}}), 400

        comp = compare_algorithms(vols, reqs, fingerprint)

    return jsonify({"data": comp}), 200

@report_bp.route("/events/<int:event_id>/reports/recommendations", methods=["GET"])
@require_roles("convener", "co_convener")
def get_recommendations_report(event_id):
    with get_db() as conn:
        vols, reqs, fingerprint = load_snapshot_data(conn, event_id)
        if not reqs:
            return jsonify({"data": []}), 200

        result = run_ilp_allocation(vols, reqs, fingerprint)
        recs = generate_recommendations(result, vols, reqs)

    return jsonify({"data": recs}), 200

@report_bp.route("/audit-log", methods=["GET"])
@require_roles("convener", "co_convener")
def get_audit_log():
    limit = int(request.args.get("limit", 100))
    with get_db() as conn:
        logs = fetch_all(conn, """
            SELECT al.*, u.email as actor_email
            FROM audit_log al
            LEFT JOIN users u ON al.actor_user_id = u.id
            ORDER BY al.id DESC
            LIMIT %s
        """, (limit,))
    return jsonify({"data": logs}), 200

@report_bp.route("/events/<int:event_id>/reports/chart", methods=["GET"])
@require_roles("convener", "co_convener")
def generate_chart(event_id):
    """
    Renders clean, restrained Matplotlib bar chart of Required vs. Allocated.
    Palette matches UI_UX_SPEC: warm orange #E8752E for allocated, subtle border #E7E5E2 / muted text #6B6B6B.
    """
    with get_db() as conn:
        pub = fetch_one(conn, "SELECT allocation_version_id FROM published_allocations WHERE event_id = %s", (event_id,))
        version_id = pub["allocation_version_id"] if pub else None
        if not version_id:
            latest = fetch_one(conn, "SELECT id FROM allocation_versions WHERE event_id = %s ORDER BY version_number DESC LIMIT 1", (event_id,))
            version_id = latest["id"] if latest else None

        reqs = fetch_all(conn, """
            SELECT d.name as department, SUM(er.headcount) as required
            FROM event_requirements er
            JOIN departments d ON er.department_id = d.id
            WHERE er.event_id = %s
            GROUP BY d.name
            ORDER BY d.name
        """, (event_id,))

        if not reqs:
            return jsonify({"error": {"code": "NO_DATA", "message": "No requirement data for chart."}}), 404

        dept_names = [r["department"] for r in reqs]
        req_counts = [r["required"] for r in reqs]
        alloc_counts = []

        for r in reqs:
            if version_id:
                cnt = fetch_one(conn, """
                    SELECT COUNT(*) as c FROM assignments a
                    JOIN event_requirements er ON a.requirement_id = er.id
                    JOIN departments d ON er.department_id = d.id
                    WHERE a.allocation_version_id = %s AND d.name = %s
                """, (version_id, r["department"]))
                alloc_counts.append(cnt["c"])
            else:
                alloc_counts.append(0)

    # Generate Matplotlib chart
    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFAFA")

    x = range(len(dept_names))
    width = 0.35

    ax.bar([i - width/2 for i in x], req_counts, width, label="Required", color="#D1D5DB", edgecolor="#9CA3AF")
    ax.bar([i + width/2 for i in x], alloc_counts, width, label="Allocated", color="#E8752E", edgecolor="#C95D1D")

    ax.set_ylabel("Headcount", fontsize=11, color="#242424", fontweight="medium")
    ax.set_title(f"Staffing by Department — Kala Fest (Version #{version_id or 'Draft'})", fontsize=13, color="#242424", fontweight="bold", pad=12)
    ax.set_xticks(list(x))
    ax.set_xticklabels([d.replace("&", "&\n") for d in dept_names], rotation=15, ha="right", fontsize=9, color="#242424")
    ax.legend(frameon=True, facecolor="#FFFFFF", edgecolor="#E7E5E2")
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#E7E5E2")

    for spine in ax.spines.values():
        spine.set_color("#E7E5E2")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120)
    buf.seek(0)
    plt.close(fig)

    return send_file(buf, mimetype="image/png")
