from datetime import date, datetime, time, timedelta

import pytest

from wallpha import config

# seg = 2026-08-17, ter = 2026-08-18, qua = 19, qui = 20, sex = 21, sab = 22, dom = 23
MON = datetime(2026, 8, 17)
TUE = datetime(2026, 8, 18)
SAB = datetime(2026, 8, 22)
DOM = datetime(2026, 8, 23)


def make(entries):
    return config.load_entries(entries)


# ---------------------------------------------------------------- parse_dia

def test_parse_dia_weekday():
    assert config.parse_dia("seg") == {"tipo": "weekday", "valor": 0}
    assert config.parse_dia("TER") == {"tipo": "weekday", "valor": 1}
    assert config.parse_dia("dom") == {"tipo": "weekday", "valor": 6}


def test_parse_dia_monthday():
    assert config.parse_dia(15) == {"tipo": "monthday", "valor": 15}
    assert config.parse_dia("15") == {"tipo": "monthday", "valor": 15}
    assert config.parse_dia(1) == {"tipo": "monthday", "valor": 1}


def test_parse_dia_yearday():
    assert config.parse_dia("01-04") == {"tipo": "yearday", "valor": (1, 4)}
    assert config.parse_dia("31-12") == {"tipo": "yearday", "valor": (31, 12)}


def test_parse_dia_date():
    assert config.parse_dia("20-12-2026") == {"tipo": "date", "valor": date(2026, 12, 20)}
    assert config.parse_dia("01-04-2026") == {"tipo": "date", "valor": date(2026, 4, 1)}


def test_parse_dia_none():
    assert config.parse_dia(None) is None


def test_parse_dia_invalidos():
    for v in ("foo", 32, "0", "31-02-2026", "32-13", "00-04", ""):
        with pytest.raises(ValueError):
            config.parse_dia(v)


def test_fmt_dia():
    assert config.fmt_dia({"tipo": "weekday", "valor": 0}) == "seg"
    assert config.fmt_dia({"tipo": "monthday", "valor": 15}) == "15"
    assert config.fmt_dia({"tipo": "yearday", "valor": (1, 4)}) == "01-04"
    assert config.fmt_dia({"tipo": "date", "valor": date(2026, 12, 20)}) == "20-12-2026"


# ---------------------------------------------------------------- resolve_active

