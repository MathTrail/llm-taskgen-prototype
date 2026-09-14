"""Recreate the database schema from db/schema.sql (T07): drops everything in the public schema, safe to rerun.

Run: uv run python -m taskgen.apply_schema [--force]
DATABASE_URL comes from the environment or from .env in the repository root.
If any table already holds rows, the script stops unless --force is given, so a paid task bank is not lost by accident.
"""

import argparse
import sys

import psycopg
from psycopg import sql

from taskgen import ROOT
from taskgen.db import database_url

SCHEMA = ROOT / "db" / "schema.sql"


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
