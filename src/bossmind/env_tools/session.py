import logging
import time

from bossmind.env_tools.memory import PlayerInfo
from bossmind.env_tools.input import InputController
from bossmind.env_tools.reset_backends.menu import Menu
from bossmind.env_tools.reset_backends.mod import Mod
from bossmind.data.schema import PlayerStates, BossStates, Observation
from bossmind.config import load_config
from bossmind.utils import is_window_focused

logger = logging.getLogger(__name__)

class GameSession:
    """
    管理游戏会话，实现取数，读档等。
    """
    def __init__(self, config):
        self._config = config
        self._player_info = PlayerInfo(self._config)
        self._input_controller = InputController(self._config)
        self._menu = Menu(self._input_controller, self._config)
        self._mod = Mod()
        self._last_hp: int | None = None
        self._hp_fail_streak: int = 0


    def attach(self):
        """
        连接游戏进程
        """
        self._player_info.attach()

    def detach(self):
        """
        断开游戏进程
        """
        self._player_info.detach()

    def get_pid(self):
        """
        获取游戏进程 id
        """
        return self._player_info.get_pid()

    def get_is_battle(self):
        """
        获取是否在战斗中
        """
        return self._player_info.get_is_battle()

    def reset_game(self, method):
        """
        重置游戏，为防止游戏读档或者mod回档导致血量基址失效，需要重新连接游戏进程
        """
        if method == "menu":
            self.detach()
            logger.info("游戏重新加载中...")
            self._menu.reset_game()
            time.sleep(5)
        elif method == "mod":
            self.detach()
            logger.info("游戏重新加载中...")
            self._mod.reset_game()
            time.sleep(5)
        else:
            raise ValueError("无效的重置方法")
    
    def goto_boss_room(self, boss_name: str):
        """
        前往指定boss房前
        """
        self._menu.goto_boss_room(boss_name)

    def quit_to_title(self):
        """
        退出到主菜单
        """
        self._menu.quit_to_title()

    def get_observation(self) -> Observation:
        """
        获取游戏环境数据
        """
        game_pid = self.get_pid()
        window_focused = is_window_focused(game_pid)
        player_states = self._player_info.get_player_states()
        raw_hp = player_states.hp
        if raw_hp is not None:
            self._last_hp = raw_hp
            self._hp_fail_streak = 0
            player_states.hp = raw_hp
        else:
            self._hp_fail_streak += 1
            player_states.hp = self._last_hp   # 用上一帧填充，可能失真，后续改。
        boss_states = BossStates()
        observation = Observation(player=player_states, boss=boss_states, is_battle=self.get_is_battle(), window_focused=window_focused, read_error_streak=self._hp_fail_streak)
        return observation

if __name__ == "__main__":
    config = load_config()
    game_session = GameSession(config)
    game_session.get_observation()