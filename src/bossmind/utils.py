import hashlib
import subprocess
import ctypes
import logging
import pymem

from pathlib import Path

from bossmind.paths import GAME_INFO_FILE, PROJECT_ROOT, LOGS_DIR

_FORMAT = "%(asctime)s - %(name)s - %(levelname)s: %(message)s"

# 获取当前git提交hash
def git_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
            cwd=PROJECT_ROOT,  # 在git仓库根目录下运行
        )
        return r.stdout.strip()
    except Exception:
        return "unknown"

# 获取yaml文件hash
def config_hash() -> str:
    return hashlib.sha256(GAME_INFO_FILE.read_bytes()).hexdigest()[:8]

# 计算p50, p95
def percentile_ns(values: list[int], p: float) -> int | None:
    if not values:
        return None
    s = sorted(values)
    # 简单算法即可，例如：
    k = int(round((len(s) - 1) * p))
    return s[k]

# 获取当前窗口pid
def get_focused_window_pid():
    # 加载 user32.dll
    user32 = ctypes.windll.user32
    
    # 获取前台窗口句柄
    hwnd = user32.GetForegroundWindow()
    
    if not hwnd:
        return None
        
    # 定义变量存储 PID
    pid = ctypes.c_ulong()
    
    # 调用 API 获取 PID
    # 第一个参数是句柄，第二个参数是指向 PID 变量的指针
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    return pid.value

def get_game_pid(process_name: str) -> int | None:
    """获取游戏进程pid

    Args:
        process_name (str): 进程名称

    Raises:
        ValueError: 未找到进程
        ValueError: 打开进程失败

    Returns:
        int | None: 进程pid
    """
    try:
        pm = pymem.Pymem(process_name)
    except pymem.exception.ProcessNotFound:
        raise ValueError(f"未找到进程: {process_name}")
    except pymem.exception.CouldNotOpenProcess:
        raise ValueError(f"打开进程失败: {process_name}")
    return pm.process_id

# 判断窗口焦点是否在游戏上
def is_window_focused(game_pid: int) -> bool:
    # 获取窗口pid
    window_pid = get_focused_window_pid()
    # 判断是否相同
    return window_pid is not None and window_pid == game_pid

def setup_logging(path: Path, level: int = logging.INFO) -> None:
    """设置日志配置，入口处设置一次即可

    Args:
        log_path (Path): 日志文件路径
        level (int, optional): 日志级别. Defaults to logging.INFO.
    """
    # 获取根logger
    root = logging.getLogger()
    if root.handlers:
        return  # 避免调两次叠出两份输出
    # 创建文件夹
    log_path = LOGS_DIR / path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # 设置日志级别
    root.setLevel(level)
    # 设置日志格式
    fmt = logging.Formatter(_FORMAT)
    # 终端输出handler
    console_h = logging.StreamHandler()  # stderr，终端看得到
    console_h.setFormatter(fmt)
    console_h.setLevel(level)
    # 文件输出handler
    file_h = logging.FileHandler(log_path, encoding="utf-8", mode="a")
    file_h.setFormatter(fmt)
    file_h.setLevel(level)
    # 添加handler
    root.addHandler(console_h)
    root.addHandler(file_h)

if __name__ == "__main__":
    print(git_sha())
