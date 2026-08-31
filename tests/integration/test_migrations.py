from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.mark.integration
def test_alembic_upgrade_and_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITDOCK_DATABASE_URL", raising=False)
    db_path = tmp_path / "migration.db"
    async_url = f"sqlite+aiosqlite:///{db_path}"
    sync_url = f"sqlite:///{db_path}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", async_url)
    command.upgrade(config, "head")

    engine = create_engine(sync_url)
    tables = set(inspect(engine).get_table_names())
    assert {"users", "telegram_accounts", "github_accounts", "github_installations"} <= tables
    engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(sync_url)
    tables_after = set(inspect(engine).get_table_names())
    assert "users" not in tables_after
    engine.dispose()
