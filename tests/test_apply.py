"""D-Bus payload contract for the unified Plasma wallpaper plugin."""

import json
import sys
import types

import pytest

from wallpha import apply as wallpaper_apply


class FakePlasmaShell:
    def __init__(self, wallpapers):
        self.wallpapers = wallpapers
        self.calls = []

    def wallpaper(self, screen):
        return self.wallpapers.get(int(screen))

    def setWallpaper(self, plugin, params, screen):
        self.calls.append((plugin, dict(params), int(screen)))


@pytest.fixture
def plasma(monkeypatch):
    """Provide just enough of dbus-python for apply()'s public path."""
    fake_dbus = types.SimpleNamespace(UInt32=int)
    monkeypatch.setitem(sys.modules, "dbus", fake_dbus)
    shell = FakePlasmaShell({0: {"existing": "value"}})
    monkeypatch.setattr(wallpaper_apply, "_iface", lambda: shell)
    monkeypatch.setattr(wallpaper_apply, "plugin_for", lambda _path: wallpaper_apply.PLUGIN)
    return shell


def test_video_payload_uses_percent_encoded_uri_and_video_only_fields(tmp_path, plasma):
    media = tmp_path / "Vídeo teste #1.mp4"
    media.write_bytes(b"")

    plugin, returned = wallpaper_apply.apply(media, loop=True, som=True)

    assert plugin == wallpaper_apply.PLUGIN
    assert returned == media.resolve()
    assert len(plasma.calls) == 1
    _, params, screen = plasma.calls[0]
    uri = media.resolve().as_uri()
    assert screen == 0
    assert uri == "file:///" + str(media.resolve()).lstrip("/").replace(" ", "%20").replace("#", "%23").replace("í", "%C3%AD")
    assert params["Source"] == uri
    assert json.loads(params["VideoUrls"])[0]["filename"] == uri
    assert params["Loop"] is True
    assert params["MuteMode"] == 4
    assert params["Volume"] == 1.0
    assert params["Paused"] is False
    # An image fallback can leave a stale image item above the video in QML.
    assert "Image" not in params


def test_image_payload_does_not_carry_video_or_audio_settings(tmp_path, plasma):
    image = tmp_path / "papel.png"
    image.write_bytes(b"")

    wallpaper_apply.apply(image, loop=True, som=True)

    _, params, _ = plasma.calls[0]
    assert params == {
        "existing": "value",
        "Source": image.resolve().as_uri(),
        "Image": image.resolve().as_uri(),
    }
    assert not {"VideoUrls", "LastVideo", "Loop", "MuteMode", "Volume"}.intersection(params)


def test_apply_all_uses_existing_screens_and_skips_gaps(tmp_path, plasma):
    image = tmp_path / "papel.png"
    image.write_bytes(b"")
    # A disconnected output may leave a hole in Plasma's screen-number sequence.
    plasma.wallpapers = {0: {"a": 1}, 2: {"b": 2}}

    wallpaper_apply.apply(image)

    assert [screen for _, _, screen in plasma.calls] == [0, 2]


def test_explicit_missing_screen_is_not_sent_to_plasma(tmp_path, plasma):
    image = tmp_path / "papel.png"
    image.write_bytes(b"")

    with pytest.raises(ValueError, match="tela.*inexistente|screen.*does not exist"):
        wallpaper_apply.apply(image, screen=3)

    assert plasma.calls == []


def test_video_payload_sets_paused(tmp_path, plasma):
    media = tmp_path / "video.mp4"
    media.write_bytes(b"")

    wallpaper_apply.apply(media, paused=True)

    _, params, _ = plasma.calls[0]
    assert params["Paused"] is True
