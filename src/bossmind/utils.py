import hashlib
import subprocess
import ctypes

from bossmind.paths import GAME_INFO_FILE, PROJECT_ROOT

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

# 判断窗口焦点是否在游戏上
def is_window_focused(game_pid: int) -> bool:
    # 获取窗口pid
    window_pid = get_focused_window_pid()
    # 判断是否相同
    return window_pid is not None and window_pid == game_pid




if __name__ == "__main__":
    print(git_sha())
