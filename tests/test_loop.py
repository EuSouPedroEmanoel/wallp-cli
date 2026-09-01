from datetime import datetime, timedelta

import pytest

from wallp import config


def t(h, m=0):
    return datetime(2026, 8, 18, h, m)


def mk(tmp_path, *nomes):
    for n in nomes:
        (tmp_path / n).write_bytes(b"")
    return str(tmp_path)


# ---------------------------------------------------------------- parse_loop

def test_parse_loop_variacoes():
    assert config.parse_loop(None) is False
    assert config.parse_loop(False) is False
    assert config.parse_loop(0) is False
    assert config.parse_loop("false") is False
    assert config.parse_loop(True) is True
    assert config.parse_loop("true") is True
    assert config.parse_loop(2) == 2
    assert config.parse_loop("3") == 3
    assert config.parse_loop(3.0) == 3
    assert config.is_loop_n(False) is False  # bool não é N de ciclos
    assert config.is_loop_n(True) is False
    assert config.is_loop_n(2) is True


@pytest.mark.parametrize("v", ["abc", -1, "sim", 1.5])
def test_parse_loop_invalido(v):
    with pytest.raises(ValueError):
        config.parse_loop(v)


# ---------------------------------------------------------------- vídeo com loop: true (trava)

def test_video_loop_true_rot_duration_infinita():
    e = config.load_entries([{"nome": "v", "local": "/tmp/v.mp4", "loop": True}])[0]
    assert config._rot_duration(e) is None
    v2 = config.load_entries([{"nome": "v", "local": "/tmp/v.mp4", "loop": 3}])[0]
    assert config._rot_duration(v2) is None  # int em vídeo também trava


