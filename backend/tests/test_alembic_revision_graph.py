from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_history_has_one_upgrade_head():
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config()
    config.set_main_option("script_location", str(backend_dir / "alembic"))

    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["b8d4e2a19f63"]
