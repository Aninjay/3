-- 001_initial_schema.sql
-- Cultural Committee Volunteer Management and Event Resource Allocation System
-- Conforms to DATABASE_SCHEMA.md

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    role TEXT NOT NULL CHECK (role IN ('convener', 'co_convener', 'volunteer', 'core_committee')),
    status TEXT NOT NULL DEFAULT 'pending_activation' CHECK (status IN ('pending_activation', 'active', 'locked', 'inactive')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS volunteer_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id),
    student_id TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    interviewed_by TEXT,
    email TEXT NOT NULL UNIQUE,
    active_status BOOLEAN NOT NULL DEFAULT 1,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'approved' CHECK (status IN ('pending', 'approved', 'rejected', 'retired')),
    created_by INTEGER REFERENCES users(id),
    approved_by INTEGER REFERENCES users(id),
    approved_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS volunteer_skills (
    volunteer_id INTEGER NOT NULL REFERENCES volunteer_profiles(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (volunteer_id, skill_id)
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS volunteer_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL REFERENCES volunteer_profiles(id) ON DELETE CASCADE,
    department_name TEXT NOT NULL,
    preference_rank INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE (volunteer_id, department_name)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    venue TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'upcoming' CHECK (status IN ('draft', 'upcoming', 'ongoing', 'completed', 'cancelled', 'archived')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS volunteer_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_id INTEGER NOT NULL REFERENCES volunteer_profiles(id) ON DELETE CASCADE,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    available BOOLEAN NOT NULL DEFAULT 1,
    availability_start TEXT,
    availability_end TEXT,
    max_hours NUMERIC NOT NULL DEFAULT 8.0,
    notes TEXT,
    UNIQUE (volunteer_id, event_id)
);

CREATE TABLE IF NOT EXISTS event_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    role_name TEXT NOT NULL,
    headcount INTEGER NOT NULL CHECK (headcount >= 0),
    priority TEXT NOT NULL CHECK (priority IN ('critical', 'high', 'normal')),
    duration_hours NUMERIC CHECK (duration_hours IS NULL OR duration_hours >= 0),
    workload_value NUMERIC CHECK (workload_value IS NULL OR workload_value >= 0),
    workload_unit TEXT,
    service_time_value NUMERIC,
    service_time_unit TEXT,
    peak_window_value NUMERIC,
    peak_window_unit TEXT,
    requirement_source TEXT NOT NULL CHECK (requirement_source IN ('fixed_headcount', 'workload_calculation')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requirement_skills (
    requirement_id INTEGER NOT NULL REFERENCES event_requirements(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    is_mandatory BOOLEAN NOT NULL DEFAULT 1,
    is_preferred BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (requirement_id, skill_id)
);

CREATE TABLE IF NOT EXISTS allocation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    algorithm TEXT NOT NULL,
    input_snapshot TEXT NOT NULL,
    input_fingerprint TEXT,
    solver_status TEXT,
    metrics TEXT,
    result_summary TEXT,
    run_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    is_simulation BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS allocation_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    parent_version_id INTEGER REFERENCES allocation_versions(id),
    source_run_id INTEGER REFERENCES allocation_runs(id),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'published', 'superseded', 'rejected')),
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    change_summary TEXT,
    row_version INTEGER NOT NULL DEFAULT 1,
    UNIQUE (event_id, version_number)
);

CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    allocation_version_id INTEGER NOT NULL REFERENCES allocation_versions(id) ON DELETE CASCADE,
    requirement_id INTEGER NOT NULL REFERENCES event_requirements(id),
    volunteer_id INTEGER NOT NULL REFERENCES volunteer_profiles(id),
    assigned_by INTEGER REFERENCES users(id),
    assignment_source TEXT NOT NULL CHECK (assignment_source IN ('greedy', 'ilp', 'manual', 'imported')),
    skill_override BOOLEAN NOT NULL DEFAULT 0,
    override_reason TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (allocation_version_id, volunteer_id)
);

CREATE TABLE IF NOT EXISTS allocation_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    allocation_version_id INTEGER NOT NULL REFERENCES allocation_versions(id) ON DELETE CASCADE,
    approved_by INTEGER NOT NULL REFERENCES users(id),
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    comment TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS published_allocations (
    event_id INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
    allocation_version_id INTEGER NOT NULL UNIQUE REFERENCES allocation_versions(id),
    published_by INTEGER NOT NULL REFERENCES users(id),
    published_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    before_data TEXT,
    after_data TEXT,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS otp_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    volunteer_profile_id INTEGER REFERENCES volunteer_profiles(id),
    purpose TEXT NOT NULL CHECK (purpose IN ('activation', 'recovery')),
    otp_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    consumed_at TEXT,
    created_at TEXT NOT NULL
);

-- Essential Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_volunteers_student_id ON volunteer_profiles(student_id);
CREATE INDEX IF NOT EXISTS idx_volunteers_email ON volunteer_profiles(email);
CREATE INDEX IF NOT EXISTS idx_events_status_starts ON events(status, starts_at);
CREATE INDEX IF NOT EXISTS idx_requirements_event ON event_requirements(event_id);
CREATE INDEX IF NOT EXISTS idx_assignments_version_vol ON assignments(allocation_version_id, volunteer_id);
CREATE INDEX IF NOT EXISTS idx_alloc_versions_event ON allocation_versions(event_id, version_number);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id, created_at);
