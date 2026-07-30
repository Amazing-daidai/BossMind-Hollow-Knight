import logging
import time

from bossmind.env_tools.memory import PlayerInfo
from bossmind.env_tools.input import InputController
from bossmind.env_tools.reset_backends.menu import Menu
from bossmind.env_tools.reset_backends.mod import Mod

logger = logging.getLogger(__name__)

class GameSession:
    """
    管理游戏会话，实现取数，读档等。
    """
    def __init__(self):
        self._player_info = PlayerInfo()
        self._input_controller = InputController()
        self._menu = Menu(self._input_controller)
        self._mod = Mod()


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

    def get_hp(self):
        """
        获取玩家当前血量
        """
        return self._player_info.get_player_hp()

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

if __name__ == "__main__":
    game_session = GameSession()
    game_session.reset_game("menu")