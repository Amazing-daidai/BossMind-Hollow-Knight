"""Vision 几何与校验：mock win32 / mss，不弹真窗。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bossmind.env_tools.vision import Vision, VisionError


@pytest.fixture
def fake_config() -> SimpleNamespace:
    return SimpleNamespace(
        process_name="hollow_knight.exe",
        window_title="FakeWindow",
        collect={
            "vision_region": {"left": 10, "top": 20, "width": 200, "height": 100},
            "vision_hz": 10,
        },
    )


class _FakeShot:
    def __init__(self, size, raw_peak=40):
        self.size = size
        w, h = size
        self.raw = bytearray([raw_peak, raw_peak, raw_peak, 255] * (w * h))
        self.rgb = bytes([raw_peak]) * (w * h * 3)


def test_real_region_recomputed_each_capture(fake_config, monkeypatch: pytest.MonkeyPatch):
    origins = iter([(1000, 500), (1100, 600)])

    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.FindWindow",
        lambda _cls, title: 0xABC if title == "FakeWindow" else 0,
    )
    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.IsWindow",
        lambda _hwnd: True,
    )
    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.IsIconic",
        lambda _hwnd: False,
    )
    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.ClientToScreen",
        lambda _hwnd, pt: next(origins) if pt == (0, 0) else pt,
    )

    class _FakeMSS:
        def grab(self, region):
            return _FakeShot((region["width"], region["height"]))

        def close(self):
            pass

    monkeypatch.setattr("bossmind.env_tools.vision.mss.mss", lambda: _FakeMSS())

    v = Vision(fake_config)
    v.pre_capture()
    assert v._real_region["left"] == 1010
    v.capture()
    assert v._real_region["left"] == 1110
    v.stop()


def test_minimized_raises(fake_config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.FindWindow",
        lambda *_a, **_k: 1,
    )
    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.IsWindow",
        lambda _h: True,
    )
    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.IsIconic",
        lambda _h: True,
    )
    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.ClientToScreen",
        lambda _h, pt: (0, 0),
    )
    monkeypatch.setattr(
        "bossmind.env_tools.vision.mss.mss",
        lambda: type(
            "M",
            (),
            {
                "grab": lambda self, r: _FakeShot((200, 100)),
                "close": lambda self: None,
            },
        )(),
    )

    v = Vision(fake_config)
    with pytest.raises(VisionError, match="最小化"):
        v.pre_capture()


def test_missing_window_raises(fake_config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "bossmind.env_tools.vision.win32gui.FindWindow",
        lambda *_a, **_k: 0,
    )
    v = Vision(fake_config)
    with pytest.raises(VisionError, match="未找到窗口"):
        v.pre_capture()
