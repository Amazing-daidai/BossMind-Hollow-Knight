"""循环打印玩家/Boss 状态，用于 B 机手工验收（掉血、换场景、暂停等）。"""
import logging
import time

from bossmind.env_tools.memory import PlayerInfo
from bossmind.config import load_config

logging.basicConfig(level=logging.WARNING)

config = load_config()
player = PlayerInfo(config)
try:
    player.attach()
    while True:
        states = player.get_player_states()
        scene_name = player.get_scene_name()
        game_state = player.get_game_state()
        boss_hp = player.get_boss_hp()
        is_battle = player.get_is_battle()
        print(
            f"hp={states.player_hp} max_hp={states.max_hp} soul={states.soul} "
            f"x={states.player_x} y={states.player_y} facing={states.player_facing_right} "
            f"scene={scene_name} state={game_state} boss_hp={boss_hp} is_battle={is_battle}"
        )
        time.sleep(0.2)
except KeyboardInterrupt:
    print("退出")
except ValueError as e:
    print(f"错误: {e}")
finally:
    player.detach()
