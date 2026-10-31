CREATE TABLE IF NOT EXISTS core_committee_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS department_heads (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    assigned_by INTEGER REFERENCES users(id),
    assigned_at TEXT NOT NULL,
    PRIMARY KEY (event_id, department_id)
);

CREATE INDEX IF NOT EXISTS idx_department_heads_user_event
    ON department_heads(user_id, event_id);
