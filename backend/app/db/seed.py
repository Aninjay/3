import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from werkzeug.security import generate_password_hash
from backend.app.db.connection import transaction, fetch_one, fetch_all, execute_query, is_postgres
from backend.app.config import Config

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

DEPARTMENTS = [
    {"name": "Stage & Backstage Management", "description": "Stage logistics, greenroom, lighting, and audio management"},
    {"name": "Sponsorship & Fundraising", "description": "Brand partnerships, corporate sponsorship, stall management"},
    {"name": "IT & Technical Support", "description": "Audio-visual systems, networking, projection, live streams"},
    {"name": "Logistics & Operations", "description": "Procurement, stage setup, vendor coordination, materials transport"},
    {"name": "Marketing & Promotions", "description": "Social media, campus outreach, poster design, brand engagement"},
    {"name": "Participant Coordination", "description": "Artist liaison, contestant registration, hospitality desks"},
    {"name": "Hospitality & Guest Handling", "description": "VIP reception, travel, accommodation, campus guides"},
    {"name": "Crowd Management & Security", "description": "Access control, queue management, safety guidelines"},
]

STANDARD_SKILLS = [
    "Technical Support",
    "Networking",
    "Stage & Backstage Management",
    "Logistics",
    "Vendor Management",
    "Stall Management",
    "Event Coordination",
    "Team Leadership",
    "Participant Coordination",
    "Marketing & Promotions",
    "Social Media & Content Creation",
    "Branding & Visual Design",
    "Public Relations & Outreach",
    "Anchoring & Public Speaking",
    "Theatre & Acting",
    "Scriptwriting",
    "Art, Props & Decoration",
    "Dance & Choreography",
    "Event Volunteering",
    "Sponsorship & Fundraising",
    "Budgeting & Finance",
    "Hospitality & Guest Handling",
    "Crowd Management & Security",
]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def normalize_name_to_email(name: str, student_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", name).strip().lower()
    parts = cleaned.split()
    if not parts:
        return f"{student_id.lower()}@tapmi.edu.in"
    if len(parts) == 1:
        return f"{parts[0]}.{student_id.lower()}@tapmi.edu.in"
    return f"{parts[0]}.{parts[-1]}@tapmi.edu.in"

def seed_database():
    ts = now_iso()
    seed_demo_data = os.environ.get("SEED_DEMO_DATA", "false").strip().lower() in {"1", "true", "yes", "on"}
    bootstrap_email = os.environ.get("BOOTSTRAP_CONVENER_EMAIL", "").strip().lower()
    bootstrap_password = os.environ.get("BOOTSTRAP_CONVENER_PASSWORD", "")
    if bool(bootstrap_email) != bool(bootstrap_password):
        raise ValueError("Set both BOOTSTRAP_CONVENER_EMAIL and BOOTSTRAP_CONVENER_PASSWORD, or leave both empty.")
    if bootstrap_password and len(bootstrap_password) < 12:
        raise ValueError("BOOTSTRAP_CONVENER_PASSWORD must contain at least 12 characters.")

    print("Seeding database...")
    with transaction() as conn:
        # Seed known demo logins only when demo data is enabled.
        organizers = []
        if seed_demo_data:
            organizers.extend([
                ("convener@tapmi.edu.in", "Convener Lead", "convener", "convener123"),
                ("coconvener@tapmi.edu.in", "Co-Convener Deputy", "co_convener", "coconvener123"),
            ])
        org_ids = {}
        for email, full_name, role, pwd in organizers:
            existing = fetch_one(conn, "SELECT id FROM users WHERE email = %s", (email,))
            if not existing:
                pwd_hash = generate_password_hash(pwd)
                execute_query(conn, """
                    INSERT INTO users (email, login_id, password_hash, role, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'active', %s, %s)
                """, (email, email, pwd_hash, role, ts, ts))
                row = fetch_one(conn, "SELECT id FROM users WHERE email = %s", (email,))
                org_ids[role] = row['id']
            else:
                org_ids[role] = existing['id']

        # Production deployments can bootstrap one organizer without installing
        # the predictable demo accounts or the sample volunteer/event records.
        if bootstrap_email:
            existing = fetch_one(conn, "SELECT id, role FROM users WHERE email = %s", (bootstrap_email,))
            if existing:
                if existing["role"] not in ("convener", "co_convener"):
                    raise ValueError("BOOTSTRAP_CONVENER_EMAIL already belongs to a non-organizer account.")
                org_ids.setdefault("convener", existing["id"])
            else:
                execute_query(conn, """
                    INSERT INTO users (email, login_id, password_hash, role, status, created_at, updated_at)
                    VALUES (%s, %s, %s, 'convener', 'active', %s, %s)
                """, (bootstrap_email, bootstrap_email, generate_password_hash(bootstrap_password), ts, ts))
                row = fetch_one(conn, "SELECT id FROM users WHERE email = %s", (bootstrap_email,))
                org_ids.setdefault("convener", row["id"])

        convener_id = org_ids.get("convener")

        # 2. Seed Departments
        dept_ids = {}
        for d in DEPARTMENTS:
            existing = fetch_one(conn, "SELECT id FROM departments WHERE name = %s", (d["name"],))
            if not existing:
                execute_query(conn, """
                    INSERT INTO departments (name, description, active)
                    VALUES (%s, %s, 1)
                """, (d["name"], d["description"]))
                row = fetch_one(conn, "SELECT id FROM departments WHERE name = %s", (d["name"],))
                dept_ids[d["name"]] = row['id']
            else:
                dept_ids[d["name"]] = existing['id']

        # 3. Seed Skills
        skill_ids = {}
        for sname in STANDARD_SKILLS:
            existing = fetch_one(conn, "SELECT id FROM skills WHERE name = %s", (sname,))
            if not existing:
                execute_query(conn, """
                    INSERT INTO skills (name, description, status, created_by, approved_by, approved_at, created_at)
                    VALUES (%s, %s, 'approved', %s, %s, %s, %s)
                """, (sname, f"Standard skill: {sname}", convener_id, convener_id, ts, ts))
                row = fetch_one(conn, "SELECT id FROM skills WHERE name = %s", (sname,))
                skill_ids[sname] = row['id']
            else:
                skill_ids[sname] = existing['id']

        # 4. Seed Volunteers from CSV if available
        csv_path = BASE_DIR / "volunteers CSV.csv"
        volunteers_seeded = 0
        if seed_demo_data and csv_path.exists():
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    v_id = row["volunteer_id"].strip()
                    name = row["name"].strip()
                    interviewed_by = row.get("interviewed_by", "").strip()
                    email = normalize_name_to_email(name, v_id)
                    max_hours = float(row.get("max_hours") or 8.0)
                    avail_start = row.get("availability_start") or "09:00"
                    avail_end = row.get("availability_end") or "21:00"

                    # Check profile
                    prof = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE student_id = %s", (v_id,))
                    if not prof:
                        # Create demo logins for the first two volunteers.
                        user_id = None
                        if v_id in ("V001", "V002"):
                            # Seed pre-activated account for demo
                            u_existing = fetch_one(conn, "SELECT id FROM users WHERE LOWER(login_id) = %s", (v_id.lower(),))
                            if not u_existing:
                                demo_password = "volunteer123" if v_id == "V001" else "volunteer124"
                                pwd_hash = generate_password_hash(demo_password)
                                execute_query(conn, """
                                    INSERT INTO users (email, login_id, password_hash, role, status, created_at, updated_at)
                                    VALUES (%s, %s, %s, 'volunteer', 'active', %s, %s)
                                """, (Config.VOLUNTEER_LOGIN_EMAIL, v_id, pwd_hash, ts, ts))
                                u_row = fetch_one(conn, "SELECT id FROM users WHERE LOWER(login_id) = %s", (v_id.lower(),))
                                user_id = u_row['id']
                            else:
                                user_id = u_existing['id']

                        execute_query(conn, """
                            INSERT INTO volunteer_profiles (user_id, student_id, full_name, interviewed_by, email, active_status, created_by, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s)
                        """, (user_id, v_id, name, interviewed_by, email, convener_id, ts, ts))
                        prof_row = fetch_one(conn, "SELECT id FROM volunteer_profiles WHERE student_id = %s", (v_id,))
                        prof_id = prof_row['id']
                        volunteers_seeded += 1
                    else:
                        prof_id = prof['id']

                    execute_query(conn, "UPDATE volunteer_profiles SET interviewed_by = %s WHERE id = %s", (interviewed_by, prof_id))

                    # Map skills
                    raw_skills = row.get("skills", "")
                    for s_item in raw_skills.split(","):
                        s_clean = s_item.strip()
                        # normalize slight variations
                        if s_clean == "Stage & Backstage Management" or s_clean == "Stage/ Backstage Management":
                            s_clean = "Stage & Backstage Management"
                        elif s_clean == "Budgeting & Finance" or s_clean == "Finance & Budgeting":
                            s_clean = "Budgeting & Finance"
                        elif s_clean == "Sponsorship & Fundraising" or s_clean == "Sponsorships":
                            s_clean = "Sponsorship & Fundraising"

                        if s_clean in skill_ids:
                            sk_id = skill_ids[s_clean]
                            has_sk = fetch_one(conn, "SELECT 1 FROM volunteer_skills WHERE volunteer_id = %s AND skill_id = %s", (prof_id, sk_id))
                            if not has_sk:
                                execute_query(conn, "INSERT INTO volunteer_skills (volunteer_id, skill_id, created_at) VALUES (%s, %s, %s)", (prof_id, sk_id, ts))

                    # Preferences
                    pref_raw = row.get("department_preference", "")
                    for rank, p_item in enumerate(pref_raw.split(","), start=1):
                        p_clean = p_item.strip()
                        if p_clean:
                            has_pref = fetch_one(conn, "SELECT 1 FROM volunteer_preferences WHERE volunteer_id = %s AND department_name = %s", (prof_id, p_clean))
                            if not has_pref:
                                execute_query(conn, """
                                    INSERT INTO volunteer_preferences (volunteer_id, department_name, preference_rank, created_at)
                                    VALUES (%s, %s, %s, %s)
                                """, (prof_id, p_clean, rank, ts))

        print(f"Volunteers processed: {volunteers_seeded} new seeded.")
        if not seed_demo_data:
            print("Demo volunteers and the pilot event are disabled (SEED_DEMO_DATA=false).")

        # 5. Seed Pilot Event: Kala Fest
        existing_event = fetch_one(conn, "SELECT id FROM events WHERE name = %s", ("Kala Fest",))
        if seed_demo_data and not existing_event:
            execute_query(conn, """
                INSERT INTO events (name, description, starts_at, ends_at, venue, status, created_by, updated_by, created_at, updated_at, version)
                VALUES (%s, %s, %s, %s, %s, 'upcoming', %s, %s, %s, %s, 1)
            """, (
                "Kala Fest",
                "TAPMI Flagship Annual Cultural Festival featuring music, dance, theatre, and management showcases.",
                "2026-11-14T09:00:00Z",
                "2026-11-15T22:00:00Z",
                "TAPMI Campus Main Auditorium & Open Air Amphitheatre",
                convener_id,
                convener_id,
                ts,
                ts
            ))
            event_row = fetch_one(conn, "SELECT id FROM events WHERE name = %s", ("Kala Fest",))
            event_id = event_row['id']

            # Attach volunteer availability for all seeded volunteers for Kala Fest
            all_vols = fetch_all(conn, "SELECT id FROM volunteer_profiles")
            for v in all_vols:
                execute_query(conn, """
                    INSERT INTO volunteer_availability (volunteer_id, event_id, available, availability_start, availability_end, max_hours, notes)
                    VALUES (%s, %s, 1, '09:00', '21:00', 8.0, 'Available for Kala Fest pilot')
                """, (v['id'], event_id))

            # Seed Event Requirements
            # Following specifications and realistic demands
            reqs = [
                # Critical
                {
                    "dept": "Stage & Backstage Management",
                    "role": "Stage Lead & Technical Stage Crew",
                    "headcount": 4,
                    "priority": "critical",
                    "mandatory": ["Stage & Backstage Management"],
                    "preferred": ["Event Coordination"],
                    "source": "fixed_headcount",
                    "duration": 12.0
                },
                {
                    "dept": "Sponsorship & Fundraising",
                    "role": "Sponsorship Desk & Brand Liaison",
                    "headcount": 3,
                    "priority": "critical",
                    "mandatory": ["Sponsorship & Fundraising"],
                    "preferred": ["Budgeting & Finance"],
                    "source": "fixed_headcount",
                    "duration": 8.0
                },
                # High
                {
                    "dept": "IT & Technical Support",
                    "role": "Audio Visual & Networking Crew",
                    "headcount": 2,
                    "priority": "high",
                    "mandatory": ["Technical Support"],
                    "preferred": ["Networking"],
                    "source": "fixed_headcount",
                    "duration": 10.0
                },
                {
                    "dept": "Logistics & Operations",
                    "role": "Procurement & Equipment Coordinator",
                    "headcount": 4,
                    "priority": "high",
                    "mandatory": ["Logistics"],
                    "preferred": ["Vendor Management"],
                    "source": "workload_calculation",
                    "workload_value": 160.0,
                    "workload_unit": "items/deliveries",
                    "service_time_value": 0.5,
                    "service_time_unit": "hours/item",
                    "peak_window_value": 20.0,
                    "peak_window_unit": "hours",
                    "duration": 8.0
                },
                {
                    "dept": "Participant Coordination",
                    "role": "Artist & Contestant Liaison",
                    "headcount": 3,
                    "priority": "high",
                    "mandatory": ["Participant Coordination"],
                    "preferred": ["Hospitality & Guest Handling"],
                    "source": "fixed_headcount",
                    "duration": 8.0
                },
                # Normal
                {
                    "dept": "Marketing & Promotions",
                    "role": "Media Coverage & Social Broadcast",
                    "headcount": 4,
                    "priority": "normal",
                    "mandatory": ["Marketing & Promotions"],
                    "preferred": ["Social Media & Content Creation"],
                    "source": "fixed_headcount",
                    "duration": 6.0
                },
                {
                    "dept": "Hospitality & Guest Handling",
                    "role": "Guest Relations & Usher",
                    "headcount": 3,
                    "priority": "normal",
                    "mandatory": ["Hospitality & Guest Handling"],
                    "preferred": ["Anchoring & Public Speaking"],
                    "source": "fixed_headcount",
                    "duration": 6.0
                },
                {
                    "dept": "Crowd Management & Security",
                    "role": "Auditorium Access & Safety Marshal",
                    "headcount": 2,
                    "priority": "normal",
                    "mandatory": ["Crowd Management & Security"],
                    "preferred": ["Team Leadership"],
                    "source": "fixed_headcount",
                    "duration": 6.0
                }
            ]

            for r in reqs:
                d_id = dept_ids.get(r["dept"])
                if not d_id:
                    continue
                execute_query(conn, """
                    INSERT INTO event_requirements (
                        event_id, department_id, role_name, headcount, priority,
                        duration_hours, workload_value, workload_unit,
                        service_time_value, service_time_unit, peak_window_value,
                        peak_window_unit, requirement_source, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event_id, d_id, r["role"], r["headcount"], r["priority"],
                    r.get("duration"), r.get("workload_value"), r.get("workload_unit"),
                    r.get("service_time_value"), r.get("service_time_unit"),
                    r.get("peak_window_value"), r.get("peak_window_unit"),
                    r["source"], ts, ts
                ))
                req_row = fetch_one(conn, "SELECT id FROM event_requirements WHERE event_id = %s AND role_name = %s", (event_id, r["role"]))
                req_id = req_row['id']

                for m_sk in r.get("mandatory", []):
                    if m_sk in skill_ids:
                        execute_query(conn, """
                            INSERT INTO requirement_skills (requirement_id, skill_id, is_mandatory, is_preferred)
                            VALUES (%s, %s, 1, 0)
                        """, (req_id, skill_ids[m_sk]))

                for p_sk in r.get("preferred", []):
                    if p_sk in skill_ids and p_sk not in r.get("mandatory", []):
                        execute_query(conn, """
                            INSERT INTO requirement_skills (requirement_id, skill_id, is_mandatory, is_preferred)
                            VALUES (%s, %s, 0, 1)
                        """, (req_id, skill_ids[p_sk]))

            print(f"Kala Fest pilot event seeded with {len(reqs)} department requirements.")
        elif existing_event:
            print("Kala Fest already exists in database.")

if __name__ == "__main__":
    seed_database()
