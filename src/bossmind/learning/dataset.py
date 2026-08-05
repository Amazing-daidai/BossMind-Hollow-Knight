import jsonlines
import json
import torch
import logging

from pathlib import Path

from bossmind.paths import RAW_DATA_DIR
from bossmind.learning.actions import key_to_vec, obs_to_vec
from bossmind.data.schema import EventRecord

logger = logging.getLogger(__name__)

# 加载一局的数据
def load_episode(file: Path) -> tuple[list, list]:
    feature_list = []
    label_list = []
    n_skip = 0
    with jsonlines.open(file) as reader:
        for obj in reader:
            # 获取事件
            event = EventRecord.model_validate(obj)
            # 获取键盘状态
            key_vec = key_to_vec(event.key_states.held)
            # 获取游戏状态
            obs_vec = obs_to_vec(event.observation)
            # 跳过含None的事件
            if None in key_vec or None in obs_vec:
                n_skip += 1
                continue
            feature_list.append(obs_vec)
            label_list.append(key_vec)
        logger.info(f"文件{file}跳过{n_skip}个事件")
    return feature_list, label_list


# 获取一个batch内的有效数据，返回特征和标签列表
def load_batch(batch_name: str) -> tuple[list, list]:
    # 获取地址
    batch_dir = RAW_DATA_DIR / batch_name
    feature_list = []
    label_list = []
    # 遍历子项
    for epi_dir in batch_dir.iterdir():
        if epi_dir.is_dir():
            meta_path = epi_dir / "meta.json"
            if not meta_path.exists():
                logger.warning(f"文件{meta_path}不存在")
                continue
            # 读取meta数据
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                # 判断是否为有效数据
                if meta["end_reason"] == "win":
                    # 加载数据
                    try:
                        event_path = epi_dir / "events.jsonl"
                        if not event_path.exists():
                            logger.warning(f"文件{event_path}不存在")
                            continue
                        feature, label = load_episode(event_path)
                        feature_list.extend(feature)
                        label_list.extend(label)
                    except Exception:
                        logger.error(f"文件{event_path}读取失败")
                        continue
            except Exception:
                logger.error(f"文件{meta_path}读取失败")
                continue
    return feature_list, label_list


# Dataset类
# 定义Dataset类
class FrameDataset(torch.utils.data.Dataset):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __len__(self):
        return len(self.x)

    def __getitem__(self, idx):
        return self.x[idx], self.y[idx]


# 数据处理函数
def _collate_fn(batch):
    # 转化为tensor
    x, y = zip(*batch)
    x = torch.tensor(x, dtype=torch.float32)
    y = torch.tensor(y, dtype=torch.float32)
    return x, y


def get_dataloader(batch_name, batch_size: int):
    """_summary_
    获取dataloader
    Args:
        batch_name (_type_): 数据集名称
        batch_size (int): 批量大小

    Returns:
        dataloader: 数据加载器
    """
    # 读取数据
    x, y = load_batch(batch_name)
    # 封装为Dataset
    dataset = FrameDataset(x, y)
    # 封装为DataLoader
    dataloader = torch.utils.data.DataLoader(
        dataset, batch_size=batch_size, shuffle=True, collate_fn=_collate_fn, drop_last=True
    )
    return dataloader


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,  # 想看 debug 就改成 DEBUG
        format="%(levelname)s %(name)s: %(message)s",
    )

    dataloader = get_dataloader("pipeline_fake", 2)
    for x, y in dataloader:
        print(x)
        print(y)
