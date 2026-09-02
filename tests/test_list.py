from datetime import datetime, time, timedelta

import pytest

from wallpha import config


def t(h, m=0):
    return datetime(2026, 8, 18, h, m)


def test_cfg_seconds_timedelta():
    assert config.cfg_seconds(timedelta(seconds=30), 1800) == 30
    assert config.cfg_seconds(timedelta(hours=2), 1800) == 7200
    assert config.cfg_seconds(None, 1800) == 1800
    assert config.cfg_seconds("30s", 1800) == 30


def mk(tmp_path, *nomes):
    for n in nomes:
        (tmp_path / n).write_bytes(b"")
    return str(tmp_path)


# ---------------------------------------------------------------- normalização

def test_lista_agrupamento_expande(tmp_path):
    a = mk(tmp_path, "a.mp4")
    es = config.load_entries([{"nome": "grupo", "list": [{"nome": "m", "local": str(tmp_path / "a.mp4"), "tempo": "30m"}]}])
    assert len(es) == 1 and es[0]["nome"] == "m"
    lista = config.find_list("grupo")
    assert lista is not None and lista["is_list"] and lista["nome"] == "grupo"


def test_lista_unidade_tempo_fica_no_yml(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    assert len(es) == 1 and es[0]["is_list"] and es[0]["nome"] == "ciclo"


def test_lista_sub_sem_tempo_herda_da_lista(tmp_path):
    a = mk(tmp_path, "a.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "2h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4")},
    ]}])
    assert es[0]["sub_entries"][0]["tempo"] == timedelta(hours=2)


def test_lista_agrupamento_sem_tempo_erro(tmp_path):
    a = mk(tmp_path, "a.mp4")
    with pytest.raises(ValueError):
        config.load_entries([{"nome": "g", "list": [{"nome": "x", "local": str(tmp_path / "a.mp4")}]}])
    with pytest.raises(ValueError):
        config.load_entries([{"nome": "g", "list": "nao-e-uma-lista"}])


