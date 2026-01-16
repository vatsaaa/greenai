import sys
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
)
import importlib
from sqlalchemy.orm import sessionmaker
import re


# Ensure project root is on sys.path so tests can import local modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load .env and ensure test DB URLs are present for test runtime.
load_dotenv()

# Provide a lightweight sqlite DB URL for tests that need DB access.
os.environ.setdefault("DB_URL", "sqlite:///./test-db.sqlite3")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test-db.sqlite3")


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create minimal tables needed for integration-style tests and tear down after.

    Uses the `DB_URL` environment variable (defaults to sqlite:///./test-db.sqlite3).
    """
    db_url = os.environ.get("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL must be set for tests")

    engine = create_engine(db_url)

    # Try to apply full SQL schema from database/schema/*.sql. If the SQL
    # contains Postgres-specific syntax incompatible with sqlite, fall
    # back to a minimal, programmatic schema so tests can still run.
    schema_dir = ROOT / "database" / "schema"
    applied_full_sql = False
    schemas_created = set()
    if schema_dir.exists():
        sql_files = sorted(schema_dir.glob("*.sql"))
        if sql_files:
            dialect = engine.dialect.name
            try:
                if dialect and dialect.startswith("postgres"):
                    # For Postgres, execute SQL files directly via connection.
                    with engine.connect() as conn:
                        # Some DDL may require autocommit-like behavior
                        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                        for f in sql_files:
                            sql = f.read_text()
                            conn.exec_driver_sql(sql)
                            # detect CREATE SCHEMA statements to help teardown
                            for m in re.finditer(
                                r"CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
                                sql,
                                re.IGNORECASE,
                            ):
                                schemas_created.add(m.group(1))
                            # detect explicit SET search_path statements
                            for m in re.finditer(
                                r"SET\s+search_path\s*=\s*([^;\n]+)", sql, re.IGNORECASE
                            ):
                                parts = m.group(1).split(",")
                                for p in parts:
                                    schemas_created.add(p.strip().strip('"'))
                    applied_full_sql = True
                else:
                    # Fallback path (likely sqlite): use raw.executescript
                    raw = engine.raw_connection()
                    try:
                        for f in sql_files:
                            sql = f.read_text()
                            raw.executescript(sql)
                        raw.commit()
                        applied_full_sql = True
                    finally:
                        raw.close()
            except Exception:
                # Applying full SQL failed (likely due to incompatible SQL dialect).
                # We'll fall back to minimal programmatic schema below.
                applied_full_sql = False

    if not applied_full_sql:
        metadata = MetaData()

        # Minimal table definitions matching production intent (lightweight)
        Table(
            "reason_codes",
            metadata,
            Column("reason_id", Integer, primary_key=True),
            Column("code", String(64), nullable=False, unique=True),
            Column("description", Text),
            Column("is_functional", Integer, default=0),
        )

        Table(
            "recon_runs",
            metadata,
            Column("run_id", Integer, primary_key=True),
            Column("status", String(32)),
            Column("end_time", DateTime),
            Column("total_differences", Integer, default=0),
        )

        Table(
            "recon_records",
            metadata,
            Column("record_id", Integer, primary_key=True),
            Column("run_id", Integer),
            Column("source_a_ref_id", String(128)),
            Column("source_b_ref_id", String(128)),
            Column("normalized_data_a", Text),
            Column("normalized_data_b", Text),
        )

        Table(
            "data_differences",
            metadata,
            Column("diff_id", String(36), primary_key=True),
            Column("record_id", Integer),
            Column("field_name", String(128)),
            Column("value_a", Text),
            Column("value_b", Text),
            Column("diff_type", String(64)),
            Column("severity", String(16)),
        )

        Table(
            "attributions",
            metadata,
            Column("attribution_id", Integer, primary_key=True),
            Column("diff_id", String(36)),
            Column("confidence_score", Float),
            Column("status", String(32)),
            Column("reason_id", Integer),
        )

        Table(
            "audit_trail",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("attribution_id", Integer),
            Column("actor_id", String(64)),
            Column("action_type", String(64)),
            Column("comments", Text),
        )

        # Create tables programmatically
        metadata.create_all(engine)

    yield

    # Teardown: if we applied full SQL on Postgres, drop schemas we created.
    try:
        if (
            applied_full_sql
            and engine.dialect.name.startswith("postgres")
            and schemas_created
        ):
            with engine.connect() as conn:
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                for schema in schemas_created:
                    try:
                        conn.exec_driver_sql(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
                    except Exception:
                        # best-effort per-schema drop
                        pass
        else:
            metadata = MetaData()
            metadata.reflect(bind=engine)
            metadata.drop_all(bind=engine)
    except Exception:
        # best-effort teardown
        pass


@pytest.fixture(scope="function", autouse=True)
def transactional_db():
    """Per-test transactional fixture.

    Starts a DB transaction and monkeypatches backend modules' `Session`
    to use the transactional connection so tests are isolated and rolled
    back after each test.
    """
    db_url = os.environ.get("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL must be set for transactional fixture")

    engine = create_engine(db_url)
    connection = engine.connect()
    transaction = connection.begin()

    SessionFactory = sessionmaker(bind=connection)
    session = SessionFactory()

    # Patch module-level Session objects so code under test uses our connection
    patched = {}
    modules_to_patch = ("backend.attribution_engine", "backend.diff_engine")
    for name in modules_to_patch:
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, "Session"):
                patched[name] = getattr(mod, "Session")
                setattr(mod, "Session", SessionFactory)
        except Exception:
            # ignore modules that aren't importable in some test contexts
            continue

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        # restore original Session objects
        for name, orig in patched.items():
            try:
                mod = importlib.import_module(name)
                setattr(mod, "Session", orig)
            except Exception:
                pass