def test_weekday_soma_ativa_so_no_dia():
    es = make([{"nome": "segunda", "local": "/tmp/seg.mp4", "dia": "seg", "hora": "8h-10h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.resolve_active(es, datetime(2026, 8, 17, 9))["nome"] == "segunda"  # segunda
    assert config.resolve_active(es, datetime(2026, 8, 18, 9))["nome"] == "d"        # terça


def test_monthday_ativo_no_dia_do_mes():
    es = make([{"nome": "quinze", "local": "/tmp/q.mp4", "dia": 15, "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.resolve_active(es, datetime(2026, 8, 14, 0, 30))["nome"] == "d"
    assert config.resolve_active(es, datetime(2026, 8, 15, 0, 30))["nome"] == "quinze"
    assert config.resolve_active(es, datetime(2026, 8, 15, 1, 30))["nome"] == "d"
    assert config.resolve_active(es, datetime(2026, 9, 15, 0, 30))["nome"] == "quinze"


def test_yearday_ativo_no_dia_do_ano():
    es = make([{"nome": "abril", "local": "/tmp/a.mp4", "dia": "01-04", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.resolve_active(es, datetime(2026, 4, 1, 0, 30))["nome"] == "abril"
    assert config.resolve_active(es, datetime(2026, 4, 2, 0, 30))["nome"] == "d"
    assert config.resolve_active(es, datetime(2027, 4, 1, 0, 30))["nome"] == "abril"


def test_data_especifica_so_naquele_dia():
    es = make([{"nome": "natal", "local": "/tmp/n.mp4", "dia": "25-12-2026", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.resolve_active(es, datetime(2026, 12, 25, 0, 30))["nome"] == "natal"
    assert config.resolve_active(es, datetime(2026, 12, 26, 0, 30))["nome"] == "d"
    # ano seguinte: a data não se repete
    assert config.resolve_active(es, datetime(2027, 12, 25, 0, 30))["nome"] == "d"


def test_default_com_dia_soma_no_dia_e_some_fora():
    es = make([{"nome": "fim", "local": "/tmp/f.mp4", "dia": "sab", "tempo": "1h", "default": True}])
    assert config.resolve_active(es, SAB.replace(hour=0, minute=30))["nome"] == "fim"
    assert config.resolve_active(es, DOM.replace(hour=0, minute=30)) is None


def test_rotacao_pula_item_fora_do_dia():
    es = make([{"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "tempo": "1h"},
               {"nome": "resto", "local": "/tmp/r.mp4", "tempo": "1h"}])
    # segunda: só "segunda" entra na rotação
    assert config.resolve_active(es, datetime(2026, 8, 17, 0, 30))["nome"] == "segunda"
    # terça: "segunda" some e "resto" preenche
    assert config.resolve_active(es, datetime(2026, 8, 18, 0, 30))["nome"] == "resto"
    assert config.resolve_active(es, datetime(2026, 8, 18, 1, 30))["nome"] == "resto"


def test_sem_nenhum_item_do_dia_retorna_none():
    es = make([{"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "tempo": "1h"}])
    assert config.resolve_active(es, DOM.replace(hour=10)) is None


# ---------------------------------------------------------------- next_transition

def test_next_transition_weekday_atravessa_dias():
    es = make([{"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "hora": "8h-10h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    # domingo -> a próxima segunda começa
    assert config.next_transition(es, datetime(2026, 8, 16, 12)) == datetime(2026, 8, 17)
    assert config.next_transition(es, datetime(2026, 8, 17)) == datetime(2026, 8, 17, 8)
    assert config.next_transition(es, datetime(2026, 8, 17, 9, 30)) == datetime(2026, 8, 17, 10)


def test_next_transition_data_especifica():
    es = make([{"nome": "natal", "local": "/tmp/n.mp4", "dia": "25-12-2026", "hora": "8h-10h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    assert config.next_transition(es, datetime(2026, 12, 24, 12)) == datetime(2026, 12, 25)


def test_next_transition_rotacao_com_dia():
    es = make([{"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "tempo": "1h"}])
    # domingo 12h: próxima transição é segunda 00:00 (rotação recomeça)
    assert config.next_transition(es, datetime(2026, 8, 16, 12)) == datetime(2026, 8, 17)
    # segunda 12h: "segunda" terminou às 1h; próxima é na segunda seguinte
    assert config.next_transition(es, datetime(2026, 8, 17, 12)) == datetime(2026, 8, 24)


# ---------------------------------------------------------------- listas

def test_lista_unidade_com_dia(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = make([{"nome": "fim de semana", "dia": "sab", "tempo": "2h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "1h"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "1h"},
    ]}])
    assert config.resolve_active(es, SAB.replace(hour=0, minute=30))["sub_nome"] == "a"
    assert config.resolve_active(es, SAB.replace(hour=1, minute=30))["sub_nome"] == "b"
    assert config.resolve_active(es, DOM.replace(hour=0, minute=30)) is None


def test_lista_sub_item_com_dia(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = make([{"nome": "exemplo", "list": [
        {"nome": "segunda", "local": str(tmp_path / "a.mp4"), "dia": "seg", "hora": "8h-10h"},
        {"nome": "tarde", "local": str(tmp_path / "b.mp4"), "tempo": "1h"},
    ]}])
    assert config.resolve_active(es, datetime(2026, 8, 17, 9))["nome"] == "segunda"
    assert config.resolve_active(es, datetime(2026, 8, 18, 9))["nome"] == "tarde"


def test_next_entry_pula_fora_do_dia():
    es = make([{"nome": "a", "local": "/tmp/a.mp4", "tempo": "1h"},
               {"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "tempo": "1h"}])
    ativo = config.resolve_active(es, datetime(2026, 8, 18, 0, 30))  # terça -> a
    nxt = config.next_entry(es, ativo, datetime(2026, 8, 18, 0, 30))
    assert nxt["nome"] == "a"  # cicla em "a", pula "segunda"


def test_format_entry_dia():
    es = make([{"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "hora": "8h-10h"}])
    out = config.format_entry(es[0])
    assert "dia=seg" in out
    es2 = make([{"nome": "natal", "local": "/tmp/n.mp4", "dia": "25-12-2026", "tempo": "1h"}])
    assert "dia=25-12-2026" in config.format_entry(es2[0])


def mk(tmp_path, *nomes):
    for n in nomes:
        (tmp_path / n).write_bytes(b"")
    return str(tmp_path)


# ---------------------------------------------------------------- erro de yml

def test_load_checked_yml_invalido_retorna_none(monkeypatch):
    import wallpha.entries as entries_mod
    monkeypatch.setattr(entries_mod, "load", lambda *a, **kw: entries_mod.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "dia": "foo", "tempo": "1h"}]))
    monkeypatch.setattr(config, "load", lambda *a, **kw: config.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "dia": "foo", "tempo": "1h"}]))
    assert entries_mod.load_checked() is None
    assert config.load_checked() is None


def test_c_dia_invalido_sai_limpo(monkeypatch, capsys):
    import sys
    import wallpha
    import wallpha.entries as entries_mod
    monkeypatch.setattr(sys, "argv", ["wallpha", "-c", "x"])
    monkeypatch.setattr(entries_mod, "load", lambda *a, **kw: entries_mod.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "dia": "foo", "tempo": "1h"}]))
    monkeypatch.setattr(config, "load", lambda *a, **kw: config.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "dia": "foo", "tempo": "1h"}]))
    with pytest.raises(SystemExit) as ex:
        wallpha.main()
    assert ex.value.code == 1
    assert "dia inválido" in capsys.readouterr().err


def test_c_yml_yaml_quebrado_sai_limpo(monkeypatch, capsys):
    import sys
    import wallpha
    import wallpha.entries as entries_mod
    monkeypatch.setattr(sys, "argv", ["wallpha", "-c", "x"])
    monkeypatch.setattr(entries_mod, "load", lambda *a, **kw: (_ for _ in ()).throw(
        __import__("yaml").YAMLError("erro de sintaxe")))
    monkeypatch.setattr(config, "load", lambda *a, **kw: (_ for _ in ()).throw(
        __import__("yaml").YAMLError("erro de sintaxe")))
    with pytest.raises(SystemExit) as ex:
        wallpha.main()
    assert ex.value.code == 1
    assert "erro de sintaxe" in capsys.readouterr().err


def test_daemon_schedule_yml_invalido_nao_crasha(monkeypatch):
    from wallpha import daemon, state
    monkeypatch.setattr(state, "is_on", lambda: True)
    monkeypatch.setattr(state, "get_random", lambda: None)
    monkeypatch.setattr(state, "get_list", lambda: None)
    monkeypatch.setattr(config, "load_checked", lambda: None)
    import wallpha.entries as _entries
    monkeypatch.setattr(_entries, "load_checked", lambda *a, **kw: None)
    import wallpha.daemon_schedule as _ds
    monkeypatch.setattr(_ds.entries, "load_checked", lambda *a, **kw: None)
    import wallpha.daemon_list as _dl
    monkeypatch.setattr(_dl.entries, "load_checked", lambda *a, **kw: None)
    calls = {"n": 0}

    def fake_sleep(sec):
        calls["n"] += 1
        if calls["n"] >= 3:
            raise SystemExit(0)

    monkeypatch.setattr(daemon.time, "sleep", fake_sleep)
    with pytest.raises(SystemExit):
        daemon.run()
    assert calls["n"] >= 3  # ficou em loop aguardando, sem crashar


def test_daemon_list_yml_invalido_nao_crasha(monkeypatch):
    from wallpha import daemon, state
    monkeypatch.setattr(state, "is_on", lambda: True)
    monkeypatch.setattr(state, "get_random", lambda: None)
    monkeypatch.setattr(state, "get_list", lambda: {"nome": "x"})
    monkeypatch.setattr(config, "load_checked", lambda: None)
    import wallpha.entries as _entries2
    monkeypatch.setattr(_entries2, "load_checked", lambda *a, **kw: None)
    import wallpha.daemon_list as _dl2
    monkeypatch.setattr(_dl2.entries, "load_checked", lambda *a, **kw: None)
    calls = {"n": 0}

    def fake_sleep(sec):
        calls["n"] += 1
        if calls["n"] >= 3:
            raise SystemExit(0)

    monkeypatch.setattr(daemon.time, "sleep", fake_sleep)
    with pytest.raises(SystemExit):
        daemon.run()
    assert calls["n"] >= 3


# ---------------------------------------------------------------- prioridade por especificidade

def test_especifico_roda_primeiro_e_passa_ao_generico():
    es = make([{"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "tempo": "1h"},
               {"nome": "resto", "local": "/tmp/r.mp4", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    # segunda: específico (0-1h), depois o genérico (1-2h), depois o default
    assert config.resolve_active(es, datetime(2026, 8, 17, 0, 30))["nome"] == "segunda"
    assert config.resolve_active(es, datetime(2026, 8, 17, 1, 30))["nome"] == "resto"
    assert config.resolve_active(es, datetime(2026, 8, 17, 2, 30))["nome"] == "d"
    # terça: sem item de segunda, só o genérico e o default
    assert config.resolve_active(es, datetime(2026, 8, 18, 0, 30))["nome"] == "resto"
    assert config.resolve_active(es, datetime(2026, 8, 18, 1, 30))["nome"] == "d"


def test_especifico_em_loop_nao_passa_ao_generico():
    # vídeo com loop trava o playback (sem tempo — loop+tempo é erro)
    es = make([{"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "loop": True},
               {"nome": "resto", "local": "/tmp/r.mp4", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    # segunda: específico em loop -> nunca passa ao genérico
    assert config.resolve_active(es, datetime(2026, 8, 17, 0, 30))["nome"] == "segunda"
    assert config.resolve_active(es, datetime(2026, 8, 17, 5, 30))["nome"] == "segunda"
    # terça: loop de segunda some, genérico roda
    assert config.resolve_active(es, datetime(2026, 8, 18, 0, 30))["nome"] == "resto"


def test_default_mais_especifico_vence_o_global():
    es = make([{"nome": "d_seg", "local": "/tmp/ds.mp4", "dia": "seg", "default": True},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    # segunda: default do dia vence o global
    assert config.resolve_active(es, datetime(2026, 8, 17, 0, 30))["nome"] == "d_seg"
    # terça: só o global
    assert config.resolve_active(es, datetime(2026, 8, 18, 0, 30))["nome"] == "d"


def test_data_vence_weekday():
    es = make([{"nome": "dia20", "local": "/tmp/x.mp4", "dia": "20-12-2026", "tempo": "1h"},
               {"nome": "domingo", "local": "/tmp/dom.mp4", "dia": "dom", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    # 2026-12-20 é domingo: a data específica vence o weekday
    assert config.resolve_active(es, datetime(2026, 12, 20, 0, 30))["nome"] == "dia20"
    assert config.resolve_active(es, datetime(2026, 12, 20, 1, 30))["nome"] == "domingo"
    # outro domingo: só o weekday
    assert config.resolve_active(es, datetime(2026, 12, 27, 0, 30))["nome"] == "domingo"


def test_next_transition_cascata_dias():
    es = make([{"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "tempo": "1h"},
               {"nome": "resto", "local": "/tmp/r.mp4", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    # segunda: 1h (específico) -> 2h (genérico) -> default
    assert config.next_transition(es, datetime(2026, 8, 17, 0, 30)) == datetime(2026, 8, 17, 1)
    assert config.next_transition(es, datetime(2026, 8, 17, 1, 30)) == datetime(2026, 8, 17, 2)
    # terça: só genérico
    assert config.next_transition(es, datetime(2026, 8, 18, 0, 30)) == datetime(2026, 8, 18, 1)


def test_next_entry_segue_a_ordem_do_dia():
    es = make([{"nome": "resto", "local": "/tmp/r.mp4", "tempo": "1h"},
               {"nome": "segunda", "local": "/tmp/s.mp4", "dia": "seg", "tempo": "1h"},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    # segunda: ciclo na ordem do dia (específico primeiro, depois genérico, depois default)
    ativo = config.resolve_active(es, datetime(2026, 8, 17, 0, 30))
    assert config.next_entry(es, ativo, datetime(2026, 8, 17, 0, 30))["nome"] == "resto"


# ---------------------------------------------------------------- -a exige default global

def test_check_global_default_falta():
    with pytest.raises(ValueError):
        config.check_global_default(make([{"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h"}]))


def test_check_global_default_so_um():
    es = make([{"nome": "d", "local": "/tmp/d.mp4", "default": True},
               {"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h"}])
    config.check_global_default(es)


def test_check_global_default_mais_de_um():
    es = make([{"nome": "d", "local": "/tmp/d.mp4", "default": True},
               {"nome": "e", "local": "/tmp/e.mp4", "default": True}])
    with pytest.raises(ValueError):
        config.check_global_default(es)


def test_default_com_dia_nao_conta_como_global():
    es = make([{"nome": "d_seg", "local": "/tmp/ds.mp4", "dia": "seg", "default": True},
               {"nome": "d", "local": "/tmp/d.mp4", "default": True}])
    config.check_global_default(es)


def test_a_sem_default_global_sai_limpo(monkeypatch, capsys):
    import sys

    import wallpha
    monkeypatch.setattr(sys, "argv", ["wallpha", "-a"])
    import wallpha.entries as entries_mod2
    monkeypatch.setattr(entries_mod2, "load", lambda *a, **kw: entries_mod2.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h"}]))
    monkeypatch.setattr(config, "load", lambda *a, **kw: config.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h"}]))
    with pytest.raises(SystemExit) as ex:
        wallpha.main()
    assert ex.value.code == 1
    assert "default global" in capsys.readouterr().err


def test_a_nome_sem_default_global_sai_limpo(monkeypatch, capsys):
    import sys

    import wallpha
    monkeypatch.setattr(sys, "argv", ["wallpha", "-a", "x"])
    import wallpha.entries as entries_mod3
    monkeypatch.setattr(entries_mod3, "load", lambda *a, **kw: entries_mod3.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h"}]))
    monkeypatch.setattr(config, "load", lambda *a, **kw: config.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h"}]))
    with pytest.raises(SystemExit) as ex:
        wallpha.main()
    assert ex.value.code == 1
    assert "default global" in capsys.readouterr().err


def test_a_com_default_global_passa(monkeypatch, capsys):
    import sys

    import wallpha
    monkeypatch.setattr(sys, "argv", ["wallpha", "-a"])
    import wallpha.entries as entries_mod4
    monkeypatch.setattr(entries_mod4, "load", lambda *a, **kw: entries_mod4.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h"},
         {"nome": "d", "local": "/tmp/d.mp4", "default": True}]))
    monkeypatch.setattr(config, "load", lambda *a, **kw: config.load_entries(
        [{"nome": "x", "local": "/tmp/x.mp4", "tempo": "1h"},
         {"nome": "d", "local": "/tmp/d.mp4", "default": True}]))
    monkeypatch.setattr(wallpha, "_start_service", lambda: None)
    from wallpha import state as st
    monkeypatch.setattr(st, "clear_list", lambda: None)
    monkeypatch.setattr(st, "clear_random", lambda: None)
    monkeypatch.setattr(st, "set_on", lambda v: None)
    wallpha.main()  # não deve levantar SystemExit


# ---------------------------------------------------------------- listas aninhadas + herança de dia

def test_lista_aninhada_unidade(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = make([{"nome": "pai", "tempo": "2h", "list": [
        {"nome": "filha", "tempo": "1h", "list": [
            {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
            {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
        ]},
        {"nome": "outro", "local": str(tmp_path / "b.mp4"), "tempo": "1h"},
    ]}])
    # 0h-1h dentro da sub-lista "filha" (a 0-30m, b 30-60m); 1h-2h "outro"
    assert config.resolve_active(es, datetime(2026, 8, 18, 0, 10))["sub_nome"] == "filha/a"
    assert config.resolve_active(es, datetime(2026, 8, 18, 0, 40))["sub_nome"] == "filha/b"
    assert config.resolve_active(es, datetime(2026, 8, 18, 1, 10))["sub_nome"] == "outro"


def test_lista_sub_herda_dia_do_pai(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = make([{"nome": "fim de semana", "dia": "sab", "tempo": "2h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "1h"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "1h"},
    ]}])
    assert config.resolve_active(es, SAB.replace(hour=0, minute=30))["sub_nome"] == "a"
    assert config.resolve_active(es, SAB.replace(hour=1, minute=30))["sub_nome"] == "b"
    assert config.resolve_active(es, DOM.replace(hour=0, minute=30)) is None


def test_sub_com_dia_proprio_vence_heranca(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = make([{"nome": "fim de semana", "dia": "sab", "tempo": "2h", "list": [
        {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "1h", "dia": "seg"},
        {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "1h"},
    ]}])
    # sábado: "a" (dia seg) é pulado; "b" (herdado sab) preenche
    assert config.resolve_active(es, SAB.replace(hour=0, minute=30))["sub_nome"] == "b"
    assert config.resolve_active(es, SAB.replace(hour=1, minute=30))["sub_nome"] == "b"


def test_lista_aninhada_agrupamento_achata(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = make([{"nome": "pai", "list": [
        {"nome": "grupo", "list": [
            {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "1h"},
            {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "1h"},
        ]},
    ]}])
    # agrupamentos aninhados achatam: os subs entram direto na agenda
    assert [e["nome"] for e in es] == ["a", "b"]


def test_next_transition_lista_aninhada(tmp_path):
    a = mk(tmp_path, "a.mp4", "b.mp4")
    es = make([{"nome": "pai", "hora": "8h-10h", "list": [
        {"nome": "filha", "tempo": "1h", "list": [
            {"nome": "a", "local": str(tmp_path / "a.mp4"), "tempo": "30m"},
            {"nome": "b", "local": str(tmp_path / "b.mp4"), "tempo": "30m"},
        ]},
    ]}])
    base = datetime(2026, 8, 18, 8)
    assert config.next_transition(es, base + timedelta(minutes=10)) == base + timedelta(minutes=30)
    assert config.next_transition(es, base + timedelta(minutes=40)) == base + timedelta(minutes=60)