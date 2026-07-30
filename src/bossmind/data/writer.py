import json
import logging

from pathlib import Path

from bossmind.data.schema import validate_event
from bossmind.paths import RAW_DATA_DIR

logger = logging.getLogger(__name__)


# 写入事件记录类
class EpisodeWriter:
    def __init__(self, batch_id: str, eps_id: str):
        self.eps_id = eps_id
        self.batch_id = batch_id
        self.eps_dir = Path(RAW_DATA_DIR / batch_id / eps_id)
        self.n_events = 0
        self.file = None
        self.t_0 = None
        self.t_1 = None

    # 写meta数据
    def _write_meta(self, end_reason, boss):
        if self.n_events == 0:
            duration = 0
        else:
            duration = self.t_1 - self.t_0
        meta = {
            "eps_id": self.eps_id,
            "batch_id": self.batch_id,
            "duration": duration / 1e9,
            "end_reason": end_reason,
            "boss": boss,
            "n_events": self.n_events,
        }
        with open(self.eps_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

    # 创建文件夹，创建并打开文件
    def pre_write(self):
        if not self.eps_dir.exists():
            self.eps_dir.mkdir(parents=True, exist_ok=True)
        self.file = open(self.eps_dir / f"events.jsonl", "w", encoding="utf-8")

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
    def close(self, end_reason, boss_name):
        self._write_meta(end_reason, boss_name)
        if self.file is not None:
            self.file.close()
            self.file = None
            self.t_0 = None
            self.t_1 = None
            self.n_events = 0


if __name__ == "__main__":
    batch_id = "test_batch"
    eps_id = "ep_001_test"
    writer = EpisodeWriter(batch_id, eps_id)
    writer.pre_write()

    fake_events = [
        {
            "t_ns": 1_000_000_000_000,
            "eps_id": eps_id,
            "player": {"hp": 9},
            "boss": {},
            "key_states": {
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
            },
        },
        {
            "t_ns": 1_000_020_000_000,  # +20ms
            "eps_id": eps_id,
            "player": {"hp": 9},
            "boss": {},
            "key_states": {
                "left": False,
                "right": True,
                "up": False,
                "down": False,
                "jump": False,
                "attack": True,
                "dash": False,
                "super_dash": False,
                "dream_knife": False,
                "heal": False,
                "skill": False,
            },
        },
        {
            "t_ns": 1_000_040_000_000,  # +40ms
            "eps_id": eps_id,
            "player": {"hp": 8},
            "boss": {},
            "key_states": {
                "left": False,
                "right": True,
                "up": False,
                "down": False,
                "jump": False,
                "attack": False,
                "dash": False,
                "super_dash": False,
                "dream_knife": False,
                "heal": False,
                "skill": False,
            },
        },
    ]

    for ev in fake_events:
        writer.write_event(ev)

    writer.close(end_reason="test", boss_name="hornet")