def test_video_loop_true_slot_vai_ate_o_proximo():
    es = config.load_entries([
        {"nome": "a", "local": "/tmp/a.mp4", "hora": "9h", "loop": True},
        {"nome": "b", "local": "/tmp/b.mp4", "hora": "12h-13h"},
        {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    slots = config._hora_slots(es, t(0).date())
    # sem hora_end e loop infinito -> fim = início do próximo slot
    assert slots[0][1] == datetime(2026, 8, 18, 12, 0)
    assert config.resolve_active(es, t(9, 30))["nome"] == "a"
    assert config.resolve_active(es, t(11, 59))["nome"] == "a"
    assert config.resolve_active(es, t(13, 30))["nome"] == "d"


def test_daemon_aplica_playback_loop_no_video(monkeypatch):
    from wallp import daemon, state

    es = config.load_entries([{"nome": "v", "local": "/tmp/v.mp4", "loop": True},
                              {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    monkeypatch.setattr(state, "is_on", lambda: True)
    monkeypatch.setattr(state, "get_random", lambda: None)
    monkeypatch.setattr(state, "get_list", lambda: None)
    monkeypatch.setattr(config, "load_checked", lambda: es)
    import wallp.entries as _e
    monkeypatch.setattr(_e, "load_checked", lambda *a, **kw: es)
    import wallp.daemon_schedule as _ds
    monkeypatch.setattr(_ds.entries, "load_checked", lambda *a, **kw: es)
    monkeypatch.setattr(config, "next_transition", lambda entries, now: now.replace(hour=23))
    import wallp.transitions as _tr
    monkeypatch.setattr(_tr, "next_transition", lambda entries, now: now.replace(hour=23))
    monkeypatch.setattr(_ds.transitions, "next_transition", lambda entries, now: now.replace(hour=23))
    got = {}
    monkeypatch.setattr(daemon.apply, "apply",
                        lambda path, **kw: got.update(loop=kw.get("loop"), path=str(path)) or ("p", str(path)))

    def fake_sleep(sec):
        raise SystemExit(0)

    monkeypatch.setattr(daemon.time, "sleep", fake_sleep)
    with pytest.raises(SystemExit):
        daemon._run_schedule()
    assert got["loop"] is True and got["path"] == "/tmp/v.mp4"


# ---------------------------------------------------------------- vídeo loop + tempo -> erro

def test_video_loop_e_tempo_erro():
    with pytest.raises(ValueError) as ex:
        config.load_entries([{"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h", "loop": True}])
    assert "loop e tempo" in str(ex.value)


def test_sub_item_de_lista_video_loop_e_tempo_erro():
    with pytest.raises(ValueError):
        config.load_entries([{"nome": "grupo", "list": [
            {"nome": "s", "local": "/tmp/s.mp4", "tempo": "30m", "loop": True}]}])


def test_loop_relaxa_validacao():
    # arquivo/yt sem hora/tempo/default é aceito quando tem loop
    e = config.load_entries([{"nome": "f", "local": "/tmp/f.mp4", "loop": True}])[0]
    assert e["loop"] is True
    y = config.load_entries([{"nome": "y", "local": "https://youtu.be/x", "type": "youtube", "loop": True}])[0]
    assert y["is_yt"] and y["loop"] is True
    h = config.load_entries([{"nome": "h", "local": "/tmp/h.mp4", "hora": "9h", "loop": True}])[0]
    assert h["hora_start"] is not None and h["tempo"] is None


# ---------------------------------------------------------------- diretório loop: 2

def test_dir_loop_2_ciclos(tmp_path):
    mk(tmp_path, "01.mp4", "02.mp4", "03.mp4")
    es = config.load_entries([
        {"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m", "loop": 2},
        {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    e = es[0]
    assert config.is_loop_n(e["loop"]) and e["loop"] == 2
    assert config._rot_duration(e) == timedelta(minutes=60)

    base = datetime(2026, 8, 18, 0, 0)
    assert config.resolve_active(es, base + timedelta(minutes=5))["arquivo"].endswith("01.mp4")
    assert config.resolve_active(es, base + timedelta(minutes=15))["arquivo"].endswith("02.mp4")
    # segundo ciclo repete a ordem
    assert config.resolve_active(es, base + timedelta(minutes=35))["arquivo"].endswith("01.mp4")
    # depois de 2 ciclos (60m) sai para o default
    assert config.resolve_active(es, base + timedelta(minutes=65))["nome"] == "d"


def test_dir_loop_2_next_transition_fim_apos_n(tmp_path):
    mk(tmp_path, "01.mp4", "02.mp4", "03.mp4")
    es = config.load_entries([
        {"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m", "loop": 2},
        {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    base = datetime(2026, 8, 18, 0, 0)
    # primeira troca interna
    assert config.next_transition(es, base) == base + timedelta(minutes=10)
    # última transição = fim do ciclo N (60m); depois disso só o dia seguinte
    assert config.next_transition(es, base + timedelta(minutes=55)) == base + timedelta(minutes=60)
    assert config.next_transition(es, base + timedelta(minutes=65)) == datetime(2026, 8, 19, 0, 0)


def test_dir_sem_loop_next_transition_normal(tmp_path):
    mk(tmp_path, "01.mp4", "02.mp4")
    es = config.load_entries([
        {"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m"},
        {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    base = datetime(2026, 8, 18, 0, 0)
    # uma passada: última troca interna em 10m e fim da rotação em 20m
    assert config.next_transition(es, base + timedelta(minutes=15)) == base + timedelta(minutes=20)
    assert config.resolve_active(es, base + timedelta(minutes=25))["nome"] == "d"


# ---------------------------------------------------------------- lista loop: 2

def test_lista_loop_2_rot_duration_finita(tmp_path):
    mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "loop": 2, "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    e = next(x for x in es if x.get("is_list"))
    assert config._rot_duration(e) == timedelta(hours=2)


def test_daemon_list_cycle_2_passadas(tmp_path, monkeypatch, capsys):
    from wallp import daemon, state

    mk(tmp_path, "a.mp4", "b.mp4")
    es = config.load_entries([{"nome": "ciclo", "tempo": "1h", "loop": 2, "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    kept = {"cfg": {"nome": "ciclo", "tempo": None, "max": None, "qtd": None, "loop": 2,
                    "rep": False, "tipo": None, "integro": False, "som": None,
                    "slideshow": False, "persist": False, "idx": 0, "shuffled": False}}
    monkeypatch.setattr(state, "is_on", lambda: True)
    monkeypatch.setattr(state, "get_random", lambda: None)
    monkeypatch.setattr(state, "get_list", lambda: kept["cfg"])
    monkeypatch.setattr(state, "set_list", lambda c: kept.update(cfg=c))
    monkeypatch.setattr(state, "clear_list", lambda: kept.update(cfg=None))
    monkeypatch.setattr(daemon.config, "load_checked", lambda: es)
    import wallp.entries as _e2
    monkeypatch.setattr(_e2, "load_checked", lambda *a, **kw: es)
    import wallp.daemon_list as _dl
    monkeypatch.setattr(_dl.entries, "load_checked", lambda *a, **kw: es)
    applied = []
    monkeypatch.setattr(daemon.apply, "apply",
                        lambda path, **kw: applied.append(str(path)) or ("p", str(path)))
    clock = {"now": 1000.0}
    monkeypatch.setattr(daemon.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(daemon.time, "sleep", lambda s: clock.update(now=clock["now"] + s))

    # compat: daemon now exposes _run_list_cycle via daemon_list
    import wallp.daemon_list as _dl2
    daemon._run_list_cycle = _dl2._run_list_cycle
    daemon._run_list_cycle(config.find_list("ciclo")["sub_entries"], kept["cfg"])
    # 2 passadas x 2 sub-itens
    assert [p.split("/")[-1] for p in applied] == ["a.mp4", "b.mp4", "a.mp4", "b.mp4"]
    assert kept["cfg"] is None  # clear_list chamado
    assert "lista concluída (2 vezes)" in capsys.readouterr().err


# ---------------------------------------------------------------- slideshow -l 2

def test_daemon_list_slideshow_l_2_passadas(tmp_path, monkeypatch, capsys):
    from wallp import daemon, state

    mk(tmp_path, "x.mp4", "y.mp4")
    es = config.load_entries([{"nome": "slide", "default": True, "list": [
        {"nome": "x", "local": str(tmp_path / "x.mp4"), "tempo": "30m"},
        {"nome": "y", "local": str(tmp_path / "y.mp4"), "tempo": "30m"},
    ]}])
    cfg = {"nome": "slide", "tempo": None, "max": None, "qtd": None, "loop": 2,
           "rep": False, "tipo": None, "integro": False, "som": None,
           "slideshow": True, "persist": False, "idx": 0, "shuffled": False}
    kept = {"cfg": dict(cfg), "pos": None}
    monkeypatch.setattr(state, "is_on", lambda: True)
    monkeypatch.setattr(state, "get_random", lambda: None)
    monkeypatch.setattr(state, "get_list", lambda: dict(kept["cfg"]))
    monkeypatch.setattr(state, "set_list", lambda c: kept.update(cfg=c))
    monkeypatch.setattr(state, "clear_list", lambda: kept.update(cfg=None))
    monkeypatch.setattr(state, "get_pos", lambda: kept["pos"])
    monkeypatch.setattr(state, "set_pos", lambda p: kept.update(pos=p))
    monkeypatch.setattr(daemon.config, "load_checked", lambda: es)
    monkeypatch.setattr(daemon.config, "get_salt", lambda: "salt-teste")
    import wallp.entries as _e3
    monkeypatch.setattr(_e3, "load_checked", lambda *a, **kw: es)
    import wallp.media as _m3
    monkeypatch.setattr(_m3, "get_salt", lambda: "salt-teste")
    import wallp.daemon_list as _dl3
    monkeypatch.setattr(_dl3.entries, "load_checked", lambda *a, **kw: es)
    monkeypatch.setattr(_dl3.media, "get_salt", lambda: "salt-teste")
    applied = []
    monkeypatch.setattr(daemon.apply, "apply",
                        lambda path, **kw: applied.append(str(path)) or ("p", str(path)))
    clock = {"now": 1000.0}
    monkeypatch.setattr(daemon.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(daemon.time, "sleep", lambda s: clock.update(now=clock["now"] + s))

    lista = config.find_list("slide")
    # compat
    import wallp.daemon_list as _dl4
    daemon._run_list_slideshow = _dl4._run_list_slideshow
    daemon._run_list_slideshow(cfg, lista)
    # 2 passadas x 2 arquivos
    assert [p.split("/")[-1] for p in applied] == ["x.mp4", "y.mp4", "x.mp4", "y.mp4"]
    assert "slideshow concluído (2 passadas)" in capsys.readouterr().err


def test_start_list_l_2_cfg_int(tmp_path, monkeypatch):
    import wallp
    from wallp import state as st

    mk(tmp_path, "a.mp4", "b.mp4")
    config.load_entries([{"nome": "exemplo", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
    ]}])
    lista = config.find_list("exemplo")
    monkeypatch.setattr(wallp, "_start_service", lambda: None)
    calls = {}
    monkeypatch.setattr(st, "set_list", lambda c: calls.update(cfg=c))
    monkeypatch.setattr(st, "set_on", lambda v: calls.update(on=v))
    monkeypatch.setattr(st, "clear_pos", lambda: None)
    monkeypatch.setattr(st, "clear_random", lambda: None)

    wallp._start_list(lista, {"loop": "2"})
    assert calls["cfg"]["loop"] == 2
    assert isinstance(calls["cfg"]["loop"], int)


# ---------------------------------------------------------------- format_entry / mensagens

def test_format_entry_mostra_loop():
    # loop=N em vídeo trava igual true -> não pode ter tempo; usa hora com range
    e = config.load_entries([{"nome": "f", "local": "/tmp/f.mp4", "hora": "9h-10h", "loop": 2}])[0]
    assert ", loop=2" in config.format_entry(e)
    e2 = config.load_entries([{"nome": "g", "local": "/tmp/g.mp4", "loop": True}])[0]
    assert ", loop" in config.format_entry(e2)
    assert ", loop=" not in config.format_entry(e2)