def test_find_by_name_lista(tmp_path):
    a = mk(tmp_path, "a.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "list": [{"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"}]}])
    e = config.find_by_name(es, "CICLO")
    assert e["is_list"] and e["nome"] == "ciclo"


# ---------------------------------------------------------------- resolução

def test_lista_unidade_rotaciona_subs(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    assert config.resolve_active(es, t(0, 10))["sub_nome"] == "a"
    assert config.resolve_active(es, t(0, 40))["sub_nome"] == "b"
    # fim da lista (1h): sem default, a sequência cicla de volta ao primeiro
    assert config.resolve_active(es, t(1, 5))["sub_nome"] == "a"


def test_lista_unidade_com_hora(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "hora": "8h-10h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    assert config.resolve_active(es, t(7)) is None
    assert config.resolve_active(es, t(8, 10))["sub_nome"] == "a"
    assert config.resolve_active(es, t(8, 40))["sub_nome"] == "b"
    assert config.resolve_active(es, t(10)) is None


def test_lista_agrupamento_hora(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "exemplo", "list": [
        {"nome": "manha", "local": str(tmp_path / "a.mp4"), "hora": "8h-11h"},
        {"nome": "tarde", "local": str(tmp_path / "b.mp4"), "hora": "12h-18h"},
    ]}])
    assert [e["nome"] for e in es] == ["manha", "tarde"]
    assert config.resolve_active(es, t(9))["nome"] == "manha"
    assert config.resolve_active(es, t(15))["nome"] == "tarde"
    assert config.resolve_active(es, t(20)) is None


def test_lista_sub_diretorio(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    for n in ("01.mp4", "02.mp4", "03.mp4"):
        (d / n).write_bytes(b"")
    es = config.load_entries([{"nome": "ciclo", "tempo": "2h", "list": [
        {"nome": "subd", "type": "diretório", "local": str(d), "tempo": "10m"},
    ]}])
    e = config.resolve_active(es, t(0, 15))
    assert e["sub_nome"] == "subd" and e["is_dir"]
    assert e["file_index"] == 0 and e["arquivo"].endswith("01.mp4")
    assert config.resolve_active(es, t(0, 25))["arquivo"].endswith("02.mp4")
    assert config.resolve_active(es, t(0, 35))["arquivo"].endswith("03.mp4")


# ---------------------------------------------------------------- transições / avanço

def test_next_transition_lista_slot(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "hora": "8h-10h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    assert config.next_transition(es, t(8, 10)) == t(8, 30)
    assert config.next_transition(es, t(8, 40)) == t(9)
    assert config.next_transition(es, t(9, 30)) == t(10)


def test_next_transition_lista_rotacao(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    assert config.next_transition(es, t(0, 10)) == t(0, 30)
    assert config.next_transition(es, t(0, 40)) == t(1)


def test_next_entry_lista(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    e = config.resolve_active(es, t(0, 10))
    assert config.next_entry(es, e, t(0, 10))["sub_nome"] == "b"
    assert config.next_entry(es, config.next_entry(es, e, t(0, 10)), t(0, 10))["sub_nome"] == "a"


def test_advance_in_list(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4", "c.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "10m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "10m"},
        {"nome": "c", "local": str(tmp_path / "c.mp4"), "tempo": "10m"},
    ]}])
    lista = config.find_list("ciclo")
    assert config.advance_in_list(lista, "a")["sub_nome"] == "b"
    assert config.advance_in_list(lista, "c")["sub_nome"] == "a"
    assert config.advance_in_list(lista, None)["sub_nome"] == "a"
    assert config.next_sub_by_nome(lista, "b")["sub_nome"] == "b"


# ---------------------------------------------------------------- fila / formatação

def test_list_media_queue(tmp_path):
    d = tmp_path / "d1"
    d.mkdir()
    (d / "x.png").write_bytes(b"")
    (d / "y.mp4").write_bytes(b"")
    (tmp_path / "solo.mp4").write_bytes(b"")
    config.load_entries([{"nome": "l", "tempo": "1h", "list": [
        {"nome": "d", "type": "diretório", "local": str(d), "tempo": "10m"},
        {"nome": "s", "local": str(tmp_path / "solo.mp4"), "tempo": "10m"},
    ]}])
    lista = config.find_list("l")
    files = config.list_media_queue(lista)
    assert len(files) == 3
    videos = config.list_media_queue(lista, "video")
    assert len(videos) == 2
    assert config.list_media_queue(lista, "imagem") == [str(d / "x.png")]


def test_format_entry_lista(tmp_path):
    a = mk(tmp_path, "a.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "list": [{"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"}]}])
    out = config.format_entry(config.resolve_active(es, t(0, 5)))
    assert "ciclo/a" in out


# ---------------------------------------------------------------- -c <lista> / -a <nome>

def test_start_list_cfg(tmp_path, monkeypatch):
    import wallpha
    from wallpha import state as st

    a = mk(tmp_path, "a.mp4", "b.mp4")
    config.load_entries([{"nome": "exemplo", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    lista = config.find_list("exemplo")
    monkeypatch.setattr(wallpha, "_start_service", lambda: None)
    calls = {}
    monkeypatch.setattr(st, "set_list", lambda c: calls.update(cfg=c))
    monkeypatch.setattr(st, "set_on", lambda v: calls.update(on=v))
    monkeypatch.setattr(st, "clear_pos", lambda: None)
    monkeypatch.setattr(st, "clear_random", lambda: None)

    wallpha._start_list(lista, {"loop": "true"})
    assert calls["cfg"]["nome"] == "exemplo"
    assert calls["cfg"]["loop"] is True
    assert calls["cfg"]["slideshow"] is False
    assert calls["on"] is True

    wallpha._start_list(lista, {"tempo": "10m", "images": True})
    assert calls["cfg"]["slideshow"] is True
    assert calls["cfg"]["tipo"] == "imagem"
    assert calls["cfg"]["tempo"] == 600


def test_list_next_ciclo(tmp_path, monkeypatch):
    import wallpha
    from wallpha import state as st

    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "2h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    import wallpha.entries as _entries
    monkeypatch.setattr(_entries, "load", lambda *a, **kw: es)
    monkeypatch.setattr(config, "load", lambda *a, **kw: es)
    kept = {"cfg": {"nome": "ciclo", "tempo": None, "max": None, "qtd": None, "loop": False,
                    "rep": False, "tipo": None, "integro": False, "som": None,
                    "slideshow": False, "persist": False, "idx": 0, "shuffled": False}}
    monkeypatch.setattr(st, "get_list", lambda: kept["cfg"])
    monkeypatch.setattr(st, "set_list", lambda c: kept.update(cfg=c))
    monkeypatch.setattr(st, "clear_list", lambda: kept.update(cfg=None))
    applied = []
    monkeypatch.setattr(wallpha.apply, "apply", lambda path, **kw: (applied.append(str(path)), ("p", path))[1])

    wallpha._list_next()
    assert applied[0].endswith("a.mp4") and kept["cfg"]["idx"] == 1
    wallpha._list_next()
    assert applied[1].endswith("b.mp4")
    wallpha._list_next()
    assert len(applied) == 2


def test_auto_mode_single_item(tmp_path, monkeypatch):
    import wallpha
    from wallpha import state as st

    a = mk(tmp_path, "a.mp4")
    es = config.load_entries([{"nome": "sozinho", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
                              {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    import wallpha.entries as _entries2
    monkeypatch.setattr(_entries2, "load", lambda *a, **kw: es)
    monkeypatch.setattr(config, "load", lambda *a, **kw: es)
    monkeypatch.setattr(wallpha, "_start_service", lambda: None)
    calls = {}
    monkeypatch.setattr(st, "set_list", lambda c: calls.update(cfg=c))
    monkeypatch.setattr(st, "set_on", lambda v: calls.update(on=v))
    monkeypatch.setattr(st, "clear_pos", lambda: None)
    monkeypatch.setattr(st, "clear_random", lambda: None)

    wallpha._auto_mode({"target": "sozinho"})
    assert calls["cfg"]["nome"] == "sozinho"
    assert calls["cfg"]["persist"] is True
    assert calls["on"] is True