# LEGADO: canônico migrado para wallp-plasma/src/wallp/daemon.py
# Este shim mantém compatibilidade: delega para wallp-plasma se instalado, senão roda fallback local.
import sys
import time
from pathlib import Path

_plasma_src = Path.home() / "dev/wallp/wallp-plasma/src"
if _plasma_src.is_dir() and str(_plasma_src) not in sys.path:
    # tenta priorizar wallp-plasma para `wallp -d` via __init__.py execv; aqui só para testes/import
    pass

from . import apply, log, state
from .daemon_list import _run_list, _run_list_cycle, _run_list_schedule, _run_list_slideshow
from .daemon_random import _run_random
from .daemon_schedule import _run_schedule

# compat for old tests that patch daemon.config / daemon.time / daemon._run_schedule etc.
import wallp.config as config

POLL = 15


def run():
    # se wallp-plasma estiver instalado e não for este arquivo, __init__.py já fez execv;
    # este fallback roda o daemon legado (mantido para testes sem wallp-plasma)
    if not state.is_on():
        log.err("modo automático desativado, encerrando.")
        sys.exit(0)

    if state.get_random():
        if _run_random():
            state.clear_random()
            log.err("slideshow encerrado, voltando à agenda do yml.")

    if state.get_list():
        _run_list()
        return

    if state.get_random() is None:
        _run_schedule()
