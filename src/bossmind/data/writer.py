import json
import logging

from datetime import datetime

from pathlib import Path

from bossmind.data.schema import validate_event, MetaData
from bossmind.paths import RAW_DATA_DIR

logger = logging.getLogger(__name__)


# 写入事件记录类
class EpisodeWriter:
    def __init__(self, batch_id: str,eps_id: str, boss_name: str):
        self.eps_id = eps_id
        self.batch_id = batch_id
        self.boss_name = boss_name
        self.eps_dir = Path(RAW_DATA_DIR / batch_id / eps_id)
        self.n_events = 0
        self.file = None
        self.t_0 = None
        self.t_1 = None

    # 写meta数据
    def _write_meta(self, end_reason, n_dropped, meta_extra):
        if self.n_events == 0:
            duration = 0
        else:
            duration = self.t_1 - self.t_0
        meta = MetaData(
            eps_id=self.eps_id,
            batch_id=self.batch_id,
            duration=duration / 1e9,
            n_dropped=n_dropped,
            end_reason=end_reason,
            boss=self.boss_name,
            n_events=self.n_events,
            **meta_extra,
        ).model_dump()
        with open(self.eps_dir / "meta.json", "x", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

    # 创建文件夹，创建并打开文件
    def pre_write(self):
        if self.eps_dir.exists():
            raise FileExistsError(f"文件夹已存在: {self.eps_dir}")
        self.eps_dir.mkdir(parents=True, exist_ok=True)
        self.file = open(self.eps_dir / f"events.jsonl", "x", encoding="utf-8")

    # 写入事件
    def write_event(self, data: dict):
        if self.file is None:
            raise ValueError("文件未打开")
        event = validate_event(data)
        line = json.dumps(event.model_dump(), ensure_ascii=False) + "\n"
        self.file.write(line)
        self.file.flush()
        if self.n_events == 0:
            self.t_0 = event.t_ns
        self.n_events += 1
        self.t_1 = event.t_ns

    # 关闭文件
    def close(self, end_reason, n_dropped, **meta_extra):
        self._write_meta(end_reason, n_dropped, meta_extra)
        if self.file is not None:
            self.file.close()
            self.file = None
            self.t_0 = None
            self.t_1 = None
            self.n_events = 0


if __name__ == "__main__":
    batch_id = "test_batch"
    boss_name = "GG_Hornet_1"
    eps_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + boss_name
    writer = EpisodeWriter(batch_id, eps_id, boss_name)
    writer.pre_write()

    _keys_off = {
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
    }

    fake_events = [
        {
            "t_ns": 1_000_000_000_000,
            "t_rel_ns": 0,
            "frame_idx": 0,
            "lag_ns": 0,
            "eps_id": eps_id,
            "observation": {
                "player": {"hp": 9, "x": None, "y": None, "soul": None},
                "boss": {},
                "is_battle": True,
            },
            "key_states": {
                "held": dict(_keys_off),
                "pressed": dict(_keys_off),
            },
        },
        {
            "t_ns": 1_000_020_000_000,  # +20ms
            "t_rel_ns": 20_000_000,
            "lag_ns": 0,
            "frame_idx": 1,
            "eps_id": eps_id,
            "observation": {
                "player": {"hp": 9, "x": None, "y": None, "soul": None},
                "boss": {},
                "is_battle": True,
            },
            "key_states": {
                "held": {**_keys_off, "right": True, "attack": True},
                "pressed": {**_keys_off, "right": True, "attack": True},
            },
        },
        {
            "t_ns": 1_000_040_000_000,  # +40ms
            "t_rel_ns": 40_000_000,
            "lag_ns": 0,
            "frame_idx": 2,
            "eps_id": eps_id,
            "observation": {
                "player": {"hp": 8, "x": None, "y": None, "soul": None},
                "boss": {},
                "is_battle": True,
            },
            "key_states": {
                "held": {**_keys_off, "right": True},
                "pressed": dict(_keys_off),
            },
        },
    ]

    for ev in fake_events:
        writer.write_event(ev)

    writer.close(end_reason="aborted", n_dropped=0)
