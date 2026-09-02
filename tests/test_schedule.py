from datetime import datetime, time, timedelta

import pytest

from wallpha import config


def t(h, m=0):
    return datetime(2026, 8, 18, h, m)


# ---------------------------------------------------------------- tempo/hora

def test_parse_tempo():
    assert config.parse_tempo("30m") == timedelta(minutes=30)
    assert config.parse_tempo("2h") == timedelta(hours=2)
    assert config.parse_tempo("1d") == timedelta(days=1)
    assert config.parse_tempo("1h30m10s") == timedelta(hours=1, minutes=30, seconds=10)
    assert config.parse_tempo("45") == timedelta(minutes=45)
    assert config.parse_tempo(45) == timedelta(minutes=45)
    assert config.parse_tempo(None) is None
    assert config.parse_tempo("abc") is None


def test_parse_time():
    assert config.parse_time("9h") == time(9, 0)
    assert config.parse_time("9h30m") == time(9, 30)
    assert config.parse_time("9h30m15s") == time(9, 30, 15)
    assert config.parse_time("30m") == time(0, 30)
    assert config.parse_time("15s") == time(0, 0, 15)
    assert config.parse_time("08:00") == time(8, 0)
    assert config.parse_time("08:00:30") == time(8, 0, 30)


def test_parse_hora():
    assert config.parse_hora("9h-10h") == (time(9, 0), time(10, 0))
    assert config.parse_hora("9h30m-11h") == (time(9, 30), time(11, 0))
    assert config.parse_hora("9h") == (time(9, 0), None)
    assert config.parse_hora(None) == (None, None)


def test_hora_range_fim_menor_que_inicio():
    with pytest.raises(ValueError):
        config.parse_hora("23h-1h")


# ---------------------------------------------------------------- validação

def test_hora_sem_range_exige_tempo():
    with pytest.raises(ValueError):
        config.load_entries([{"nome": "x", "local": "/tmp/x.mp4", "hora": "9h"}])


def test_hora_range_nao_exige_tempo():
    e = config.load_entries([{"nome": "x", "local": "/tmp/x.mp4", "hora": "9h-10h"}])
    assert e[0]["hora_start"] == time(9, 0)
    assert e[0]["hora_end"] == time(10, 0)


def test_hora_inicio_mais_tempo():
    e = config.load_entries([{"nome": "x", "local": "/tmp/x.mp4", "hora": "9h", "tempo": "1h"}])
    assert e[0]["hora_start"] == time(9, 0)
    assert e[0]["hora_end"] is None


def test_default_nao_pode_ter_hora():
    with pytest.raises(ValueError):
        config.load_entries([{"nome": "d", "local": "/tmp/d.mp4", "default": True, "hora": "9h-10h"}])


def test_arquivo_sem_hora_tempo_default_erro():
    with pytest.raises(ValueError):
        config.load_entries([{"nome": "x", "local": "/tmp/x.mp4"}])


# ---------------------------------------------------------------- agenda

def make(entries):
    return config.load_entries(entries)


