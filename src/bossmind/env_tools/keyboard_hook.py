import time
import pynput
import logging
import threading

from bossmind.config import load_config
from bossmind.data.schema import ButtonStates, KeyStates

logger = logging.getLogger(__name__)


class KeyboardHook:
    def __init__(self, config):
        self._config = config
        self._key_dict = None  # 按键字典
        self._logic_key_dict = None  # 逻辑键字典
        self._get_config()
        self._state = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "jump": False,
            "attack": False,
            "dash": False,
            "super_dash": False,
            "dream_knife": False,
            "heal": False,
            "skill": False,
            "tab": False,
        }
        self._edge = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "jump": False,
            "attack": False,
            "dash": False,
            "super_dash": False,
            "dream_knife": False,
            "heal": False,
            "skill": False,
            "tab": False,
        }
        self._listener = None
        self._lock = threading.Lock()
        self.is_ok = False

    # 工具函数
    # 配置
    def _get_config(self):
        """
        用于加载配置文件，获取按键配置
        """
        self._key_dict = self._config.keybinds
        self._logic_key_dict = {v: k for k, v in self._key_dict.items()}

    # 监听键转token
    def _key_to_token(self, key):
        # 读取字符按键
        try:
            if key.char is not None:
                return key.char.lower()
        # 读取特殊按键
        except AttributeError:
            if key == pynput.keyboard.Key.shift:
                return "lshift"
            elif key == pynput.keyboard.Key.space:
                return "space"
            elif key == pynput.keyboard.Key.tab:
                return "tab"
            else:
                return None

    # token转逻辑键
    def _token_to_logic_key(self, token):
        return self._logic_key_dict.get(token, None)

    # 按键按下
    def _on_press(self, key):
        # 如果按键token为f12, 则返回False，停止监听
        if key == pynput.keyboard.Key.f12:
            self.stop()
            return False
        # 用于collect准备
        if key == pynput.keyboard.Key.f11:
            self.is_ok = True
            return
        # 获取按键token
        token = self._key_to_token(key)
        # 如果按键token为空, 则返回
        if token is None:
            return
        # 获取逻辑键
        logic_key = self._token_to_logic_key(token)
        # 如果逻辑键为空, 则返回
        if logic_key is None:
            return
        # 如果逻辑键不在_state中，则返回
        if logic_key not in self._state:
            return
        # 更新状态
        with self._lock:
            if not self._state[logic_key]:      # 刚才是松开的
                self._edge[logic_key] = True    # 记一次「按下」
            self._state[logic_key] = True       # 再更新 held

    # 按键释放
    def _on_release(self, key):
        token = self._key_to_token(key)
        if token is None:
            return
        logic_key = self._token_to_logic_key(token)
        if logic_key is None:
            return
        # 如果逻辑键不在_state中，则返回
        if logic_key not in self._state:
            return
        with self._lock:
            self._state[logic_key] = False

    def _get_listener(self):
        """
        获取键盘监听器
        """
        self._listener = pynput.keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )

    # 判断是否在运行
    @property
    def is_running(self) -> bool:
        return self._listener is not None and self._listener.running

    # 业务函数
    def start(self):
        if self.is_running:
            return   # 已经在跑
        self._get_listener()
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        """
        停止键盘监听, 重置状态
        """
        try:
            if self.is_running:
                self._listener.stop()
        finally:
            with self._lock:
                for k in self._state:
                    self._state[k] = False
                for k in self._edge:
                    self._edge[k] = False
            self._listener = None
            self.is_ok = False
    
    def snapshot(self):
        """
        获取当前状态快照
        """
        with self._lock:
            held = ButtonStates(**dict(self._state))
            pressed = ButtonStates(**dict(self._edge))
            for k in self._edge:
                self._edge[k] = False
            return KeyStates(held=held, pressed=pressed)


if __name__ == "__main__":
    config = load_config()
    keyboard_hook = KeyboardHook(config)
    keyboard_hook.start()
    try:
        while keyboard_hook.is_running:
            print(keyboard_hook.snapshot())
            time.sleep(0.02)
    except KeyboardInterrupt:
        keyboard_hook.stop()
