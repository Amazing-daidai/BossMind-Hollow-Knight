import yaml

from bossmind.paths import GAME_INFO_FILE

from functools import lru_cache

from pydantic import BaseModel, ValidationError

class Config(BaseModel):
    process_name: str
    window_title: str
    player_info: dict
    player_position: dict
    player_facing: dict
    scene_name: dict
    game_state: dict
    boss_info: dict
    keybinds: dict
    menu: dict
    collect: dict
    client: dict

@lru_cache(maxsize=1)
def load_config():
    """
    加载配置文件，并返回Config对象
    """
    if not GAME_INFO_FILE.exists():
        raise FileNotFoundError(f"配置文件不存在: {GAME_INFO_FILE}")
    with open(GAME_INFO_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    try:
        return Config.model_validate(config)
    except ValidationError as e:
        raise ValueError(f"配置文件有误: {e}")
