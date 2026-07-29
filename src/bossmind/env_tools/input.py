import time
import logging
import yaml
import pydirectinput

from bossmind.paths import GAME_INFO_FILE

# 日志
logger = logging.getLogger(__name__)

class InputController:
    """
    用于按键输入
    """
    def __init__(self):
        self._keybinds = None  # 按键字典
        pydirectinput.PAUSE = 0.03
        self._get_config()

    # 工具函数
    # 配置
    def _get_config(self):
        """
        用于加载配置文件，获取按键配置
        """
        # 校验配置文件是否存在
        if not GAME_INFO_FILE.exists():
            raise FileNotFoundError(f"配置文件不存在: {GAME_INFO_FILE}")
        # 读取配置文件，获取按键
        with open(GAME_INFO_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            self._keybinds = config["keybinds"]

    # 获取实际按键
    def _get_actual_key(self, name: str) -> str:
        """
        用于获取实际按键
        """
        try:
            return self._keybinds[name] 
        except KeyError:
            raise KeyError(f"按键{name}不存在")

    # 按下按键
    def press_key(self, name: str):
        """
        用于按下按键
        """
        key = self._get_actual_key(name)
        pydirectinput.keyDown(key)
        logger.debug(f"keyDown {name} ({key})")

    # 释放按键
    def release_key(self, name: str):
        """
        用于释放按键
        """
        key = self._get_actual_key(name)
        pydirectinput.keyUp(key)
        logger.debug(f"keyUp {name} ({key})")

    # 按下多少秒后抬起, 默认0.5秒
    def hold_key(self, name: str, seconds: float = 0.5):
        """
        用于按下按键多少秒后抬起
        """
        self.press_key(name)
        time.sleep(seconds)
        self.release_key(name)
    
    # 按一下并抬起按键
    def tap(self, name: str):
        """
        用于按一下并抬起按键
        """
        key = self._get_actual_key(name)
        pydirectinput.press(key)
        logger.debug(f"press {name} ({key})")

    # 执行具体操作
    def run_action(self, action: str, key: str, delay: float, duration: float = 1.0):
        """
        用于执行具体操作
        """
        if action == "press":
            self.press_key(key)
            time.sleep(delay)
        elif action == "tap":
            self.tap(key)
            time.sleep(delay)
        elif action == "release":
            self.release_key(key)
            time.sleep(delay)
        elif action == "hold":
            self.hold_key(key, duration)
            time.sleep(delay)
        else:
            raise ValueError(f"不支持的操作: {action}")

if __name__ == "__main__":
    input_controller = InputController()
    time.sleep(5)
    input_controller.tap("left")