"""Tests for JSON I/O helpers in modules/json_io.py."""

from __future__ import annotations

import json

import pytest

from modules.json_io import JsonIOError, read_json_file, write_json_file


def test_read_json_file_roundtrip(tmp_path):
    target = tmp_path / "data.json"
    payload = {"ok": True, "items": [1, 2, 3]}
    write_json_file(target, payload)
    assert read_json_file(target) == payload


def test_read_json_file_returns_default_when_missing(tmp_path):
    assert read_json_file(tmp_path / "missing.json", default={}) == {}


def test_read_json_file_returns_default_when_invalid_json(tmp_path):
    target = tmp_path / "bad.json"
    target.write_text("{invalid json", encoding="utf-8")
    assert read_json_file(target, default=[]) == []


def test_write_json_file_creates_parent_directories(tmp_path):
    target = tmp_path / "nested" / "dir" / "data.json"
    write_json_file(target, {"ok": True})
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}


def test_write_json_file_raises_on_permission_error(monkeypatch, tmp_path):
    target = tmp_path / "data.json"

    def fake_write_text(*args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(type(target), "write_text", fake_write_text)
    with pytest.raises(JsonIOError):
        write_json_file(target, {})
