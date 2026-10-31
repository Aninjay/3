import sys
from backend.app.db.connection import run_migrations, get_db, fetch_all, is_postgres

def main():
    print("Applying migrations...")
    run_migrations()
    with get_db() as conn:
        if is_postgres():
            tables = fetch_all(conn, "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            names = [t['table_name'] for t in tables]
        else:
            tables = fetch_all(conn, "SELECT name FROM sqlite_master WHERE type='table'")
            names = [t['name'] for t in tables]
    print(f"SUCCESS: {len(names)} tables present in database.")
    print("Tables:", sorted(names))

if __name__ == "__main__":
    main()
