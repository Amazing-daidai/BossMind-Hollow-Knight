from pydantic import BaseModel, Field, ValidationError
from typing import Literal

SCHEMA_VERSION = "2.0.0"

# 按键数据
class ButtonStates(BaseModel):
    left: bool = Field(default=False)
    right: bool = Field(default=False)
    up: bool = Field(default=False)
    down: bool = Field(default=False)
    jump: bool = Field(default=False)
    attack: bool = Field(default=False)
    dash: bool = Field(default=False)
    super_dash: bool = Field(default=False)
    dream_knife: bool = Field(default=False)
    heal: bool = Field(default=False)
    skill: bool = Field(default=False)
    tab: bool = Field(default=False)

class KeyStates(BaseModel):
    held: ButtonStates = Field(default_factory=ButtonStates)
    pressed: ButtonStates = Field(default_factory=ButtonStates)

# 玩家状态
class PlayerStates(BaseModel):
    player_hp: int | None = None
    player_x: float | None = None
    player_y: float | None = None
    soul: int | None = None
    player_facing_right: bool | None = None

# 敌人状态
class EnemyStates(BaseModel):
    enemy_hp: int | None = None
    enemy_x: float | None = None
    enemy_y: float | None = None
    enemy_facing_right: bool | None = None
    name: str | None = None

# 游戏数据
class Observation(BaseModel):
    player: PlayerStates
    enemies: list[EnemyStates]
    n_enemies: int | None = None
    window_focused: bool | None = None
    is_battle: bool | None = None
    scene_name: str | None = None
    game_state: str | None = None

# 整体记录内容
class EventRecord(BaseModel):
    t_ns: int = Field(...)  # 绝对时间
    t_rel_ns: int = Field(...)  # 相对时间
    lag_ns: int = Field(...)  # 采集滞后
    frame_idx: int = Field(...)
    eps_id: str = Field(...)
    observation: Observation
    key_states: KeyStates

def validate_event(data: dict) -> EventRecord:
    try:
        return EventRecord.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"事件格式有误: {e}")

# meta数据
class MetaData(BaseModel):
    schema_version: str = Field(default=SCHEMA_VERSION) 
    started_at_unix_ns: int | None = None  # 开始时间
    code_git_sha: str = "unknown"  # git hash
    config_hash: str = "unknown"  # 配置hash
    eps_id: str = Field(...)
    batch_id: str = Field(...)
    duration: float = Field(...)
    sample_hz_nominal: int | None = None  # 采样率
    sample_hz_measured: float | None = None  # 实际采样率
    dt_p50_ns: int | None = None 
    dt_p95_ns: int | None = None
    n_dropped: int = Field(...)
    image_dropped: int = Field(...)
    end_reason: Literal["win","death","aborted","error","timeout","discard"]
    boss: str
    n_events: int = Field(...)
    n_frames: int = Field(...)
    vision_hz: float | None = None  # 图像采样率
    vision_region: dict | None = None
    vision_format: str | None = None  # 图像采集格式
    vision_quality: int | None = None  # 图像质量
    vision_color_order: str | None = None  # 图像颜色顺序
    n_frames_enqueued: int | None = None
    image_join_timeout: bool | None = None
    image_error: str | None = None
    capture_ms_p50: float | None = None
    capture_ms_p95: float | None = None

