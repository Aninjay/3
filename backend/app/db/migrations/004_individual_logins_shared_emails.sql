-- PostgreSQL version of migration 004. SQLite applies the equivalent table
-- rebuild in connection.py so its legacy UNIQUE constraints can be removed.
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE volunteer_profiles DROP CONSTRAINT IF EXISTS volunteer_profiles_email_key;
ALTER TABLE users ADD COLUMN IF NOT EXISTS login_id TEXT;
ALTER TABLE core_committee_profiles ADD COLUMN IF NOT EXISTS email TEXT;

UPDATE users u
SET login_id = COALESCE(
    (SELECT vp.student_id FROM volunteer_profiles vp WHERE vp.user_id = u.id),
    CASE WHEN u.role = 'core_committee' THEN 'core-' || u.id::TEXT ELSE u.email END
)
WHERE login_id IS NULL;

UPDATE core_committee_profiles ccp
SET email = u.email
FROM users u
WHERE u.id = ccp.user_id AND ccp.email IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_login_id_lower ON users(LOWER(login_id));
CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(LOWER(email));
