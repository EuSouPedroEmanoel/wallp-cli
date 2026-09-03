import json
import sys
from datetime import date

import pytest

from wallpha import cli, config, state


# ---------------------------------------------------------------- shuffle diário

def test_day_shuffled_determinismo_e_permutacao():
    files = [f"f{i}.mp4" for i in range(10)]
    a = config.day_shuffled(files, salt="abc", day=date(2026, 1, 1))
    b = config.day_shuffled(files, salt="abc", day=date(2026, 1, 1))
    assert a == b
    assert sorted(a) == sorted(files)


def test_day_shuffled_muda_por_dia_e_por_salt():
    files = [f"f{i}.mp4" for i in range(10)]
    d1 = config.day_shuffled(files, salt="abc", day=date(2026, 1, 1))
    d2 = config.day_shuffled(files, salt="abc", day=date(2026, 1, 2))
    s2 = config.day_shuffled(files, salt="xyz", day=date(2026, 1, 1))
    assert d1 != d2
    assert d1 != s2


def test_get_salt_cria_e_reusa(tmp_path):
    import wallpha.paths as paths
    import wallpha.media as media
    paths.SALT_FILE = tmp_path / "shuffle.json"
    media.SALT_FILE = tmp_path / "shuffle.json"
    config.SALT_FILE = tmp_path / "shuffle.json"
    salt1 = config.get_salt()
    salt2 = config.get_salt()
    assert salt1 == salt2
    assert json.loads((tmp_path / "shuffle.json").read_text())["salt"] == salt1


# ---------------------------------------------------------------- varredura

def test_list_tree_files_recursivo(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "sub").mkdir()
    (tmp_path / "a" / "1.png").write_bytes(b"")
    (tmp_path / "a" / "sub" / "2.mp4").write_bytes(b"")
    (tmp_path / "nota.txt").write_bytes(b"")
    (tmp_path / "a" / ".oculto.png").write_bytes(b"")
    (tmp_path / "a" / ".h").mkdir()
    (tmp_path / "a" / ".h" / "x.png").write_bytes(b"")
    out = config.list_tree_files(str(tmp_path))
    assert len(out) == 2
    assert any(f.endswith("1.png") for f in out)
    assert any(f.endswith(os_sep("2.mp4")) for f in out)


def os_sep(name):
    import os

    return os.path.join("sub", name)


# ---------------------------------------------------------------- shuffled no yml

def test_normalize_shuffled(tmp_path):
    import wallpha.paths as paths
    import wallpha.media as media
    paths.SALT_FILE = tmp_path / "shuffle.json"
    media.SALT_FILE = tmp_path / "shuffle.json"
    config.SALT_FILE = tmp_path / "shuffle.json" 
    (tmp_path / "b.mp4").write_bytes(b"")
    (tmp_path / "a.mp4").write_bytes(b"")
    (tmp_path / "c.mp4").write_bytes(b"")
    base = sorted(config.list_dir_files(str(tmp_path)))
    e = config.load_entries(
        [{"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m", "shuffled": True}]
    )[0]
    assert e["shuffled"] is True
    assert sorted(e["files"]) == base
    assert e["arquivo"] == e["files"][0]
    e2 = config.load_entries(
        [{"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m", "shuffled": True}]
    )[0]
    assert e["files"] == e2["files"]


def test_normalize_sem_shuffled_mantem_ordem(tmp_path):
    (tmp_path / "b.mp4").write_bytes(b"")
    (tmp_path / "a.mp4").write_bytes(b"")
    e = config.load_entries(
        [{"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m"}]
    )[0]
    assert e["files"] == [str(tmp_path / "a.mp4"), str(tmp_path / "b.mp4")]


# ---------------------------------------------------------------- estado random

def test_state_random(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state, "RANDOM_FILE", tmp_path / "random")
    assert state.get_random() is None
    state.set_random({"dir": None, "tempo": "30m"})
    assert state.get_random() == {"dir": None, "tempo": "30m"}
    state.clear_random()
    assert state.get_random() is None


# ---------------------------------------------------------------- limites

def test_random_boundary_quantidade():
    assert config.random_boundary(3, 0, 5, None, False, 10) == "ok"
    assert config.random_boundary(5, 0, 5, None, False, 10) == "end"


def test_random_boundary_tempo_max():
    assert config.random_boundary(1, 50, None, 60, False, 10) == "ok"
    assert config.random_boundary(1, 60, None, 60, False, 10) == "end"


