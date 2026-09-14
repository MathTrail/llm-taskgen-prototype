"""Recreate the database schema from db/schema.sql (T07): drops everything in the public schema, safe to rerun.

DATABASE_URL comes from the environment or from .env in the project root.
If any table already holds rows, the script stops unless --force is given, so a paid task bank is not lost by accident.
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "db" / "schema.sql"


def database_url() -> str:
    """DATABASE_URL from the environment, otherwise from the .env file."""
    if url := os.environ.get("DATABASE_URL"):
        return url
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "DATABASE_URL" and value.strip():
                return value.strip().strip("\"'")
    sys.exit("DATABASE_URL is not set: copy .env.example to .env")


def nonempty_tables(conn: psycopg.Connection) -> dict[str, int]:
    """Row counts of the tables in the public schema that are not empty."""
    tables = conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    ).fetchall()
    counts = {}
    for (table,) in tables:
        query = sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
        count = conn.execute(query).fetchone()[0]
        if count:
            counts[table] = count
    return counts


def apply_schema(url: str, force: bool = False) -> None:
    """Drop the public schema and run schema.sql, all in one transaction."""
    with psycopg.connect(url) as conn:
        filled = nonempty_tables(conn)
        if filled and not force:
            summary = ", ".join(f"{table}: {count}" for table, count in filled.items())
            sys.exit(f"Tables hold data ({summary}). Rerun with --force to drop it.")

        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute(SCHEMA.read_text(encoding="utf-8"))

        counts = dict(
            conn.execute(
                "SELECT table_type, count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' GROUP BY table_type"
            ).fetchall()
        )
        info = conn.info
        print(
            f"Schema applied to {info.dbname} at {info.host}:{info.port}: "
            f"{counts.get('BASE TABLE', 0)} tables, {counts.get('VIEW', 0)} views"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Recreate the database schema from db/schema.sql.")
    parser.add_argument("--force", action="store_true", help="recreate even if tables hold data; the data is lost")
    args = parser.parse_args()
    apply_schema(database_url(), force=args.force)


if __name__ == "__main__":
    main()
