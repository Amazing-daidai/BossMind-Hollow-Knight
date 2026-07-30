import time
import pynput
import logging
import yaml
import threading

from bossmind.paths import GAME_INFO_FILE

logger = logging.getLogger(__name__)


class KeyboardHook:
    def __init__(self):
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
        }
        self._listener = None
        self._lock = threading.Lock()
        self.is_running = False

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
            self._key_dict = config["keybinds"]
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
        # 更新状态
        with self._lock:
            self._state[logic_key] = True

    # 按键释放
    def _on_release(self, key):
        token = self._key_to_token(key)
        if token is None:
            return
        logic_key = self._token_to_logic_key(token)
        if logic_key is None:
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

    # 业务函数
    def start(self):
        if self.is_running:
            return   # 已经在跑
        self._get_listener()
        self._listener.daemon = True
        self._listener.start()
        self.is_running = True

    def stop(self):
        """
        停止键盘监听, 重置状态
        """
        if self.is_running:
            self._listener.stop()
            with self._lock:
                for k in self._state:
                    self._state[k] = False
            self._listener = None
            self.is_running = False
    
    def snapshot(self):
        """
        获取当前状态快照
        """
        with self._lock:
            return dict(self._state)


if __name__ == "__main__":
    keyboard_hook = KeyboardHook()
    keyboard_hook.start()
    try:
        while keyboard_hook.is_running:
            print(keyboard_hook.snapshot())
            time.sleep(0.02)
    except KeyboardInterrupt:
        keyboard_hook.stop()
