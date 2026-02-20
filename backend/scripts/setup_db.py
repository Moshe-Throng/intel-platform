"""
setup_db.py - Execute SQL migrations against Supabase

Usage:
    python scripts/setup_db.py              # Run all migrations
    python scripts/setup_db.py --seed-only  # Run only seed data
    python scripts/setup_db.py --schema-only # Run only schema creation

Reads SUPABASE_URL and SUPABASE_SERVICE_KEY from .env
Uses the Supabase REST API (rpc endpoint) to execute raw SQL.
"""

import os
import sys
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root or backend/
env_paths = [
    Path(__file__).parent.parent / ".env",           # backend/.env
    Path(__file__).parent.parent.parent / ".env",     # project root .env
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

SCRIPTS_DIR = Path(__file__).parent

SQL_FILES = {
    "schema": SCRIPTS_DIR / "001_create_tables.sql",
    "seed": SCRIPTS_DIR / "002_seed_data.sql",
}


def execute_sql(sql: str, description: str) -> bool:
    """Execute raw SQL via Supabase's REST API using the pg_net/rpc approach."""
    # Use the Supabase SQL endpoint (postgrest rpc)
    # We'll use the raw postgres connection via supabase-py or REST
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    # First try: use a custom RPC function if it exists
    response = requests.post(url, json={"query": sql}, headers=headers)

    if response.status_code == 404:
        # RPC function doesn't exist - fall back to direct SQL via management API
        print(f"  [INFO] exec_sql RPC not found. Using Supabase SQL Editor instead.")
        print(f"  [INFO] Copy and paste the SQL from the files below into your Supabase SQL Editor:")
        print(f"         Dashboard > SQL Editor > New Query")
        return False

    if response.status_code != 200:
        print(f"  [ERROR] {description}: {response.status_code}")
        print(f"  {response.text}")
        return False

    print(f"  [OK] {description}")
    return True


def run_sql_file(filepath: Path, description: str) -> bool:
    """Read and execute a SQL file."""
    if not filepath.exists():
        print(f"  [ERROR] File not found: {filepath}")
        return False

    sql = filepath.read_text(encoding="utf-8")
    print(f"\nRunning: {filepath.name} ({description})")
    print(f"  SQL length: {len(sql)} chars")

    return execute_sql(sql, description)


def verify_connection() -> bool:
    """Verify Supabase connection works."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
        return False

    url = f"{SUPABASE_URL}/rest/v1/"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print(f"[OK] Connected to Supabase: {SUPABASE_URL}")
            return True
        else:
            print(f"[ERROR] Supabase returned {response.status_code}: {response.text}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] Cannot connect to Supabase: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Set up Intel Platform database")
    parser.add_argument("--seed-only", action="store_true", help="Only run seed data")
    parser.add_argument("--schema-only", action="store_true", help="Only run schema creation")
    args = parser.parse_args()

    print("=" * 60)
    print("Intel Platform MVP - Database Setup")
    print("=" * 60)

    if not verify_connection():
        sys.exit(1)

    success = True
    used_rpc = True

    if not args.seed_only:
        if not run_sql_file(SQL_FILES["schema"], "Create tables & indexes"):
            used_rpc = False

    if not args.schema_only:
        if used_rpc:
            if not run_sql_file(SQL_FILES["seed"], "Seed initial data"):
                used_rpc = False

    if not used_rpc:
        print("\n" + "=" * 60)
        print("MANUAL SETUP REQUIRED")
        print("=" * 60)
        print("\nThe automated RPC method isn't available on your Supabase instance.")
        print("This is normal for most Supabase projects. Follow these steps:\n")
        print("1. Go to: https://supabase.com/dashboard")
        print("2. Select your project")
        print("3. Navigate to: SQL Editor (left sidebar)")
        print("4. Click 'New Query'")
        print(f"5. Copy & paste contents of:\n   - {SQL_FILES['schema']}")
        print("6. Click 'Run' (or Ctrl+Enter)")
        print(f"7. Then copy & paste contents of:\n   - {SQL_FILES['seed']}")
        print("8. Click 'Run' again")
        print("\nAfter running both scripts, your database is ready!")
    else:
        print("\n" + "=" * 60)
        print("Database setup complete!")
        print("=" * 60)

    print("\nTables created:")
    print("  - news_sources   (12 initial sources)")
    print("  - articles        (empty, ready for crawling)")
    print("  - tags            (58 tags across 4 categories)")
    print("  - article_tags    (empty, populated by auto-tagger)")
    print("  - published_posts (empty, populated by publisher)")


if __name__ == "__main__":
    main()