def test_random_boundary_fim_da_lista():
    assert config.random_boundary(10, 0, None, None, False, 10) == "end"
    assert config.random_boundary(9, 0, None, None, False, 10) == "ok"


def test_random_boundary_loop_reinicia():
    assert config.random_boundary(10, 999, None, None, True, 10) == "loop"
    assert config.random_boundary(5, 999, 5, 60, True, 10) == "ok"


# ---------------------------------------------------------------- cli.parse

def test_parse_n(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-n"])
    o = cli.parse()
    assert o["next"] and o["change"] is False


def test_parse_log(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-log"])
    o = cli.parse()
    assert o["log"] is True and o["log_lines"] is None


def test_parse_log_com_a(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-a", "Pokemon", "-log", "10"])
    o = cli.parse()
    assert o["auto"] and o["target"] == "Pokemon" and o["log"] is True and o["log_lines"] == 10


def test_parse_log_valor(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-log", "10"])
    o = cli.parse()
    assert o["log"] is True and o["log_lines"] == 10


def test_parse_n_com_target_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-n", "celeste"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_c_n_juntos_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-c", "-n"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_r_m_q_l(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "~/x", "-t", "30m", "-m", "2h", "-q", "10", "-l", "true"])
    o = cli.parse()
    assert o["random"] and o["tempo"] == "30m" and o["max"] == "2h"
    assert o["qtd"] == "10" and o["loop"] == "true"


def test_parse_valores_sem_r_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-n", "-q", "3"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_c_aceita_valores(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-c", "lista", "-t", "30m", "-q", "3"])
    o = cli.parse()
    assert o["change"] and o["tempo"] == "30m" and o["qtd"] == "3"


def test_parse_a_nao_aceita_valores(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-a", "-q", "3"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_valor_sem_valor_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-l"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_r_sem_t(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r"])
    o = cli.parse()
    assert o["random"] and o["target"] is None and o["tempo"] is None


def test_parse_t_sem_r_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-n", "-t", "30m"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_dois_modos_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-a"])
    with pytest.raises(SystemExit):
        cli.parse()


# ---------------------------------------------------------------- próximo

def test_next_after_cicla():
    es = config.load_entries([{"nome": "a", "local": "/tmp/a.mp4", "tempo": "1h"},
                              {"nome": "b", "local": "/tmp/b.mp4", "tempo": "1h"},
                              {"nome": "c", "local": "/tmp/c.mp4", "tempo": "1h"}])
    assert config.next_after(es, ["/tmp/a.mp4", "a"])["nome"] == "b"
    assert config.next_after(es, ["/tmp/c.mp4", "c"])["nome"] == "a"
    assert config.next_after(es, ["/tmp/zz.mp4", "x"]) is None
    assert config.next_after([], ["/tmp/a.mp4", "a"]) is None


def test_next_after_distingue_local_repetido():
    es = config.load_entries([{"nome": "outro", "local": "/tmp/sem.mp4", "tempo": "1h"},
                              {"nome": "padrao", "local": "/tmp/sem.mp4", "default": True}])
    assert config.next_after(es, ["/tmp/sem.mp4", "outro"])["nome"] == "padrao"
    assert config.next_after(es, ["/tmp/sem.mp4", "padrao"])["nome"] == "outro"


def test_state_last(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state, "LAST_FILE", tmp_path / "last")
    assert state.get_last() is None
    state.set_last(["/tmp/a.mp4", "a"])
    assert state.get_last() == ["/tmp/a.mp4", "a"]


def test_state_override(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state, "OVERRIDE_FILE", tmp_path / "override")
    assert state.get_override() is None
    cfg = {"key": ["/tmp/a.mp4", "a", "/tmp/a.mp4"], "until": "2026-08-18T10:00:00"}
    state.set_override(cfg)
    assert state.get_override() == cfg
    state.clear_override()
    assert state.get_override() is None


def test_state_pos(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setattr(state, "POS_FILE", tmp_path / "pos")
    assert state.get_pos() is None
    state.set_pos({"idx": 3, "day": "2026-01-01", "salt": "x", "dir": None})
    assert state.get_pos() == {"idx": 3, "day": "2026-01-01", "salt": "x", "dir": None}
    state.clear_pos()
    assert state.get_pos() is None


# ---------------------------------------------------------------- repetir (-rep / yml)

def test_parse_r_rep(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-rep", "-t", "10s"])
    o = cli.parse()
    assert o["random"] and o["rep"] is True


def test_parse_rep_sem_r_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-n", "-rep"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_normalize_repetir(tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"")
    e = config.load_entries(
        [{"nome": "x", "type": "arquivo", "local": str(tmp_path / "v.mp4"), "tempo": "10m", "repetir": True}]
    )[0]
    assert e["repetir"] is True
    e2 = config.load_entries(
        [{"nome": "y", "type": "arquivo", "local": str(tmp_path / "v.mp4"), "tempo": "10m", "repeat": True}]
    )[0]
    assert e2["repetir"] is True
    e3 = config.load_entries(
        [{"nome": "z", "type": "arquivo", "local": str(tmp_path / "v.mp4"), "tempo": "10m"}]
    )[0]
    assert e3["repetir"] is False


def test_format_entry_repetir(tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"")
    e = config.load_entries(
        [{"nome": "x", "type": "arquivo", "local": str(tmp_path / "v.mp4"), "tempo": "10m", "repetir": True}]
    )[0]
    assert ", repetir" in config.format_entry(e)


# ---------------------------------------------------------------- advance_in_dir

def test_advance_in_dir_cicla(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"")
    (tmp_path / "b.mp4").write_bytes(b"")
    (tmp_path / "c.mp4").write_bytes(b"")
    e = config.load_entries(
        [{"nome": "dir", "type": "diretório", "local": str(tmp_path), "tempo": "10m"}]
    )[0]
    files = e["files"]
    assert config.advance_in_dir(e, files[0]) == files[1]
    assert config.advance_in_dir(e, files[1]) == files[2]
    assert config.advance_in_dir(e, files[2]) == files[0]
    assert config.advance_in_dir(e, None) == files[0]
    assert config.advance_in_dir(e, "/tmp/inexistente.mp4") == files[0]


# ---------------------------------------------------------------- video params loop

def test_video_params_loop():
    from wallpha import apply as _apply

    uri = "file:///tmp/v.mp4"
    p = _apply._video_params(uri, loop=True)
    assert json.loads(p["VideoUrls"])[0]["loop"] is True
    p2 = _apply._video_params(uri, loop=False)
    assert json.loads(p2["VideoUrls"])[0]["loop"] is False


def test_video_params_som_integro():
    from wallpha import apply as _apply

    p = _apply._video_params("file:///tmp/v.mp4", som=True, integro=False)
    assert p["MuteMode"] == 4 and p["Volume"] == 1.0 and "ChangeWallpaperMode" not in p
    p2 = _apply._video_params("file:///tmp/v.mp4", som=False, integro=False)
    assert p2["MuteMode"] == 5
    p3 = _apply._video_params("file:///tmp/v.mp4", som=True, integro=True)
    assert p3["MuteMode"] == 4 and p3["ChangeWallpaperMode"] == 1


# ---------------------------------------------------------------- -i / -v / -int / -s

def test_parse_i_v_int_s(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-i", "-s", "on", "-t", "10s"])
    o = cli.parse()
    assert o["images"] and not o["videos"] and o["som"] == "on"
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-v", "-int"])
    o = cli.parse()
    assert o["videos"] and o["integro"]
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-s", "off"])
    o = cli.parse()
    assert o["som"] == "off"


def test_parse_i_v_juntos_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-i", "-v"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_int_sem_v_ok(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-int"])
    o = cli.parse()
    assert o["integro"] and not o["videos"]
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-i", "-int"])
    o = cli.parse()
    assert o["integro"] and o["images"]


def test_parse_int_com_t_ok(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-v", "-int", "-t", "1m"])
    o = cli.parse()
    assert o["integro"] and o["tempo"] == "1m"


def test_parse_int_com_rep_ok(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-v", "-int", "-rep"])
    o = cli.parse()
    assert o["integro"] and o["rep"]


def test_parse_s_invalido_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-r", "-s", "alto"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_valores_novos_sem_r_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-n", "-v"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_parse_y_implica_random(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-y", "https://youtu.be/abc", "-t", "30m", "-s", "on", "-l", "true"])
    o = cli.parse()
    assert o["random"] and o["yt"] == "https://youtu.be/abc"
    assert o["tempo"] == "30m" and o["som"] == "on" and o["loop"] == "true"


def test_parse_y_sem_valor_erro(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["wallpha", "-y"])
    with pytest.raises(SystemExit):
        cli.parse()


def test_build_random_queue_file(tmp_path):
    (tmp_path / "solo.mp4").write_bytes(b"")
    (tmp_path / "outro.mp4").write_bytes(b"")
    _, files, err = config.build_random_queue({"file": str(tmp_path / "solo.mp4")})
    assert err is None and files == [str(tmp_path / "solo.mp4")]
    _, files2, err2 = config.build_random_queue({"file": str(tmp_path / "nao-existe.mp4")})
    assert err2 is not None and files2 is None


def test_match_tipo():
    assert config.match_tipo("/tmp/x.png", "imagem") is True
    assert config.match_tipo("/tmp/x.png", "video") is False
    assert config.match_tipo("/tmp/x.mp4", "video") is True
    assert config.match_tipo("/tmp/x.mp4", None) is True


def test_build_random_queue_tipo(tmp_path):
    (tmp_path / "a.png").write_bytes(b"")
    (tmp_path / "b.mp4").write_bytes(b"")
    _, files_img, err = config.build_random_queue({"dir": str(tmp_path), "tipo": "imagem"})
    assert err is None and len(files_img) == 1 and files_img[0].endswith(".png")
    _, files_vid, err = config.build_random_queue({"dir": str(tmp_path), "tipo": "video"})
    assert err is None and len(files_vid) == 1 and files_vid[0].endswith(".mp4")


def test_video_duration_ffprobe(monkeypatch):
    calls = {}

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd
        import subprocess as sp

        class R:
            stdout = "12.5\n"

        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    assert config.video_duration("/tmp/x.mp4") == 12.5


def test_video_duration_falha(monkeypatch):
    import subprocess as sp

    def fake_run(cmd, **kw):
        raise sp.TimeoutExpired(cmd, 15)

    monkeypatch.setattr("subprocess.run", fake_run)
    assert config.video_duration("/tmp/x.mp4", fallback=99) == 99


# ---------------------------------------------------------------- som / integro no yml

def test_normalize_som_integro(tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"")
    e = config.load_entries(
        [{"nome": "x", "type": "arquivo", "local": str(tmp_path / "v.mp4"), "tempo": "10m", "som": True, "integro": True}]
    )[0]
    assert e["som"] is True and e["integro"] is True
    e2 = config.load_entries(
        [{"nome": "y", "type": "arquivo", "local": str(tmp_path / "v.mp4"), "tempo": "10m", "sound": True, "integrado": True}]
    )[0]
    assert e2["som"] is True and e2["integro"] is True


def test_normalize_integro_dir_sem_tempo(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"")
    (tmp_path / "b.mp4").write_bytes(b"")
    e = config.load_entries(
        [{"nome": "d", "type": "diretório", "local": str(tmp_path), "integro": True}]
    )[0]
    assert e["integro"] is True and e["tempo"] is None
    assert len(e["files"]) == 2


def test_normalize_integro_rep_juntos_ok(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"")
    e = config.load_entries(
        [{"nome": "d", "type": "arquivo", "local": str(tmp_path / "a.mp4"), "tempo": "10m", "integro": True, "repetir": True}]
    )[0]
    assert e["integro"] is True and e["repetir"] is True


def test_format_entry_som_integro(tmp_path):
    (tmp_path / "v.mp4").write_bytes(b"")
    e = config.load_entries(
        [{"nome": "x", "type": "arquivo", "local": str(tmp_path / "v.mp4"), "tempo": "10m", "som": True, "integro": True}]
    )[0]
    out = config.format_entry(e)
    assert ", som" in out and ", integro" in out


def test_normalize_youtube_url_intacto():
    e = config.load_entries(
        [{"nome": "yt1", "type": "youtube", "local": "https://youtu.be/abc", "tempo": "10m"}]
    )[0]
    assert e["is_yt"] is True
    assert e["local"] == "https://youtu.be/abc"
    assert e["arquivo"] == "https://youtu.be/abc"
    assert "https://youtu.be/abc" in config.format_entry(e)


def test_normalize_youtube_sem_hora_tempo_erro():
    with pytest.raises(ValueError):
        config.load_entries(
            [{"nome": "yt1", "type": "youtube", "local": "https://youtu.be/abc"}]
        )
