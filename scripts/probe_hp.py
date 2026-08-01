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
        print(
            f"hp={states.hp} max_hp={states.max_hp} soul={states.soul}"
        )
        time.sleep(0.2)
except KeyboardInterrupt:
    print("退出")
except ValueError as e:
    print(f"错误: {e}")
finally:
    player.detach()
