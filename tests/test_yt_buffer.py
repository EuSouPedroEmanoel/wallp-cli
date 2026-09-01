import os
import time
import sys
from pathlib import Path

import pytest

import wallp.yt as yt
from wallp import state
import wallp


def make_file(path, size, mtime=None):
    # cria arquivo com tamanho size (sparse via truncate para ser rápido)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        if size > 0:
            f.truncate(size)
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def test_clean_yt_buffer_mantem_keep_e_recentes(tmp_path, monkeypatch):
    # fake yt_dir
    monkeypatch.setattr(yt, "yt_dir", lambda: tmp_path)
    # usa limite pequeno 1 MB para testar com arquivos pequenos
    monkeypatch.setenv("WALLP_YT_CACHE_MB", "1")
    # limpa
    # cria 3 arquivos: antigo 600KB, medio 600KB, novo 600KB (total 1.8MB >1MB)
    # keep = novo, deve manter novo (600KB) + um dos recentes que ainda cabe (600KB) = 1.2MB mas over? Actually limit 1MB, keep entra sempre (600KB), sobra 400KB, nenhum outro cabe (600KB>400KB) então só keep fica
    # Para testar LRU mais preciso: cria arquivos de 400KB cada, total 1.2MB, keep 400KB, sobra 600KB, pode manter 1 extra
    # Vamos criar 3 arquivos de 400KB cada
    now = time.time()
    f_old = make_file(tmp_path / "old.mp4", 400 * 1024, now - 300)
    f_mid = make_file(tmp_path / "mid.mp4", 400 * 1024, now - 200)
    f_new = make_file(tmp_path / "new.mp4", 400 * 1024, now - 100)
    # keep = new, deve manter new + mid (mais recente que old), old deve ser apagado (pois new+mid=800KB <1MB, new+mid+old=1.2MB >1MB)
    yt.clean_yt_buffer(keep=str(f_new))
    assert f_new.exists()
    assert f_mid.exists()
    assert not f_old.exists()
    # agora testa que keep sempre fica mesmo estourando: cria arquivo gigante 2MB como keep, com limite 1MB, deve manter só ele
    f_big = make_file(tmp_path / "big.mp4", 2 * 1024 * 1024, now)
    # limpa com keep=big, mesmo com outros arquivos existentes (mid ainda existe 400KB, new 400KB)
    # total keep 2MB já estoura, mas keep entra sempre, então os outros devem ser apagados
    yt.clean_yt_buffer(keep=str(f_big))
    assert f_big.exists()
    assert not f_mid.exists()
    assert not f_new.exists()


def test_clean_yt_buffer_lru_sem_keep_esvazia(tmp_path, monkeypatch):
    monkeypatch.setattr(yt, "yt_dir", lambda: tmp_path)
    monkeypatch.setenv("WALLP_YT_CACHE_MB", "500")
    f1 = make_file(tmp_path / "a.mp4", 1024)
    f2 = make_file(tmp_path / "b.mp4", 1024)
    assert f1.exists() and f2.exists()
    yt.clean_yt_buffer()
    # sem keep deve esvaziar tudo (usado por -x e -x cache)
    assert not f1.exists()
    assert not f2.exists()


def test_clean_yt_buffer_keep_dir_mantem_tudo(tmp_path, monkeypatch):
    monkeypatch.setattr(yt, "yt_dir", lambda: tmp_path)
    monkeypatch.setenv("WALLP_YT_CACHE_MB", "1")
    # cria pasta keep com 2 arquivos 400KB cada
    keep_dir = tmp_path / "keepdir"
    keep_dir.mkdir()
    f1 = make_file(keep_dir / "k1.mp4", 400 * 1024, time.time() - 50)
    f2 = make_file(keep_dir / "k2.mp4", 400 * 1024, time.time() - 40)
    # outro arquivo fora 400KB mais antigo
    f_old = make_file(tmp_path / "old.mp4", 400 * 1024, time.time() - 300)
    # keep_dir tem 800KB, limite 1MB, old não cabe (800+400>1024) deve ser apagado, mas keep_dir arquivos mantidos
    yt.clean_yt_buffer(keep=str(keep_dir))
    assert f1.exists() and f2.exists()
    assert not f_old.exists()


