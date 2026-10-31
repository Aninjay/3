import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app import create_app
from backend.app.db.migrate import main as run_migrations
from backend.app.db.seed import seed_database

app = create_app()

if __name__ == "__main__":
    # Ensure database migrations and pilot data are present
    run_migrations()
    seed_database()

    # Docker sets PORT=5000 explicitly. Locally use a dedicated port to avoid
    # accidentally proxying requests to an unrelated service already on 5000.
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting Cultural Committee Allocation API on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
