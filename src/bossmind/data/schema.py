from pydantic import BaseModel, Field, ValidationError

# 按键内容校验
class KeyStates(BaseModel):
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

# 玩家状态内容校验
class PlayerStates(BaseModel):
    hp: int = Field(...)

# 整体记录内容校验
class EventRecord(BaseModel):
    t_ns: int = Field(...)
    eps_id: str = Field(...)
    key_states: KeyStates
    boss: dict = Field(default_factory=dict)
    player: PlayerStates

def validate_event(data: dict) -> EventRecord:
    try:
        return EventRecord.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"事件格式有误: {e}")