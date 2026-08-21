"""obs_to_vec：45 维、dx/dy、mask、空包与截断。"""

from bossmind.data.schema import EnemyStates, Observation, PlayerStates
from bossmind.learning.actions import (
    ENEMY_INFO,
    MAX_ENEMIES,
    PLAY_INFO,
    obs_to_vec,
)

# 与 policy._input_dim 同一公式：5 + 8*4 + 8
VEC_DIM = len(PLAY_INFO) + len(ENEMY_INFO) * MAX_ENEMIES + MAX_ENEMIES
ENEMY_SLOT = 4  # hp, dx, dy, facing
PLAYER_DIM = len(PLAY_INFO)


def _player(**kwargs) -> PlayerStates:
    defaults = dict(
        player_hp=5,
        player_x=10.0,
        player_y=20.0,
        soul=33,
        player_facing_right=True,
    )
    defaults.update(kwargs)
    return PlayerStates(**defaults)


def _enemy(**kwargs) -> EnemyStates:
    defaults = dict(
        enemy_hp=100,
        enemy_x=10.0,
        enemy_y=20.0,
        enemy_facing_right=False,
        name="Hornet",
    )
    defaults.update(kwargs)
    return EnemyStates(**defaults)


def test_vec_dim_is_45():
    assert VEC_DIM == 45


def test_empty_observation_is_all_zeros():
    vec = obs_to_vec(Observation())
    assert vec == [0] * VEC_DIM


def test_player_only_enemies_none_pads_zeros():
    vec = obs_to_vec(Observation(player=_player(), enemies=None))
    assert len(vec) == VEC_DIM
    assert vec[:PLAYER_DIM] == [5, 10.0, 20.0, 33, True]
    assert vec[PLAYER_DIM:] == [0] * (VEC_DIM - PLAYER_DIM)


def test_three_enemies_relative_xy_and_mask():
    obs = Observation(
        player=_player(player_x=10.0, player_y=20.0),
        enemies=[
            _enemy(enemy_hp=50, enemy_x=13.0, enemy_y=17.0, enemy_facing_right=True),
            _enemy(enemy_hp=100, enemy_x=12.0, enemy_y=24.0, enemy_facing_right=False),
            _enemy(enemy_hp=80, enemy_x=7.0, enemy_y=20.0, enemy_facing_right=True),
        ],
    )
    vec = obs_to_vec(obs)
    assert len(vec) == VEC_DIM

    # hp 降序：100, 80, 50；dx/dy = enemy - player
    body = vec[PLAYER_DIM : PLAYER_DIM + 3 * ENEMY_SLOT]
    assert body == [
        100, 2.0, 4.0, False,
        80, -3.0, 0.0, True,
        50, 3.0, -3.0, True,
    ]
    pad = vec[PLAYER_DIM + 3 * ENEMY_SLOT : PLAYER_DIM + MAX_ENEMIES * ENEMY_SLOT]
    assert pad == [0] * (5 * ENEMY_SLOT)
    assert vec[-MAX_ENEMIES:] == [1, 1, 1, 0, 0, 0, 0, 0]


def test_sorts_none_hp_as_zero_and_keeps_length():
    obs = Observation(
        player=_player(),
        enemies=[
            _enemy(enemy_hp=None, enemy_x=11.0, enemy_y=20.0),
            _enemy(enemy_hp=10, enemy_x=14.0, enemy_y=20.0),
        ],
    )
    vec = obs_to_vec(obs)
    assert len(vec) == VEC_DIM
    first = vec[PLAYER_DIM : PLAYER_DIM + ENEMY_SLOT]
    second = vec[PLAYER_DIM + ENEMY_SLOT : PLAYER_DIM + 2 * ENEMY_SLOT]
    assert first[0] == 10
    assert second[0] is None
    assert vec[-MAX_ENEMIES:] == [1, 1, 0, 0, 0, 0, 0, 0]


def test_truncates_to_max_enemies_highest_hp():
    enemies = [
        _enemy(enemy_hp=i, enemy_x=10.0 + i, enemy_y=20.0)
        for i in range(1, 10)  # hp 1..9
    ]
    vec = obs_to_vec(Observation(player=_player(), enemies=enemies))
    assert len(vec) == VEC_DIM
    hps = [vec[PLAYER_DIM + i * ENEMY_SLOT] for i in range(MAX_ENEMIES)]
    assert hps == [9, 8, 7, 6, 5, 4, 3, 2]
    assert vec[-MAX_ENEMIES:] == [1] * MAX_ENEMIES
    assert 1 not in hps
