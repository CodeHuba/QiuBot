import importlib.util
import os
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "plugins" / "bazaar_plugin" / "card_data_paths.py"


def load_paths_module():
    spec = importlib.util.spec_from_file_location("card_data_paths_under_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gamedata_path_prefers_explicit_environment(monkeypatch, tmp_path):
    module = load_paths_module()
    explicit = tmp_path / "explicit.db"
    fallback = tmp_path / "cache" / "GameData.db"
    monkeypatch.setenv("GAMEDATA_DB", str(explicit))

    assert module.get_gamedata_db_path(fallback) == explicit


def test_gamedata_path_uses_cache_file_when_environment_is_unset(monkeypatch, tmp_path):
    module = load_paths_module()
    monkeypatch.delenv("GAMEDATA_DB", raising=False)
    fallback = tmp_path / "cache" / "GameData.db"

    assert module.get_gamedata_db_path(fallback) == fallback


def test_gamedata_path_reports_missing_when_no_candidate_exists(monkeypatch, tmp_path):
    module = load_paths_module()
    monkeypatch.delenv("GAMEDATA_DB", raising=False)
    fallback = tmp_path / "cache" / "GameData.db"

    assert module.get_gamedata_db_path(fallback, require_exists=True) is None
