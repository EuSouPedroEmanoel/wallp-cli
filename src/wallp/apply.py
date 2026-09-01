import json
from pathlib import Path

PLUGIN_VIDEO = "luisbocanegra.smart.video.wallpaper.reborn"
PLUGIN_IMAGE = "org.kde.image"

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mpeg", ".mpg", ".ogg", ".ogv"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".avif"}


def _iface():
    import dbus

    bus = dbus.SessionBus()
    proxy = bus.get_object("org.kde.plasmashell", "/PlasmaShell")
    return dbus.Interface(proxy, "org.kde.PlasmaShell")


def _screens(iface):
    import dbus

    screens = []
    for n in range(0, 10):
        cur = iface.wallpaper(dbus.UInt32(n))
        if not cur:
            break
        screens.append(n)
    return screens


def plugin_for(path):
    ext = Path(path).suffix.lower()
    if ext in VIDEO_EXTS:
        return PLUGIN_VIDEO
    return PLUGIN_IMAGE


def _video_params(uri, loop=False, som=False, integro=False):
    video = {
        "filename": uri,
        "enabled": True,
        "duration": 0,
        "customDuration": 0,
        "playbackRate": 0,
        "alternativePlaybackRate": 0,
        "loop": bool(loop),
    }
    params = {
        "VideoUrls": json.dumps([video], ensure_ascii=False),
        "LastVideo": uri,
        "LastVideoPosition": 0,
        "ResumeLastVideo": True,
        "MuteMode": 4 if som else 5,
        "Volume": 1.0,
    }
    if integro:
        params["ChangeWallpaperMode"] = 1
    return params


def apply(path, screen=None, loop=False, som=False, integro=False):
    import dbus

    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"arquivo não encontrado: {p}")
    uri = p.as_uri()
    plugin = plugin_for(p)
    if plugin == PLUGIN_VIDEO:
        params = _video_params(uri, loop=loop, som=som, integro=integro)
    else:
        params = {"Image": uri}

    iface = _iface()
    screens = [screen] if screen is not None else _screens(iface)
    if not screens:
        raise RuntimeError("nenhuma tela de desktop encontrada (plasmashell rodando?)")

    for n in screens:
        cur = iface.wallpaper(dbus.UInt32(n))
        merged = dict(cur) if cur else {}
        merged.update(params)
        iface.setWallpaper(plugin, merged, dbus.UInt32(n))
    return plugin, p