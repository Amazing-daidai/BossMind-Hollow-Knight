import time
import logging

from bossmind.env_tools.input import InputController
from bossmind.config import load_config

logger = logging.getLogger(__name__)

class Menu:
    """
    通过菜单方式实现读档操作
    """
    def __init__(self, input_controller: InputController, config):
        self._config = config
        self._input = input_controller
        self._menu_config = None
        self._get_config()

    # 工具函数
    # 配置
    def _get_config(self):
        """
        用于加载配置文件，获取按键序列
        """
        # 读取配置文件，获取按键序列
        self._menu_config = self._config.menu
    
    # 退出到主菜单
    def quit_to_title(self):
        """
        退出到主菜单
        """
        logger.info("开始退出到主菜单操作")
        # 读取操作序列
        event_list = self._menu_config["quit_to_title"]["event"]
        # 执行操作
        for event in event_list:
            self._input.run_action(event["action"], event["key"], float(event["delay"]), float(event["duration"]))
        logger.info("退出到主菜单操作完成")


    # 重新加载存档
    def reload_save(self):
        """
        重新加载存档
        """
        logger.info("开始重新加载存档操作")
        # 读取操作序列
        event_list = self._menu_config["reload_save"]["event"]
        # 执行操作
        for event in event_list:
            self._input.run_action(event["action"], event["key"], float(event["delay"]), float(event["duration"]))

    # 前往指定boss房前
    def goto_boss_room(self, boss_name: str):
        """
        前往指定boss房前
        """
        if boss_name not in self._menu_config["godhome_boss_room"].keys():
            raise ValueError(f"未知boss: {boss_name}")
        logger.info(f"开始前往{boss_name}房前操作")
        # 读取操作序列
        event_list = self._menu_config["godhome_boss_room"][boss_name]["event"]
        # 执行操作
        for event in event_list:
            self._input.run_action(event["action"], event["key"], float(event["delay"]), float(event["duration"]))
        logger.info(f"前往{boss_name}房前操作完成")

    def reset_game(self):
        """
        重置游戏
        """
        self.quit_to_title()
        self.reload_save()

if __name__ == "__main__":
    config = load_config()
    input_controller = InputController(config)
    menu = Menu(input_controller, config)
    time.sleep(5)
    menu.goto_boss_room("GG_Hornet_1")
