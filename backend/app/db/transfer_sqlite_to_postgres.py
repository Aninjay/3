"""Safely copy an existing SQLite database into an empty migrated PostgreSQL DB.

Run without --apply first. The source is opened read-only and the target must
contain no application rows before a copy is attempted.
"""

import argparse
import sqlite3
from pathlib import Path

from backend.app.db.connection import (
    execute_query,
    fetch_all,
    fetch_one,
    is_postgres,
    transaction,
)


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def source_tables(source):
    return [
        row[0]
        for row in source.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]


def dependency_order(source, tables):
    """Return a parent-before-child order based on the SQLite foreign keys."""
    table_set = set(tables)
    dependencies = {}
    for table in tables:
        dependencies[table] = {
            row[2]
            for row in source.execute(f"PRAGMA foreign_key_list({quote_identifier(table)})")
            if row[2] in table_set and row[2] != table
        }

    ordered = []
    while dependencies:
        ready = sorted(table for table, parents in dependencies.items() if parents.issubset(ordered))
        if not ready:
            raise RuntimeError(
                "The source schema contains circular table dependencies that this safe importer cannot order."
            )
        ordered.extend(ready)
        for table in ready:
            del dependencies[table]
    return ordered


def transfer(source_path: Path, apply: bool = False) -> dict:
    if not is_postgres():
        raise RuntimeError("DATABASE_URL must point to the PostgreSQL destination database.")
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite source database not found: {source_path}")

    source = sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        fk_errors = source.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"SQLite source has {len(fk_errors)} foreign-key integrity issue(s).")

        tables = dependency_order(source, source_tables(source))
        counts = {
            table: source.execute(f"SELECT COUNT(*) FROM {quote_identifier(table)}").fetchone()[0]
            for table in tables
        }

        with transaction() as target:
            pg_tables = {
                row["table_name"]
                for row in fetch_all(
                    target,
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'",
                )
            }
            missing = sorted(set(tables) - pg_tables)
            if missing:
                raise RuntimeError(
                    "Destination schema is missing tables. Run the project migrations first: "
                    + ", ".join(missing)
                )

            occupied = []
            for table in tables:
                row = fetch_one(target, f"SELECT COUNT(*) AS n FROM {quote_identifier(table)}")
                if row["n"]:
                    occupied.append(table)
            if occupied:
                raise RuntimeError(
                    "Destination is not empty; refusing to merge or overwrite records in: "
                    + ", ".join(occupied)
                )

            if not apply:
                return {"mode": "dry-run", "tables": counts, "total": sum(counts.values())}

            inserted = {}
            for table in tables:
                source_columns = [row["name"] for row in source.execute(
                    f"PRAGMA table_info({quote_identifier(table)})"
                )]
                target_columns = {
                    row["column_name"]
                    for row in fetch_all(
                        target,
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = current_schema() AND table_name = %s",
                        (table,),
                    )
                }
                columns = [column for column in source_columns if column in target_columns]
                if counts[table] and not columns:
                    raise RuntimeError(f"No matching columns found for populated table {table}.")
                if not columns:
                    inserted[table] = 0
                    continue

                names_sql = ", ".join(quote_identifier(column) for column in columns)
                placeholders = ", ".join("%s" for _ in columns)
                sql = f"INSERT INTO {quote_identifier(table)} ({names_sql}) VALUES ({placeholders})"
                rows = source.execute(
                    f"SELECT {names_sql} FROM {quote_identifier(table)} ORDER BY rowid"
                )
                count = 0
                for row in rows:
                    execute_query(target, sql, tuple(row[column] for column in columns))
                    count += 1
                inserted[table] = count

            # Explicit IDs are retained; advance PostgreSQL SERIAL sequences so
            # newly created records continue after the imported records.
            for table in tables:
                if "id" not in {
                    row["column_name"]
                    for row in fetch_all(
                        target,
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = current_schema() AND table_name = %s",
                        (table,),
                    )
                }:
                    continue
                sequence = fetch_one(
                    target,
                    "SELECT pg_get_serial_sequence(%s, 'id') AS sequence_name",
                    (table,),
                )["sequence_name"]
                if sequence:
                    max_id = fetch_one(
                        target,
                        f"SELECT MAX(id) AS max_id FROM {quote_identifier(table)}",
                    )["max_id"]
                    if max_id is not None:
                        execute_query(target, "SELECT setval(%s::regclass, %s, true)", (sequence, max_id))

            return {"mode": "applied", "tables": inserted, "total": sum(inserted.values())}
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to the SQLite database to copy (opened read-only).")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy records. Without this flag, only validate and report source row counts.",
    )
    args = parser.parse_args()
    result = transfer(args.source, apply=args.apply)
    print(f"SQLite to PostgreSQL {result['mode']} passed: {result['total']} record(s).")
    for table, count in sorted(result["tables"].items()):
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
