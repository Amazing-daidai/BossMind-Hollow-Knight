import logging

import pymem

from bossmind.config import load_config
from bossmind.data.schema import PlayerStates

logger = logging.getLogger(__name__)


class PlayerInfo:
    """
    用于管理与游戏进程的连接和内存的读取
    """
    
    def __init__(self, config):
        self._process_name = None  # 进程名
        self._module_base = None  # 模块基址
        self._base_offset = None  # 基址偏移
        self._position_base_offset = None  # 位置基址偏移
        self._position_offsets = None  # 位置偏移链
        self._position_x_offset = None  # x偏移
        self._position_y_offset = None  # y偏移
        self._offsets = None  # 偏移链
        self._hp_offset = None  # 血量偏移
        self._soul_offset = None  # 灵魂偏移
        self._max_hp_offset = None  # 最大血量偏移
        self._pm = None  # pymem对象
        self._hp_addr = None  # 血量地址
        self._soul_addr = None  # 灵魂地址
        self._max_hp_addr = None  # 最大血量地址
        self._position_x_addr = None  # x地址
        self._position_y_addr = None  # y地址
        self._config = config
        self._get_config()


    # 工具函数
    # 配置
    def _get_config(self):
        """
        用于加载配置文件，获取地址信息，并赋值给私有属性
        """
        self._process_name = self._config.process_name
        self._module_base = self._config.player_info["module_base"]
        self._base_offset = self._config.player_info["base_offset"]
        self._offsets = self._config.player_info["offsets"]
        self._hp_offset = self._config.player_info["hp_offset"]
        self._max_hp_offset = self._config.player_info["max_hp_offset"]
        self._soul_offset = self._config.player_info["soul_offset"]
        self._position_base_offset = self._config.player_position["base_offset"]
        self._position_offsets = self._config.player_position["offsets"]
        self._position_x_offset = self._config.player_position["x_offset"]
        self._position_y_offset = self._config.player_position["y_offset"]

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
        self._soul_addr = None
        self._max_hp_addr = None
        self._position_x_addr = None
        self._position_y_addr = None

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

    # 通用读取int数据函数
    def _get_int_data_once(self, addr_name: str, final_offset: int):
        """
        可用于hp，soul，max_hp的读取
        """
        try:
            # 解析地址链
            if getattr(self, addr_name) is None:
                setattr(self, addr_name, self._resolve_pointer_chain(
                    self._pm,
                    self._module_base,
                    self._base_offset,
                    self._offsets,
                    final_offset,
                ))
            result = self._pm.read_int(getattr(self, addr_name))
            return result
        except Exception as e:
            logger.debug(f"读取数据失败: {e}")
            return None

    # 通用读取float数据函数
    def _get_float_data_once(self, addr_name: str, final_offset: int):
        """
        可用于x，y的读取
        """
        try:
            # 解析地址链
            if getattr(self, addr_name) is None:
                setattr(self, addr_name, self._resolve_pointer_chain(
                    self._pm,
                    self._module_base,
                    self._position_base_offset,
                    self._position_offsets,
                    final_offset,
                ))
            result = self._pm.read_float(getattr(self, addr_name))
            return result
        except Exception as e:
            logger.debug(f"读取数据失败: {e}")
            return None

    def _get_player_hp(self, max_hp:int):
        """
        用于获取玩家血量
        """
        if self._pm is None:
            self.attach()
        try:
            # 读取血量
            hp = self._get_int_data_once("_hp_addr", self._hp_offset)
            if hp is None:
                # 清理地址，重试一次
                self._clean_addr()
                hp = self._get_int_data_once("_hp_addr", self._hp_offset)
            if 0 <= hp <= max_hp:
                return hp
            else:
                self._clean_addr()
                return None
        except Exception as e:
            self._clean_addr()
            logger.warning(f"读取数据失败: {e}")
            return None

    def _get_player_max_hp(self):
        """
        获取玩家最大血量
        """
        if self._pm is None:
            self.attach()
        try:
            # 读取最大血量
            max_hp = self._get_int_data_once("_max_hp_addr", self._max_hp_offset)
            if max_hp is None:
                # 清理地址，重试一次
                self._clean_addr()
                max_hp = self._get_int_data_once("_max_hp_addr", self._max_hp_offset)
            if max_hp == self._config.player_info["max_hp"]:
                return max_hp
            else:
                self._clean_addr()
                raise ValueError("最大血量有误，请检查地址链")
        except Exception as e:
            logger.warning(f"读取数据失败: {e}")
            self._clean_addr()
            return None

    def _get_player_soul(self):
        """
        获取玩家灵魂
        """
        if self._pm is None:
            self.attach()
        try:
            # 读取灵魂
            soul = self._get_int_data_once("_soul_addr", self._soul_offset)
            if soul is None:
                # 清理地址，重试一次
                self._clean_addr()
                soul = self._get_int_data_once("_soul_addr", self._soul_offset)
            return soul
        except Exception as e:
            logger.warning(f"读取数据失败: {e}")
            self._clean_addr()
            return None
    
    def _get_x(self):
        """
        获取玩家x坐标
        """
        if self._pm is None:
            self.attach()
        try:
            # 读取x
            x = self._get_float_data_once("_position_x_addr", self._position_x_offset)
            if x is None:
                # 清理地址，重试一次
                self._clean_addr()
                x = self._get_float_data_once("_position_x_addr", self._position_x_offset)
            return x
        except Exception as e:
            logger.warning(f"读取数据失败: {e}")
            self._clean_addr()
            return None
    
    def _get_y(self):
        """
        获取玩家y坐标
        """
        if self._pm is None:
            self.attach()
        try:
            # 读取y
            y = self._get_float_data_once("_position_y_addr", self._position_y_offset)
            if y is None:
                # 清理地址，重试一次
                self._clean_addr()
                y = self._get_float_data_once("_position_y_addr", self._position_y_offset)
            return y
        except Exception as e:
            logger.warning(f"读取数据失败: {e}")
            self._clean_addr()
            return None

    def get_player_states(self):
        """
        获取玩家状态，先获取hp，max_hp，soul，x，y
        """
        max_hp = self._get_player_max_hp()
        if max_hp is None:
            max_hp_for_check = self._config.player_info["max_hp"]   # 仅作上界
            # PlayerStates.max_hp 仍可写 None（表示内存没读到）
        else:
            max_hp_for_check = max_hp
        hp = self._get_player_hp(max_hp_for_check)
        soul = self._get_player_soul()  # 使用hp和max_hp已经校验地址链正确性，灵魂值暂不增加额外校验
        x = self._get_x()
        y = self._get_y()
        return PlayerStates(hp=hp, max_hp=max_hp, soul=soul, x=x, y=y)


    def get_is_battle(self):
        """
        判读是否在战斗中
        """
        if True:
            return True
        else:
            return False


if __name__ == "__main__":
    config = load_config()
    player_info = PlayerInfo(config)
    player_info.get_pid()
