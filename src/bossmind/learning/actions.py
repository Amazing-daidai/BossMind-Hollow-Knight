from bossmind.data.schema import ButtonStates, Observation


ACTION_KEY = ("left", "right", "up", "down", "jump", "attack", "dash", "super_dash", "dream_knife", "heal", "skill", "tab")
PLAY_INFO = ("player_hp", "player_x", "player_y", "soul", "player_facing_right")
ENEMY_INFO = ("enemy_hp", "enemy_x", "enemy_y", "boss_facing_right")


# 按键转向量
def key_to_vec(key_states: ButtonStates) -> list:
    vec_list = [1 if getattr(key_states, key) else 0 for key in ACTION_KEY]
    return vec_list

# 状态转向量
def obs_to_vec(observation: Observation) -> list:
    player_states = observation.player
    enemies_states = observation.enemies
    player_vec = [getattr(player_states, key) for key in PLAY_INFO]
    enemies_vec = [getattr(enemies_states, key) for key in ENEMY_INFO]
    return player_vec + enemies_vec

