CREATE UNIQUE INDEX IF NOT EXISTS idx_department_heads_unique_member_per_event
    ON department_heads(event_id, user_id);
