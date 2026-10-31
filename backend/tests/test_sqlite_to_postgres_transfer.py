import sqlite3

from backend.app.db.transfer_sqlite_to_postgres import dependency_order, quote_identifier, source_tables


def test_dependency_order_places_parent_tables_first():
    source = sqlite3.connect(":memory:")
    source.execute("PRAGMA foreign_keys = ON")
    source.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        CREATE TABLE events (id INTEGER PRIMARY KEY, created_by INTEGER REFERENCES users(id));
        CREATE TABLE assignments (
            id INTEGER PRIMARY KEY,
            event_id INTEGER REFERENCES events(id),
            assigned_by INTEGER REFERENCES users(id)
        );
    """)

    ordered = dependency_order(source, source_tables(source))

    assert ordered.index("users") < ordered.index("events")
    assert ordered.index("events") < ordered.index("assignments")
    assert ordered.index("users") < ordered.index("assignments")


def test_identifier_quoting_escapes_embedded_quotes():
    assert quote_identifier('table"name') == '"table""name"'
