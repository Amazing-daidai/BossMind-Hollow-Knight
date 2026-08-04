import jsonlines
import json

from typing import Iterator

from bossmind.paths import RAW_DATA_DIR
from bossmind.learning.actions import key_to_vec, obs_to_vec
from bossmind.data.schema import EventRecord

# 加载一局的数据
def load_episode(file) -> list:
    data_list = []
    with jsonlines.open(file) as reader:
        for obj in reader:
            # 获取事件
            event = EventRecord.model_validate(obj)
            # 获取键盘状态
            key_vec = key_to_vec(event.key_states.held)
            # 获取游戏状态
            obs_vec = obs_to_vec(event.observation)
            data_list.append((obs_vec, key_vec)) # (x, a)
    return data_list

# 加载一个batch内的有效数据
def load_batch(batch_name: str) -> Iterator[list[tuple[list, list]]]:
    # 获取地址
    batch_dir = RAW_DATA_DIR / batch_name
    # 遍历子项
    for epi_dir in batch_dir.iterdir():
        if epi_dir.is_dir():
            # 读取meta数据
            with open(epi_dir / "meta.json", "r") as f:
                meta = json.load(f)
            # 判断是否为有效数据
            if meta["end_reason"] == "win":
                # 加载数据
                data_list = load_episode(epi_dir / "events.jsonl")
                yield data_list

if __name__ == "__main__":
    for data_list in load_batch("pipeline_fake"):
        print(data_list)