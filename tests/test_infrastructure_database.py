from infrastructure.database.settings import DatabaseEngine, DatabaseSettings, PostgresMigrationPlan


def test_database_settings_detects_postgres_urls() -> None:
    settings = DatabaseSettings.from_url("postgresql+asyncpg://user:pass@localhost/platform")

    assert settings.engine == DatabaseEngine.POSTGRES
    assert settings.pool_size == 5


def test_database_settings_defaults_non_postgres_to_sqlite() -> None:
    settings = DatabaseSettings.from_url("sqlite:///data/agentic_platform.db")

    assert settings.engine == DatabaseEngine.SQLITE
    assert settings.pool_size == 1


def test_postgres_migration_plan_lists_enterprise_migration_steps() -> None:
    steps = PostgresMigrationPlan().describe()

    assert len(steps) >= 5
    assert any("DATABASE_URL" in step for step in steps)
