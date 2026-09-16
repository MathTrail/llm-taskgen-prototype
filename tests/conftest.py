"""Fixtures for tests on a real PostgreSQL (T12).

The tests use a separate database, taskgen_test, on the server from DATABASE_URL: the fixture creates it if needed
and recreates its schema from db/schema.sql once per run. Every test works in its own transaction that is rolled
back, so tests do not see each other's rows. Without a reachable server the tests are skipped.
"""

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from taskgen.apply_schema import apply_schema
from taskgen.db import database_url

TEST_DB = "taskgen_test"


@pytest.fixture(scope="session")
def test_url():
    try:
        main_url = database_url()
    except SystemExit:
        pytest.skip("DATABASE_URL is not set")
    assert conninfo_to_dict(main_url).get("dbname") != TEST_DB, "DATABASE_URL must point to the working database"
    url = make_conninfo(main_url, dbname=TEST_DB)
    try:
        with psycopg.connect(main_url, autocommit=True, connect_timeout=3) as admin:
            if not admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,)).fetchone():
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB)))
    except psycopg.OperationalError as error:
        pytest.skip(f"PostgreSQL is not reachable: {error}")
    apply_schema(url, force=True)
    return url


@pytest.fixture
def conn(test_url):
    with psycopg.connect(test_url) as connection:
        yield connection
        connection.rollback()
