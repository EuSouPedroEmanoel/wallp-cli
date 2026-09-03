from datetime import datetime, timedelta

from wallpha import config, state, transitions
from wallpha import daemon_list, daemon_schedule


def _state_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state, "LAST_FILE", tmp_path / "last")
    monkeypatch.setattr(state, "OVERRIDE_FILE", tmp_path / "override")


def _entries():
    return config.load_entries([
        {"nome": "a", "local": "/tmp/a.mp4", "tempo": "1h"},
        {"nome": "b", "local": "/tmp/b.mp4", "tempo": "1h"},
        {"nome": "d", "local": "/tmp/d.mp4", "default": True},
    ])


def test_daemon_remember_persists_applied_entry(tmp_path, monkeypatch):
    _state_tmp(tmp_path, monkeypatch)
    active = _entries()[1]
    daemon_schedule._remember(active)
    assert state.get_last() == ["/tmp/b.mp4", "b", "/tmp/b.mp4"]


def test_list_daemon_remember_persists_applied_entry(tmp_path, monkeypatch):
    _state_tmp(tmp_path, monkeypatch)
    active = _entries()[0]
    daemon_list._remember(active)
    assert state.get_last() == ["/tmp/a.mp4", "a", "/tmp/a.mp4"]


def test_override_is_resolved_until_next_transition(tmp_path, monkeypatch):
    _state_tmp(tmp_path, monkeypatch)
    entries = _entries()
    now = datetime(2026, 8, 18, 9, 0)
    key = transitions.last_key(entries[1])
    state.set_override({"key": key, "until": (now + timedelta(minutes=10)).isoformat()})
    active, until = daemon_schedule._override_active(entries, now)
    assert active["nome"] == "b"
    assert until == now + timedelta(minutes=10)


def test_expired_or_invalid_override_is_removed(tmp_path, monkeypatch):
    _state_tmp(tmp_path, monkeypatch)
    entries = _entries()
    now = datetime(2026, 8, 18, 9, 0)
    state.set_override({"key": transitions.last_key(entries[1]), "until": (now - timedelta(seconds=1)).isoformat()})
    assert daemon_schedule._override_active(entries, now) == (None, None)
    assert state.get_override() is None

    state.set_override({"key": ["/tmp/removido.mp4", "removido", "/tmp/removido.mp4"], "until": (now + timedelta(minutes=1)).isoformat()})
    assert daemon_schedule._override_active(entries, now) == (None, None)
    assert state.get_override() is None
