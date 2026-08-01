from pydantic import BaseModel, Field, ValidationError
from typing import Literal

SCHEMA_VERSION = "1.0.0"

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

class KeyStates(BaseModel):
    held: ButtonStates = Field(default_factory=ButtonStates)
    pressed: ButtonStates = Field(default_factory=ButtonStates)

# 玩家状态
class PlayerStates(BaseModel):
    hp: int | None = None
    x: float | None = None
    y: float | None = None
    soul: int | None = None
    max_hp: int | None = None
    facing_right: bool | None = None
    on_ground: bool | None = None

# boss状态
class BossStates(BaseModel):
    hp: int | None = None
    x: float | None = None
    y: float | None = None
    facing_right: bool | None = None
    on_ground: bool | None = None

# 游戏数据
class Observation(BaseModel):
    player: PlayerStates
    boss: BossStates
    window_focused: bool | None = None
    is_battle: bool | None = None
    scene_name: str | None = None
    game_state: str | None = None
    read_error_streak: int = Field(default=0)

# 整体记录内容
class EventRecord(BaseModel):
    t_ns: int = Field(...)
    t_rel_ns: int = Field(...)
    lag_ns: int = Field(...)
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
    started_at_unix_ns: int | None = None
    code_git_sha: str = "unknown"
    config_hash: str = "unknown"
    eps_id: str = Field(...)
    batch_id: str = Field(...)
    duration: float = Field(...)
    sample_hz_nominal: int | None = None
    sample_hz_measured: float | None = None
    dt_p50_ns: int | None = None
    dt_p95_ns: int | None = None
    n_dropped: int = Field(...)
    end_reason: Literal["win","death","aborted","error","timeout","discard"]
    boss: str
    n_events: int = Field(...)