def test_download_yt_chama_clean_com_keep(monkeypatch, tmp_path):
    # fake yt_dir
    monkeypatch.setattr(yt, "yt_dir", lambda: tmp_path)
    monkeypatch.setenv("WALLP_YT_CACHE_MB", "1")
    # cria arquivos antigos que devem ser limpos após download
    old = make_file(tmp_path / "old.mp4", 800 * 1024, time.time() - 300)
    # fake subprocess.run para yt-dlp
    def fake_run(cmd, capture_output=False, text=False, timeout=None):
        # cria arquivo fake como se yt-dlp tivesse baixado
        fake_path = tmp_path / "abc123.mp4"
        fake_path.write_bytes(b"x" * (400 * 1024))
        class R:
            returncode = 0
            stdout = str(fake_path) + "\n"
            stderr = ""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    # chama download_yt single video
    out = yt.download_yt("https://youtu.be/abc123")
    assert Path(out).exists()
    # old deve ter sido apagado pela limpeza LRU (keep novo 400KB + old 800KB >1MB, old sai)
    assert not old.exists()
    assert Path(out).exists()

    # testa falha não limpa: fake_run que falha
    def fake_fail(cmd, capture_output=False, text=False, timeout=None):
        class R:
            returncode = 1
            stdout = ""
            stderr = "erro"
        return R()
    monkeypatch.setattr("subprocess.run", fake_fail)
    # cria outro old
    old2 = make_file(tmp_path / "old2.mp4", 100 * 1024)
    with pytest.raises(RuntimeError):
        yt.download_yt("https://youtu.be/fail")
    # old2 deve continuar existindo (falha não limpa)
    assert old2.exists()


def test_x_cache_limpa_sem_parar_daemon(tmp_path, monkeypatch):
    # fake yt_dir com arquivos
    monkeypatch.setattr(yt, "yt_dir", lambda: tmp_path)
    f1 = make_file(tmp_path / "x.mp4", 1024)
    f2 = make_file(tmp_path / "y.mp4", 1024)
    # mock state para verificar que não mexe em daemon/estado
    calls = {}
    monkeypatch.setattr(state, "is_on", lambda: True)
    monkeypatch.setattr(state, "get_random", lambda: {"dir": "/tmp"})
    monkeypatch.setattr(state, "get_list", lambda: {"nome": "lista"})
    orig_set_on = state.set_on
    monkeypatch.setattr(state, "set_on", lambda v: calls.setdefault("set_on", []).append(v))
    monkeypatch.setattr(state, "clear_random", lambda: calls.setdefault("clear_random", []).append(1))
    monkeypatch.setattr(state, "clear_list", lambda: calls.setdefault("clear_list", []).append(1))
    monkeypatch.setattr("wallp.service._stop_service", lambda: calls.setdefault("stop", []).append(1))
    # também precisa mock wallp.__init__._stop_service? Na main importamos from .service import _stop_service
    # O main usa _stop_service do service, então patch wallp.service._stop_service deve cobrir
    # Simula argv
    monkeypatch.setattr(sys, "argv", ["wallp", "-x", "cache"])
    # captura info
    import wallp.log as log
    msgs = []
    monkeypatch.setattr(log, "info", lambda m: msgs.append(m))
    wallp.main()
    # buffer vazio
    assert not f1.exists() and not f2.exists()
    # estado intacto: não chamou set_on/clear etc.
    assert "set_on" not in calls
    assert "clear_random" not in calls
    assert "clear_list" not in calls
    assert "stop" not in calls
    assert any("buffer do youtube limpo" in m for m in msgs)


def test_x_para_e_esvazia(tmp_path, monkeypatch):
    monkeypatch.setattr(yt, "yt_dir", lambda: tmp_path)
    f1 = make_file(tmp_path / "a.mp4", 1024)
    calls = {}
    monkeypatch.setattr(state, "set_on", lambda v: calls.__setitem__("set_on", v))
    monkeypatch.setattr(state, "clear_random", lambda: calls.__setitem__("clear_random", True))
    monkeypatch.setattr(state, "clear_list", lambda: calls.__setitem__("clear_list", True))
    monkeypatch.setattr("wallp.service._stop_service", lambda: calls.__setitem__("stop", True))
    # também patch yt.clean_yt_buffer para verificar chamada, mas vamos deixar real e verificar arquivo apagado
    # patch o _stop_service importado em wallp.__init__
    import wallp.service as svc
    monkeypatch.setattr(svc, "_stop_service", lambda: calls.__setitem__("stop", True))
    import wallp as w
    monkeypatch.setattr(w, "_stop_service", lambda: calls.__setitem__("stop", True))
    monkeypatch.setattr(sys, "argv", ["wallp", "-x"])
    import wallp.log as log
    msgs = []
    monkeypatch.setattr(log, "info", lambda m: msgs.append(m))
    wallp.main()
    assert calls.get("set_on") is False
    assert calls.get("clear_random") is True
    assert calls.get("clear_list") is True
    assert not f1.exists()
    # log deve mencionar buffer limpo
    assert any("buffer" in m for m in msgs)


def test_x_invalido_erro(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["wallp", "-x", "foo"])
    with pytest.raises(SystemExit) as ex:
        wallp.main()
    assert ex.value.code == 1
    # mensagem de erro deve ser "só 'cache' é aceito com -x"
    err = capsys.readouterr().err
    assert "só 'cache' é aceito com -x" in err
