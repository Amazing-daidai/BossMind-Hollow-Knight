from bossmind.data.schema import ButtonStates, Observation


ACTION_KEY = ("left", "right", "up", "down", "jump", "attack", "dash", "super_dash", "dream_knife", "heal", "skill", "tab")
PLAY_INFO = ("player_hp", "player_x", "player_y", "soul", "player_facing_right", "player_on_ground")
BOSS_INFO = ("boss_hp", "boss_x", "boss_y", "boss_facing_right", "boss_on_ground")


# 按键转向量
def key_to_vec(key_states: ButtonStates) -> list:
    vec_list = [1 if getattr(key_states, key) else 0 for key in ACTION_KEY]
    return vec_list

# 状态转向量
def obs_to_vec(observation: Observation) -> list:
    player_states = observation.player
    boss_states = observation.boss
    player_vec = [getattr(player_states, key) for key in PLAY_INFO]
    boss_vec = [getattr(boss_states, key) for key in BOSS_INFO]
    return player_vec + boss_vec

