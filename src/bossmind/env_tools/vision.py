import ctypes
import logging

import mss
from win32 import win32gui

logger = logging.getLogger(__name__)

_DPI_DONE = False


class VisionError(RuntimeError):
    """窗口几何 / 截图异常（采集侧应终止本局）。"""

# 设置高DPI感知
def _ensure_dpi_awareness() -> None:
    """与 mss 对齐：优先 PER_MONITOR；只设一次，避免与 mss 内部调用互相抢锁。"""
    global _DPI_DONE
    if _DPI_DONE:
        return
    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            logger.warning("设置 DPI 感知失败，截图坐标在缩放≠100% 时可能偏移")
    _DPI_DONE = True


class Vision:
    def __init__(self, config):
        # 设置高DPI感知
        _ensure_dpi_awareness()
        self._raw_region = None  # 采集区域
        self._real_region = None  # 实际采集区域
        self._window_title = None  # 窗口标题
        self._hwnd = None  # 窗口句柄
        self._mss = None  # mss实例
        self._config = config
        self._get_config()

    def _get_config(self):
        self._process_name = self._config.process_name
        self._raw_region = self._config.collect["vision_region"]
        self._window_title = self._config.window_title

    # 获取窗口句柄
    def _get_window(self):
        self._hwnd = win32gui.FindWindow(None, self._window_title)
        if not self._hwnd:
            raise VisionError(f"未找到窗口: '{self._window_title}'")

    # 判断窗口是否最小化
    def _check_window(self):
        if not self._hwnd or not win32gui.IsWindow(self._hwnd):
            self._get_window()
        if win32gui.IsIconic(self._hwnd):
            raise VisionError("窗口已最小化")

    # 获取真实采集区域
    def _get_real_region(self):
        # 获取游戏窗口左上角坐标
        abs_x, abs_y = win32gui.ClientToScreen(self._hwnd, (0, 0))
        self._real_region = {
            "left": abs_x + self._raw_region["left"],
            "top": abs_y + self._raw_region["top"],
            "width": self._raw_region["width"],
            "height": self._raw_region["height"],
        }

    # 获取mss实例
    def _get_mss(self):
        if self._mss is None:
            self._mss = mss.mss()

    # 采集前准备
    def pre_capture(self):
        self._get_window()
        self._check_window()
        self._get_real_region()
        self._get_mss()

    # 采集图片
    def capture(self):
        if self._mss is None:
            self.pre_capture()
        # 每帧检测窗口并更新真实采集区域
        self._check_window()
        self._get_real_region()
        # 使用grab获取数据
        shot = self._mss.grab(self._real_region)
        # 判断图片尺寸是否符合预期
        expect = (self._raw_region["width"], self._raw_region["height"])
        if tuple(shot.size) != expect:
            raise VisionError(f"截图尺寸异常: got={shot.size} expect={expect}")
        return shot

    # 停止采集，销毁mss实例
    def stop(self):
        if self._mss is not None:
            try:
                self._mss.close()
            finally:
                self._mss = None


if __name__ == "__main__":
    from bossmind.config import load_config

    config = load_config()
    vision = Vision(config)
    vision.pre_capture()
    image = vision.capture()
    mss.tools.to_png(image.rgb, image.size, output="image.png")
