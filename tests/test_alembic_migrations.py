"""Migration tests against a real Postgres.

Every other test in this suite builds its schema from `Base.metadata` on
SQLite, so nothing here can tell you whether a migration produced the schema it
claims to — only the migrations can. These tests run `alembic upgrade` against a
disposable database on the local Supabase Postgres and use the resulting tables.

Opt in with `ALEMBIC_LIVE_CHECK=1`. Skipped when that is unset or when the local
Postgres is unreachable. The disposable database is dropped on the way out, so
nothing the dev stack owns is read or written.
"""

import logging.config
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError

from database import DATABASE_URL

ALEMBIC_INI = "alembic.ini"
DISPOSABLE_DATABASE = "memo_tables_alembic_test"

# The revision that gave `grammar_rules.canonical_rule_id` a UNIQUE constraint.
# Pinning it is what makes the first test a test of the migration rather than a
# snapshot of the current schema.
CONSTRAINT_ADDED_AT = "99012e1bc634"

EXTENSIONS = ("pg_trgm", "vector")


@contextmanager
def _leaving_host_logging_alone():
    """Keep `alembic/env.py` from reconfiguring logging process-wide.

    `env.py` calls `logging.config.fileConfig`, which disables every logger that
    already exists unless told otherwise. That is right for a command-line run
    and wrong for a test suite running Alembic in-process.
    """
    configure = logging.config.fileConfig
    logging.config.fileConfig = partial(configure, disable_existing_loggers=False)
    try:
        yield
    finally:
        logging.config.fileConfig = configure


@dataclass
class CatalogSeed:
    canonical_rule_id: uuid.UUID
    language_id: uuid.UUID
    word_category_id: uuid.UUID


@dataclass
class MigratedPostgres:
    """An empty database that migrations can be run against, then used."""

    engine: Engine
    config: Config

    def upgrade(self, revision: str) -> None:
        with _leaving_host_logging_alone():
            command.upgrade(self.config, revision)

    def insert(self, statement: str, **parameters) -> None:
        with self.engine.begin() as connection:
            connection.execute(text(statement), parameters)

    def seed_catalog_entry(self) -> CatalogSeed:
        """Insert the rows a grammar rule needs, and return their ids."""
        language_id = uuid.uuid4()
        word_category_id = uuid.uuid4()
        canonical_rule_id = uuid.uuid4()
        self.insert(
            "insert into languages (id, code, name) values (:id, 'es', 'Spanish')",
            id=language_id,
        )
        self.insert(
            "insert into word_categories (id, name, slug)"
            " values (:id, 'Migration Test', 'migration-test-category')",
            id=word_category_id,
        )
        self.insert(
            "insert into canonical_rules (id, native_language_id, target_language_id,"
            " word_category_id, level, name, description, position, slug, is_active)"
            " values (:id, :language_id, :language_id, :word_category_id, 'B1',"
            " 'Ser vs. estar', 'd', 1, 'ser-vs-estar', true)",
            id=canonical_rule_id,
            language_id=language_id,
            word_category_id=word_category_id,
        )
        return CatalogSeed(canonical_rule_id, language_id, word_category_id)

    def insert_rule(self, name: str, catalog: CatalogSeed) -> None:
        self.insert(
            "insert into grammar_rules (id, name, description, language_id,"
            " word_category_id, canonical_rule_id) values (:id, :name, 'd',"
            " :language_id, :word_category_id, :canonical_rule_id)",
            id=uuid.uuid4(),
            name=name,
            language_id=catalog.language_id,
            word_category_id=catalog.word_category_id,
            canonical_rule_id=catalog.canonical_rule_id,
        )

    def rule_names_for(self, canonical_rule_id: uuid.UUID) -> list[str]:
        with self.engine.connect() as connection:
            return list(
                connection.execute(
                    text(
                        "select name from grammar_rules"
                        " where canonical_rule_id = :id order by name"
                    ),
                    {"id": canonical_rule_id},
                ).scalars()
            )


def _drop_database(admin_engine: Engine, name: str) -> None:
    with admin_engine.connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as connection:
        connection.execute(
            text(
                "select pg_terminate_backend(pid) from pg_stat_activity"
                " where datname = :name and pid <> pg_backend_pid()"
            ),
            {"name": name},
        )
        connection.execute(text(f'drop database if exists "{name}"'))


@pytest.fixture()
def migrated_postgres():
    """An empty database on the local Postgres, with no migrations applied yet."""
    if os.environ.get("ALEMBIC_LIVE_CHECK") != "1":
        pytest.skip("set ALEMBIC_LIVE_CHECK=1 to run migrations against local Postgres")

    admin_url = make_url(DATABASE_URL)
    admin_engine = create_engine(admin_url)
    try:
        with admin_engine.connect() as connection:
            connection.execute(text("select 1"))
    except Exception as error:
        pytest.skip(f"local Postgres is unavailable: {error}")

    database_url = admin_url.set(database=DISPOSABLE_DATABASE)
    _drop_database(admin_engine, DISPOSABLE_DATABASE)
    with admin_engine.connect().execution_options(
        isolation_level="AUTOCOMMIT"
    ) as connection:
        connection.execute(text(f'create database "{DISPOSABLE_DATABASE}"'))

    engine = create_engine(database_url)
    # The migrations assume the extensions the Supabase stack enables, including
    # `pg_trgm`, which the trigram index on rule names needs.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for extension in EXTENSIONS:
            connection.execute(text(f"create extension if not exists {extension}"))

    # `alembic/env.py` reads the URL from the environment rather than the ini.
    previous_url = os.environ["DATABASE_URL_LOCAL"]
    os.environ["DATABASE_URL_LOCAL"] = database_url.render_as_string(
        hide_password=False
    )
    try:
        yield MigratedPostgres(engine=engine, config=Config(ALEMBIC_INI))
    finally:
        os.environ["DATABASE_URL_LOCAL"] = previous_url
        engine.dispose()
        _drop_database(admin_engine, DISPOSABLE_DATABASE)
        admin_engine.dispose()


class TestCanonicalRuleIdIsNotUnique:
    def test_a_second_rule_sharing_a_catalog_entry_is_rejected_before_the_drop(
        self, migrated_postgres
    ):
        migrated_postgres.upgrade(CONSTRAINT_ADDED_AT)
        catalog = migrated_postgres.seed_catalog_entry()

        migrated_postgres.insert_rule("Ser vs. estar", catalog)

        with pytest.raises(IntegrityError):
            migrated_postgres.insert_rule("Ser frente a estar", catalog)

    def test_two_rules_can_share_a_catalog_entry(self, migrated_postgres):
        migrated_postgres.upgrade("head")
        catalog = migrated_postgres.seed_catalog_entry()

        migrated_postgres.insert_rule("Ser vs. estar", catalog)
        migrated_postgres.insert_rule("Ser frente a estar", catalog)

        assert migrated_postgres.rule_names_for(catalog.canonical_rule_id) == [
            "Ser frente a estar",
            "Ser vs. estar",
        ]
