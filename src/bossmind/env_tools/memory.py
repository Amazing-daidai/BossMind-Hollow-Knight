import logging

import pymem
import yaml

from bossmind.paths import GAME_INFO_FILE

logger = logging.getLogger(__name__)


class PlayerInfo:
    """
    用于管理与游戏进程的连接和内存的读取
    """
    
    def __init__(self):
        self._process_name = None  # 进程名
        self._module_base = None  # 模块基址
        self._base_offset = None  # 基址偏移
        self._offsets = None  # 偏移链
        self._hp_offset = None  # 血量偏移
        self._pm = None  # pymem对象
        self._hp_addr = None  # 血量地址
        self._get_config()

    # 工具函数
    # 配置
    def _get_config(self):
        """
        用于加载配置文件，获取地址信息，并赋值给私有属性
        """
        # 校验配置文件是否存在
        if not GAME_INFO_FILE.exists():
            raise FileNotFoundError(f"配置文件不存在: {GAME_INFO_FILE}")
        # 读取配置文件，获取基址与血量偏移
        with open(GAME_INFO_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            self._process_name = config["process_name"]
            player_info = config["player_info"]
            self._module_base = player_info["module_base"]
            self._base_offset = player_info["base_offset"]
            self._offsets = player_info["offsets"]
            self._hp_offset = player_info["hp_offset"]

    # 进程处理
    def _get_pm(self):
        """
        用于获取pm对象
        """
        try:
            self._pm = pymem.Pymem(self._process_name)
        except pymem.exception.ProcessNotFound:
            raise ValueError(f"未找到进程: {self._process_name}")
        except pymem.exception.CouldNotOpenProcess:
            raise ValueError(f"打开进程失败: {self._process_name}")

    def _clean_addr(self):
        """
        清除缓存地址
        """
        self._hp_addr = None

    def _close_pm(self):
        """
        关闭pm对象
        """
        try:
            self._pm.close_process()
        except Exception as e:
            raise ValueError(f"关闭进程失败: {e}")

    # 解析地址
    def _resolve_pointer_chain(
        self, pm, module_base: str, base_offset: int, offsets: list[int], final_offset: int
    ) -> int:
        """
        解析地址链，获取最终地址
        """
        try:
            # 获取基址地址
            module_addr = int(
                pymem.process.module_from_name(pm.process_handle, module_base).lpBaseOfDll
            )
            addr = int(pm.read_ulonglong(module_addr + int(base_offset)))
            # 遍历偏移链
            for i, offset in enumerate(offsets):
                # 先偏移地址，再读取8字节，获取指针。
                addr = int(pm.read_ulonglong(int(addr + int(offset))))
                # 判断偏移链是否断裂
                if addr == 0:
                    raise ValueError(f"偏移链断裂: {hex(addr)}，当前为第{i + 1}层")
            # 返回最终地址
            return int(addr) + int(final_offset)
        except Exception as e:
            raise ValueError(f"解析地址链失败: {e}")

    # 业务函数
    def attach(self):
        """
        用于获取并保持连接到游戏进程
        """
        if self._pm is not None:
            logger.debug("进程已连接，无需重新连接")
            return
        try:
            self._get_pm()
        except Exception as e:
            raise ValueError(f"获取并保持连接到游戏进程失败: {e}")

    def detach(self):
        """
        断开与游戏进程的连接，清除缓存地址
        """
        self._clean_addr()
        if self._pm is not None:
            self._close_pm()
            self._pm = None
            logger.debug("进程已关闭，缓存已清除")
        else:
            logger.debug("进程未连接，缓存已清除")

    def get_pid(self):
        """
        用于获取进程ID
        """
        if self._pm is None:
            self.attach()
        return self._pm.process_id

    def get_player_hp(self):
        """
        用于获取玩家血量
        """
        if self._pm is None:
            self.attach()
        try:
            # 解析地址链，获取hp地址
            if self._hp_addr is None:
                self._hp_addr = self._resolve_pointer_chain(
                    self._pm,
                    self._module_base,
                    self._base_offset,
                    self._offsets,
                    self._hp_offset,
                )
            # 读取血量
            hp = self._pm.read_int(self._hp_addr)
            return hp
        except Exception as e:
            raise ValueError(f"获取玩家血量失败: {e}")


if __name__ == "__main__":
    player_info = PlayerInfo()
    player_info.get_pid()
