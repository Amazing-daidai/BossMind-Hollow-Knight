import yaml
import time
import logging

from bossmind.env_tools.input import InputController
from bossmind.paths import GAME_INFO_FILE

logger = logging.getLogger(__name__)

class Menu:
    """
    通过菜单方式实现读档操作
    """
    def __init__(self, input_controller: InputController):
        self.__menu_config = None
        self._input = input_controller
        self._get_config()

    # 工具函数
    # 配置
    def _get_config(self):
        """
        用于加载配置文件，获取按键序列
        """
        # 校验配置文件是否存在
        if not GAME_INFO_FILE.exists():
            raise FileNotFoundError(f"配置文件不存在: {GAME_INFO_FILE}")
        # 读取配置文件，获取按键序列
        with open(GAME_INFO_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            self.__menu_config = config["menu"]
    
    # 退出到主菜单
    def quit_to_title(self):
        """
        退出到主菜单
        """
        logger.info("开始退出到主菜单操作")
        event_list = self.__menu_config["quit_to_title"]["event"]
        for key, delay in event_list:
            self._input.tap(key)
            time.sleep(float(delay))
        logger.info("退出到主菜单操作完成")

    # 加载存档
    def load_save(self):
        """
        加载存档
        """
        logger.info("开始加载存档操作")
        event_list = self.__menu_config["load_save"]["event"]
        for key, delay in event_list:
            self._input.tap(key)
            time.sleep(float(delay))
        logger.info("加载存档操作完成")

    # 前往指定boss房前
    def goto_boss_room(self, boss_name: str):
        """
        前往指定boss房前
        """
        if boss_name not in self.__menu_config["godhome_boss_room"].keys():
            raise ValueError(f"未知boss: {boss_name}")
        logger.info(f"开始前往{boss_name}房前操作")
        event_list = self.__menu_config["godhome_boss_room"][boss_name]["event"]
        for event in event_list:
            key, action_list = list(event.items())[0]
            action, delay, duration = action_list
            self._input.run_action(action, key, float(delay), float(duration))
        logger.info(f"前往{boss_name}房前操作完成")

    def reset_game(self):
        """
        重置游戏
        """
        self.quit_to_title()
        self.load_save()

if __name__ == "__main__":
    input_controller = InputController()
    menu = Menu(input_controller)
    menu.goto_boss_room("hornet")

