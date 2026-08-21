from bossmind.data.schema import ButtonStates, Observation


MAX_ENEMIES = 8
ACTION_KEY = ("left", "right", "up", "down", "jump", "attack", "dash", "super_dash", "dream_knife", "heal", "skill", "tab")
PLAY_INFO = ("player_hp", "player_x", "player_y", "soul", "player_facing_right")
ENEMY_INFO = ("enemy_hp", "d_x", "d_y", "enemy_facing_right")


# 按键转向量
def key_to_vec(key_states: ButtonStates) -> list:
    vec_list = [1 if getattr(key_states, key) else 0 for key in ACTION_KEY]
    return vec_list

# 状态转向量
def obs_to_vec(observation: Observation) -> list:
    if observation.player is None:
        return [0] * (len(PLAY_INFO) + MAX_ENEMIES * 4 + MAX_ENEMIES)
    # 玩家vec
    player_states = observation.player
    player_vec = [getattr(player_states, key) for key in PLAY_INFO]
    player_x = player_states.player_x
    player_y = player_states.player_y
    # 敌人vec
    if observation.enemies is None:
        return player_vec + [0] * (MAX_ENEMIES * 4 + MAX_ENEMIES)
    enemies_vec = []
    enemies_list = observation.enemies
    # 取前八个
    final_list = sorted(enemies_list, key=lambda x: x.enemy_hp or 0, reverse=True)[:MAX_ENEMIES]
    for enemy_states in final_list:
        enemy_hp = enemy_states.enemy_hp
        enemy_x = enemy_states.enemy_x
        enemy_y = enemy_states.enemy_y
        enemy_facing_right = enemy_states.enemy_facing_right
        enemies_vec.append(enemy_hp)
        enemies_vec.append(enemy_x - player_x)
        enemies_vec.append(enemy_y - player_y)
        enemies_vec.append(enemy_facing_right)
    # 填充0和mask
    mask_vec = [0 if i >= len(final_list) else 1 for i in range(MAX_ENEMIES)]
    if len(final_list) < MAX_ENEMIES:
        zero_vec = [0] * 4
        enemies_vec.extend(zero_vec * (MAX_ENEMIES-len(final_list)))
    
    return player_vec + enemies_vec + mask_vec