def test_hora_range_slot():
    es = make([{"nome": "a", "local": "/tmp/a.mp4", "hora": "8h-10h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.resolve_active(es, t(7))["nome"] == "d"
    assert config.resolve_active(es, t(8))["nome"] == "a"
    assert config.resolve_active(es, t(9, 59))["nome"] == "a"
    assert config.resolve_active(es, t(10))["nome"] == "d"


def test_hora_inicio_tempo_define_fim():
    es = make([{"nome": "a", "local": "/tmp/a.mp4", "hora": "8h", "tempo": "2h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.resolve_active(es, t(9))["nome"] == "a"
    assert config.resolve_active(es, t(10))["nome"] == "d"


def test_hora_substitui_tempo():
    es = make([{"nome": "rot", "local": "/tmp/r.mp4", "tempo": "12h"},
               {"nome": "a", "local": "/tmp/a.mp4", "hora": "10h-11h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.resolve_active(es, t(9))["nome"] == "rot"
    assert config.resolve_active(es, t(10, 30))["nome"] == "a"
    # turno de 12h: às 12h ainda no "rot" (hora foi descontada do tempo livre)
    assert config.resolve_active(es, t(12))["nome"] == "rot"
    # 13h: 13h livres - 1h da hora = 12h -> turno encerra, vai ao default
    assert config.resolve_active(es, t(13))["nome"] == "d"


def test_hora_interrompe_e_continua(tmp_path):
    for n in ("01.mp4", "02.mp4", "03.mp4"):
        (tmp_path / n).write_bytes(b"")
    es = make([{"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "1h", "loop": True},
               {"nome": "a", "local": "/tmp/a.mp4", "hora": "2h-3h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    base = datetime(2026, 8, 18, 0, 0)
    assert config.resolve_active(es, base + timedelta(minutes=30))["arquivo"].endswith("01.mp4")
    assert config.resolve_active(es, base + timedelta(minutes=90))["arquivo"].endswith("02.mp4")
    assert config.resolve_active(es, base + timedelta(minutes=150))["nome"] == "a"
    # 3h30: 3h30 de tempo livre - 1h da hora = 2h30 -> arquivo index 2 -> 03.mp4
    assert config.resolve_active(es, base + timedelta(minutes=210))["arquivo"].endswith("03.mp4")


def test_sequencia_rota_no_orden():
    es = make([{"nome": "a", "local": "/tmp/a.mp4", "tempo": "1h"},
               {"nome": "b", "local": "/tmp/b.mp4", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.resolve_active(es, t(0, 30))["nome"] == "a"
    assert config.resolve_active(es, t(1, 30))["nome"] == "b"
    # fim da sequência -> default
    assert config.resolve_active(es, t(2, 30))["nome"] == "d"


def test_sem_default_cicla():
    es = make([{"nome": "a", "local": "/tmp/a.mp4", "tempo": "1h"},
               {"nome": "b", "local": "/tmp/b.mp4", "tempo": "1h"}])
    assert config.resolve_active(es, t(2, 30))["nome"] == "a"
    assert config.resolve_active(es, t(3, 30))["nome"] == "b"


def test_diretorio_rotaciona_arquivos(tmp_path):
    for n in ("01.mp4", "02.mp4", "03.mp4"):
        (tmp_path / n).write_bytes(b"")
    es = make([{"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    base = datetime(2026, 8, 18, 0, 0)
    assert config.resolve_active(es, base)["arquivo"].endswith("01.mp4")
    assert config.resolve_active(es, base + timedelta(minutes=10))["arquivo"].endswith("02.mp4")
    assert config.resolve_active(es, base + timedelta(minutes=25))["arquivo"].endswith("03.mp4")
    # fim da passada (30m) -> default
    assert config.resolve_active(es, base + timedelta(minutes=31))["nome"] == "d"


def test_diretorio_loop_true_cicla(tmp_path):
    for n in ("a.mp4", "b.mp4"):
        (tmp_path / n).write_bytes(b"")
    es = make([{"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m", "loop": True},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    base = datetime(2026, 8, 18, 0, 0)
    assert config.resolve_active(es, base + timedelta(minutes=20))["arquivo"].endswith("a.mp4")
    assert config.resolve_active(es, base + timedelta(minutes=25))["arquivo"].endswith("a.mp4")
    assert config.resolve_active(es, base + timedelta(minutes=30))["arquivo"].endswith("b.mp4")


def test_diretorio_sem_tempo_erro(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"")
    with pytest.raises(ValueError):
        config.load_entries([{"nome": "dir", "type": "diretório", "local": str(tmp_path)}])


def test_default_diretorio_cicla(tmp_path):
    for n in ("x.mp4", "y.mp4"):
        (tmp_path / n).write_bytes(b"")
    es = make([{"nome": "d", "type": "diretório", "local": str(tmp_path), "tempo": "10m", "loop": True, "default": True}])
    base = datetime(2026, 8, 18, 0, 0)
    assert config.resolve_active(es, base + timedelta(minutes=5))["arquivo"].endswith("x.mp4")
    assert config.resolve_active(es, base + timedelta(minutes=15))["arquivo"].endswith("y.mp4")


# ---------------------------------------------------------------- transições

def test_next_transition_hora():
    es = make([{"nome": "a", "local": "/tmp/a.mp4", "hora": "8h-10h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.next_transition(es, t(7)) == t(8)
    assert config.next_transition(es, t(9)) == t(10)


def test_next_transition_rota():
    es = make([{"nome": "a", "local": "/tmp/a.mp4", "tempo": "1h"},
               {"nome": "b", "local": "/tmp/b.mp4", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.next_transition(es, t(0, 30)) == t(1)
    assert config.next_transition(es, t(1, 30)) == t(2)


# ---------------------------------------------------------------- -c

def test_next_entry_cicla():
    es = make([{"nome": "a", "local": "/tmp/a.mp4", "tempo": "1h"},
               {"nome": "b", "local": "/tmp/b.mp4", "tempo": "1h"}])
    ativo = config.resolve_active(es, t(0, 30))  # a
    assert config.next_entry(es, ativo, t(0, 30))["nome"] == "b"
    assert config.next_entry(es, config.resolve_active(es, t(1, 30)), t(1, 30))["nome"] == "a"


def test_next_entry_diretorio_cicla_arquivos(tmp_path):
    for n in ("a.mp4", "b.mp4", "c.mp4"):
        (tmp_path / n).write_bytes(b"")
    es = make([{"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m", "loop": True}])
    ativo = config.resolve_active(es, datetime(2026, 8, 18, 0, 0))  # arquivo a.mp4
    nxt = config.next_entry(es, ativo, datetime(2026, 8, 18, 0, 0))
    assert nxt["arquivo"].endswith("b.mp4")
    nxt2 = config.next_entry(es, nxt, datetime(2026, 8, 18, 0, 0))
    assert nxt2["arquivo"].endswith("c.mp4")
    nxt3 = config.next_entry(es, nxt2, datetime(2026, 8, 18, 0, 0))
    assert nxt3["arquivo"].endswith("a.mp4")


def test_find_by_name_ignora_caixa():
    es = make([{"nome": "manha", "local": "/tmp/m.mp4", "tempo": "1h"}])
    assert config.find_by_name(es, "MANHA")["nome"] == "manha"
    assert config.find_by_name(es, "x") is None