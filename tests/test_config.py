import json
import pytest

from config import Config, ConfigError, load_config


def test_loads_key_and_model_from_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_key": "file-key", "model": "m-file"}), encoding="utf-8")
    cfg = load_config(p)
    assert cfg == Config(api_key="file-key", model="m-file")


def test_file_key_wins_over_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_key": "file-key"}), encoding="utf-8")
    assert load_config(p).api_key == "file-key"


def test_env_key_used_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    cfg = load_config(tmp_path / "nope.json")
    assert cfg.api_key == "env-key"
    assert cfg.model == "gemini-3.5-flash"


def test_default_model_when_file_has_only_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_key": "k"}), encoding="utf-8")
    assert load_config(p).model == "gemini-3.5-flash"


def test_error_when_no_key_anywhere(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.json")


def test_error_when_file_is_not_json(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_loads_key_with_utf8_bom(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"api_key": "k"}).encode())
    assert load_config(p).api_key == "k"


def test_error_when_env_key_is_whitespace(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.json")


def test_strips_whitespace_from_file_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"api_key": " k \n"}), encoding="utf-8")
    assert load_config(p).api_key == "k"


def test_error_when_file_is_json_array(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = tmp_path / "config.json"
    p.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)
