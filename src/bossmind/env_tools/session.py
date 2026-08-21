import logging
import time

from bossmind.env_tools.obs_map import ObservationMapper
from bossmind.env_tools.input import InputController
from bossmind.env_tools.reset_backends.menu import Menu
from bossmind.env_tools.reset_backends.mod import Mod
from bossmind.env_tools.mod_ipc import ModIpc
from bossmind.data.schema import Observation
from bossmind.config import load_config
from bossmind.utils import is_window_focused, get_game_pid

logger = logging.getLogger(__name__)

class GameSession:
    """
    管理游戏会话，实现取数，读档等。
    """
    def __init__(self, config):
        self._config = config
        self._input_controller = InputController(self._config)
        self._menu = Menu(self._input_controller, self._config)
        self._ipc = ModIpc(self._config)
        self._mapper = ObservationMapper(self._config)
        self._mod = Mod()
        self._pid = None


    def attach(self):
        """
        启动接收
        """
        self._ipc.start()
        self._pid = self._get_pid()

    def detach(self):
        """
        停止接收
        """
        self._ipc.stop()
        self._pid = None

    def _get_pid(self):
        """
        获取游戏进程 id
        """
        return get_game_pid(self._config.process_name)

    def _get_data(self):
        """获取mod发送的游戏数据

        Returns:
            dict: 游戏数据
        """
        return self._ipc.read_latest()

    def reset_game(self, method):
        """
        重置游戏，为防止游戏读档或者mod回档导致血量基址失效，需要重新连接游戏进程
        """
        if method == "menu":
            logger.info("游戏重新加载中...")
            self._menu.reset_game()
            time.sleep(5)
        elif method == "mod":
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

    def get_is_battle(self) -> bool:
        """获取是否在战斗中

        Returns:
            bool: 是否在战斗中
        """
        obs = self.get_observation()
        return bool(obs.is_battle)

    def get_observation(self) -> Observation:
        """
        获取游戏环境数据
        """
        window_focused = is_window_focused(self._pid)
        data = self._get_data()
        if data is None:
            logger.warning("未收到游戏数据")
            return Observation(
                is_battle=False,
                window_focused=window_focused
            )
        observation = self._mapper.udp_dict_to_observation(data, window_focused=window_focused)
        return observation

if __name__ == "__main__":
    config = load_config()
    game_session = GameSession(config)
    game_session.attach()
    game_session.get_observation()
    game_session.detach()