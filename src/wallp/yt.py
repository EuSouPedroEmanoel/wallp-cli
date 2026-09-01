import os
import re
import subprocess
from pathlib import Path

from .media import VIDEO_EXTS, WALLP_EXTS
from .media import day_shuffled, get_salt

YT_CACHE_MB = int(os.environ.get("WALLP_YT_CACHE_MB", "500"))


def _cache_bytes():
    try:
        return int(os.environ.get("WALLP_YT_CACHE_MB", str(YT_CACHE_MB))) * 1024 * 1024
    except ValueError:
        return YT_CACHE_MB * 1024 * 1024


def yt_dir():
    """Diretório do buffer do -y/youtube: tmpfs em RAM, limpo pelo sistema no logout.
    Limite de 500 MiB (YT_CACHE_MB) com limpeza LRU após cada download; `wallp -x cache`
    limpa só o buffer sem tocar no daemon."""
    base = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    d = Path(base) / "wallp"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return d


def clean_yt_buffer(keep=None):
    """Limpeza LRU por mtime do buffer do YouTube.
    Mantém `keep` (arquivo recém-baixado) e os mais recentes que caibam em YT_CACHE_MB;
    apaga o resto. Falha de download não limpa. Unlink de arquivo aberto é seguro no Linux.
    Se `keep` for diretório, mantém todos os arquivos dentro dele.
    Sem `keep`, esvazia o buffer inteiro (usado por `wallp -x` e `wallp -x cache`)."""
    try:
        yt = yt_dir()
        if not yt.is_dir():
            return
        # Sem keep -> esvazia tudo (para -x e -x cache)
        if keep is None:
            for p in yt.rglob("*"):
                if p.is_file():
                    try:
                        p.unlink()
                    except OSError:
                        pass
            for d in sorted([p for p in yt.rglob("*") if p.is_dir()], reverse=True):
                try:
                    if not any(d.iterdir()):
                        d.rmdir()
                except OSError:
                    pass
            return

        limit = _cache_bytes()
        files = [p for p in yt.rglob("*") if p.is_file() and p.suffix.lower() in WALLP_EXTS]
        try:
            files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError:
            return

        keep_path = Path(keep).resolve() if keep is not None else None
        keep_files = set()
        if keep_path is not None:
            try:
                if keep_path.is_dir():
                    keep_files = {p.resolve() for p in keep_path.rglob("*") if p.is_file()}
                elif keep_path.is_file():
                    keep_files = {keep_path.resolve()}
                else:
                    keep_files = {keep_path.resolve()}
            except OSError:
                keep_files = set()

        if keep_path is not None and keep_path.is_file() and keep_path.resolve() not in {f.resolve() for f in files}:
            try:
                files.insert(0, keep_path)
            except OSError:
                pass

        kept = set()
        total = 0
        if keep_files:
            for kf in keep_files:
                try:
                    if kf.is_file():
                        sz = kf.stat().st_size
                    else:
                        continue
                    kept.add(kf)
                    total += sz
                except OSError:
                    pass
        for f in files:
            rf = f.resolve()
            if rf in kept:
                continue
            try:
                sz = f.stat().st_size
            except OSError:
                continue
            if total + sz <= limit:
                kept.add(rf)
                total += sz

        for f in files:
            rf = f.resolve()
            if rf in kept:
                continue
            try:
                f.unlink()
            except OSError:
                pass

        for d in sorted([p for p in yt.rglob("*") if p.is_dir()], reverse=True):
            try:
                if not any(d.iterdir()):
                    d.rmdir()
            except OSError:
                pass

    except Exception:
        pass


def _prune_yt_cache(limit_bytes=None):
    """Compat: antigo nome, delega para clean_yt_buffer."""
    clean_yt_buffer()


def _extract_playlist_id(url):
    m = re.search(r"[?&]list=([^&]+)", url)
    return m.group(1) if m else None


def get_playlist_ids(url):
    """Retorna lista de IDs da playlist sem baixar vídeos (usado para shuffle sem download)."""
    r = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print", "%(id)s", "--yes-playlist", url],
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "falha ao listar playlist").strip())
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def _get_shuffled_playlist_ids(url):
    """Obtém IDs da playlist via --flat-playlist e retorna embaralhados por dia (sem baixar vídeos)."""
    ids = get_playlist_ids(url)
    return day_shuffled(ids, get_salt())


def download_yt(url, batch_size=7):
    """Baixa um vídeo do YouTube pro buffer em RAM e devolve o caminho local.
    Se a URL contiver playlist (list=), prepara fila embaralhada sem baixar tudo (sem download) — baixa sob demanda com LRU.
    Limite de 500 MiB (YT_CACHE_MB) com limpeza LRU após cada download bem-sucedido; falha não limpa.
    `wallp -x cache` limpa só o buffer; `wallp -x` esvazia tudo."""
    is_playlist = "list=" in url.lower()
    if is_playlist:
        playlist_id = _extract_playlist_id(url) or "playlist"
        folder = yt_dir() / playlist_id
        folder.mkdir(parents=True, exist_ok=True)
        marker = folder / ".playlist_url"
        try:
            marker.write_text(url, encoding="utf-8")
        except OSError:
            pass
        existing = len([p for p in folder.glob("*.mp4")] + [p for p in folder.glob("*.webm")] + [p for p in folder.glob("*.mkv")])
        if existing == 0:
            tpl = str(folder / "%(id)s.%(ext)s")
            args = [
                "yt-dlp",
                "--yes-playlist",
                "--playlist-items",
                f"1:{batch_size}",
                "--extractor-args",
                "youtube:player_client=android",
                "-o",
                tpl,
                "--print",
                "after_move:filepath",
                url,
            ]
            r = subprocess.run(args, capture_output=True, text=True, timeout=600)
            if r.returncode == 0:
                try:
                    files = sorted(folder.glob("*"), key=lambda p: p.stat().st_mtime if p.is_file() else 0)
                    keep = str(files[-1]) if files else str(folder)
                except OSError:
                    keep = str(folder)
                # só limpa em sucesso
                try:
                    clean_yt_buffer(keep=keep)
                except Exception:
                    pass
            elif r.returncode != 0:
                # falha não limpa; se já tem arquivos retorna pasta, senão erro
                if folder.is_dir() and any(folder.iterdir()):
                    return str(folder)
                raise RuntimeError((r.stderr or r.stdout or "falha ao baixar o vídeo").strip())
        return str(folder)
    # vídeo único (sem playlist)
    tpl = str(yt_dir() / "%(id)s.%(ext)s")
    args = [
        "yt-dlp",
        "--no-playlist",
        "--extractor-args",
        "youtube:player_client=android",
        "-o",
        tpl,
        "--print",
        "after_move:filepath",
        url,
    ]
    r = subprocess.run(
        args,
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "falha ao baixar o vídeo").strip())
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("não consegui localizar o vídeo baixado")
    path = lines[-1].strip()
    if not path or not Path(path).is_file():
        raise RuntimeError("não consegui localizar o vídeo baixado")
    clean_yt_buffer(keep=path)
    return path
