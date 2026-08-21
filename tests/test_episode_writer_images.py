"""EpisodeWriter 异步写图：假 ScreenShot，不依赖游戏窗口。"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from queue import Queue

import pytest
from PIL import Image

from bossmind.data.writer import EpisodeWriter
from bossmind.paths import RAW_DATA_DIR


class FakeShot:
    """具备 .size / .raw / .rgb，兼容 jpg(BGRX) 与 png(.rgb) 分支。"""

    def __init__(self, width: int = 8, height: int = 8, fill: int = 40):
        self.size = (width, height)
        # BGRA
        pixel = bytes([fill & 0xFF, fill & 0xFF, fill & 0xFF, 255])
        self.raw = bytearray(pixel * (width * height))
        self.rgb = bytes([fill & 0xFF]) * (width * height * 3)


def _keys_off() -> dict[str, bool]:
    return {
        "left": False,
        "right": False,
        "up": False,
        "down": False,
        "jump": False,
        "attack": False,
        "dash": False,
        "super_dash": False,
        "dream_knife": False,
        "heal": False,
        "skill": False,
        "tab": False,
    }


def _fake_event(
    eps_id: str,
    frame_idx: int,
    t_rel_ns: int,
    *,
    player_hp: int = 9,
    enemy_hp: int | None = 800,
    is_battle: bool = True,
    held: dict[str, bool] | None = None,
    pressed: dict[str, bool] | None = None,
) -> dict:
    """一帧假事件，字段对齐 schema 2.0.0。"""
    enemies = [
        {
            "enemy_hp": enemy_hp,
            "enemy_x": 40.0,
            "enemy_y": 27.658,
            "enemy_facing_right": False,
            "name": "Hornet",
        }
    ]
    return {
        "t_ns": 1_000_000_000_000 + t_rel_ns,
        "t_rel_ns": t_rel_ns,
        "lag_ns": 0,
        "frame_idx": frame_idx,
        "eps_id": eps_id,
        "observation": {
            "player": {
                "player_hp": player_hp,
                "player_x": 15.0 + frame_idx,
                "player_y": 27.658,
                "soul": 33,
                "player_facing_right": True,
            },
            "enemies": enemies,
            "n_enemies": len(enemies),
            "window_focused": True,
            "is_battle": is_battle,
            "scene_name": "GG_Hornet_1",
            "game_state": "PLAYING",
        },
        "key_states": {
            "held": held if held is not None else _keys_off(),
            "pressed": pressed if pressed is not None else _keys_off(),
        },
    }


def _win_episode_events(eps_id: str) -> list[dict]:
    """一局假数据：开战 → 输出 → 战斗结束（供 end_reason=win）。"""
    attack = {**_keys_off(), "attack": True}
    return [
        _fake_event(eps_id, 0, 0, enemy_hp=800, is_battle=True),
        _fake_event(
            eps_id,
            1,
            20_000_000,
            enemy_hp=200,
            is_battle=True,
            held=attack,
            pressed=attack,
        ),
        _fake_event(
            eps_id,
            2,
            40_000_000,
            enemy_hp=0,
            is_battle=False,
        ),
    ]


@pytest.fixture
def writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> EpisodeWriter:
    monkeypatch.setattr("bossmind.data.writer.RAW_DATA_DIR", tmp_path)
    w = EpisodeWriter(
        "test_batch",
        "eps_vision_1",
        "GG_Hornet_1",
        image_queue_size=30,
        image_ext="jpg",
        jpeg_quality=85,
    )
    w.pre_write()
    return w


def test_enqueue_then_close_writes_jpgs_and_stops_thread(writer: EpisodeWriter, tmp_path: Path):
    shot = FakeShot()
    n = 5
    for i in range(n):
        assert writer.enqueue_image(shot, frame_idx=i, t_rel_ns=i * 100_000_000)

    assert writer.image_thread is not None
    assert writer.image_thread.is_alive()

    writer.close(end_reason="aborted", n_dropped=0)
    assert not writer.image_thread  # close 后置 None
    assert writer._closed

    frames_dir = tmp_path / "test_batch" / "eps_vision_1" / "frames"
    jpgs = sorted(frames_dir.glob("*.jpg"))
    assert len(jpgs) == n
    with Image.open(jpgs[0]) as im:
        assert im.size == (8, 8)

    meta = json.loads(
        (tmp_path / "test_batch" / "eps_vision_1" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["image_dropped"] == 0
    assert meta["n_frames"] == n
    assert meta["n_frames_enqueued"] == n
    assert meta["image_join_timeout"] is False
    assert meta["image_error"] is None


def test_write_fake_win_episode(writer: EpisodeWriter, tmp_path: Path):
    """写入一局假数据：3 事件 + 3 图，end_reason=win。"""
    shot = FakeShot(fill=80)
    events = _win_episode_events(writer.eps_id)
    for ev in events:
        writer.write_event(ev)
        writer.enqueue_image(shot, frame_idx=ev["frame_idx"], t_rel_ns=ev["t_rel_ns"])

    writer.close(end_reason="win", n_dropped=0)

    eps = tmp_path / "test_batch" / "eps_vision_1"
    lines = (eps / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3

    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["observation"]["enemies"][0]["enemy_hp"] == 800
    assert parsed[0]["observation"]["n_enemies"] == 1
    assert parsed[0]["observation"]["is_battle"] is True
    assert parsed[1]["observation"]["enemies"][0]["enemy_hp"] == 200
    assert parsed[1]["key_states"]["pressed"]["attack"] is True
    assert parsed[2]["observation"]["enemies"][0]["enemy_hp"] == 0
    assert parsed[2]["observation"]["is_battle"] is False

    assert len(list((eps / "frames").glob("*.jpg"))) == 3

    meta = json.loads((eps / "meta.json").read_text(encoding="utf-8"))
    assert meta["end_reason"] == "win"
    assert meta["n_events"] == 3
    assert meta["n_dropped"] == 0
    assert meta["n_frames"] == 3
    assert meta["boss"] == "GG_Hornet_1"


def test_close_is_fast_when_queue_empty(writer: EpisodeWriter):
    t0 = time.perf_counter()
    writer.close(end_reason="aborted", n_dropped=0)
    assert time.perf_counter() - t0 < 3.0
    writer.close(end_reason="aborted", n_dropped=0)  # 幂等


def test_queue_full_drops_and_keeps_newer_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("bossmind.data.writer.RAW_DATA_DIR", tmp_path)

    real_encode = EpisodeWriter._encode_one

    def slow_encode(self, item):
        time.sleep(0.05)
        return real_encode(self, item)

    monkeypatch.setattr(EpisodeWriter, "_encode_one", slow_encode)

    w = EpisodeWriter(
        "test_batch",
        "eps_drop",
        "GG_Hornet_1",
        image_queue_size=2,
        image_ext="jpg",
    )
    w.pre_write()

    shot = FakeShot()
    for i in range(15):
        w.enqueue_image(shot, frame_idx=i, t_rel_ns=i)

    assert w.image_dropped > 0
    w.close(end_reason="aborted", n_dropped=0)

    meta = json.loads(
        (tmp_path / "test_batch" / "eps_drop" / "meta.json").read_text(encoding="utf-8")
    )
    n_jpg = len(list((tmp_path / "test_batch" / "eps_drop" / "frames").glob("*.jpg")))
    assert meta["image_dropped"] > 0
    assert n_jpg < 15
    assert n_jpg >= 1
    assert meta["n_frames"] == n_jpg


def test_encode_error_sets_image_error_and_stops_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("bossmind.data.writer.RAW_DATA_DIR", tmp_path)
    calls = {"n": 0}
    real_encode = EpisodeWriter._encode_one

    def flaky_encode(self, item):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise OSError("disk full")
        return real_encode(self, item)

    monkeypatch.setattr(EpisodeWriter, "_encode_one", flaky_encode)

    w = EpisodeWriter("test_batch", "eps_err", "GG_Hornet_1", image_ext="jpg")
    w.pre_write()
    shot = FakeShot()
    for i in range(5):
        w.enqueue_image(shot, i, i)
        time.sleep(0.02)

    # 等写盘线程吃到错误
    deadline = time.time() + 2
    while w.image_error is None and time.time() < deadline:
        time.sleep(0.02)
    assert w.image_error is not None
    assert "OSError" in w.image_error

    w.close(end_reason="error", n_dropped=0)
    meta = json.loads(
        (tmp_path / "test_batch" / "eps_err" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["image_error"] is not None
    assert meta["n_frames"] == len(
        list((tmp_path / "test_batch" / "eps_err" / "frames").glob("*.jpg"))
    )


def test_enqueue_rejects_after_stop(writer: EpisodeWriter):
    writer._image_stop.set()
    assert writer.enqueue_image(FakeShot(), 0, 0) is False
    writer.close(end_reason="aborted", n_dropped=0)


def test_drop_oldest_does_not_eat_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("bossmind.data.writer.RAW_DATA_DIR", tmp_path)
    w = EpisodeWriter("test_batch", "eps_sent", "GG_Hornet_1", image_queue_size=1)
    # 不启动消费线程，手动构造「哨兵在队且满」
    w.image_queue.put_nowait(None)
    w._image_stop.clear()
    assert w.enqueue_image(FakeShot(), 99, 0) is False
    assert w.image_queue.get_nowait() is None


def write_fake_win_episode(
    batch_id: str = "pipeline_fake",
    boss_name: str = "GG_Hornet_1",
) -> Path:
    """写一局假 win 数据到 RAW_DATA_DIR，返回 episode 目录。"""
    eps_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_fake_win"
    w = EpisodeWriter(batch_id, eps_id, boss_name, image_ext="jpg", jpeg_quality=85)
    w.pre_write()
    shot = FakeShot(width=64, height=36, fill=80)
    for ev in _win_episode_events(eps_id):
        w.write_event(ev)
        w.enqueue_image(shot, frame_idx=ev["frame_idx"], t_rel_ns=ev["t_rel_ns"])
    w.close(end_reason="win", n_dropped=0)
    return RAW_DATA_DIR / batch_id / eps_id


if __name__ == "__main__":
    eps_dir = write_fake_win_episode()
    meta = json.loads((eps_dir / "meta.json").read_text(encoding="utf-8"))
    n_jpg = len(list((eps_dir / "frames").glob("*.jpg")))
    n_ev = len((eps_dir / "events.jsonl").read_text(encoding="utf-8").strip().splitlines())
    print(f"wrote: {eps_dir}")
    print(
        f"end_reason={meta['end_reason']} n_events={n_ev} "
        f"n_frames={n_jpg} duration={meta['duration']:.3f}s"
    )
