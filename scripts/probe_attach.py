import logging

from bossmind.env_tools.memory import PlayerInfo
from bossmind.config import load_config

logging.basicConfig(level=logging.WARNING)

config = load_config()
player = PlayerInfo(config)
try:
    player.attach()
    print(f"pid为{player.get_pid()}")
except KeyboardInterrupt:
    print("退出")
except ValueError as e:
    print(f"错误: {e}")
finally:
    player.detach()