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
        self._facing_base_offset = None  # 朝向偏移
        self._facing_offsets = None  # 朝向偏移链
        self._facing_final_offset = None  # 朝向偏移
        # scene_name：GameManager.sceneName 指针槽（静态链见 game_info.yaml）
        self._scene_name_base_offset = None
        self._scene_name_offsets = None
        self._scene_name_ptr_offset = None
        self._scene_name_length_offset = None  # Unity System.String 长度偏移 +0x10
        self._scene_name_chars_offset = None   # Unity System.String UTF-16 字符 +0x14
        self._scene_name_module_base = None
        # game_state：GameManager.gameState（与 scene_name 同静态链，final 为 +0x18C）
        self._game_state_module_base = None
        self._game_state_base_offset = None
        self._game_state_offsets = None
        self._game_state_offset = None
        self._game_state_labels = None  # int 枚举 → PLAYING/PAUSED/CUTSCENE 字符串
        # boss_hp：按 scene_name 选 boss_info 链；换房时清缓存
        self._boss_hp_addr = None
        self._boss_hp_scene = None       # 上次读取 boss_hp 时的场景名
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
        self._facing_addr = None  # 朝向地址
        self._scene_name_slot_addr = None  # sceneName 指针槽缓存
        self._game_state_addr = None       # gameState int 字段缓存
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
        self._facing_base_offset = self._config.player_facing["base_offset"]
        self._facing_offsets = self._config.player_facing["offsets"]
        self._facing_final_offset = self._config.player_facing["facing_offset"]
        # scene_name / game_state 共用 player_info 同根静态链（0x01F28838），final 偏移不同
        sn = self._config.scene_name
        self._scene_name_module_base = sn["module_base"]
        self._scene_name_base_offset = sn["base_offset"]
        self._scene_name_offsets = sn["offsets"]
        self._scene_name_ptr_offset = sn["name_ptr_offset"]
        self._scene_name_length_offset = sn["string_length_offset"]
        self._scene_name_chars_offset = sn["string_chars_offset"]
        # game_state 与 scene_name 共用 UnityPlayer+0x01F28838 根链，仅 final_offset 不同
        gs = self._config.game_state
        self._game_state_module_base = gs["module_base"]
        self._game_state_base_offset = gs["base_offset"]
        self._game_state_offsets = gs["offsets"]
        self._game_state_offset = gs["state_offset"]
        self._game_state_labels = {
            gs["playing_value"]: "PLAYING",    # 实测 4：能操控
            gs["paused_value"]: "PAUSED",      # 实测 5：ESC 暂停
            gs["cutscene_value"]: "CUTSCENE",  # 实测 3：白屏过场
            # 进门偶发 6 等未知值：原样 str(value)，不算 PLAYING
        }

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
        清除缓存地址（含 scene/game_state/boss_hp，换房或链断裂后重解析）
        """
        self._hp_addr = None
        self._soul_addr = None
        self._max_hp_addr = None
        self._position_x_addr = None
        self._position_y_addr = None
        self._facing_addr = None
        self._scene_name_slot_addr = None
        self._game_state_addr = None
        # boss 链按场景缓存；读档/换房后必须清掉，否则会读到别的 HealthManager
        self._boss_hp_addr = None
        self._boss_hp_scene = None

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
    def _get_float_data_once(self, addr_name: str, base_offset: int, offsets: list[int], final_offset: int):
        """
        可用于player的x，y，facing的读取
        """
        try:
            # 解析地址链
            if getattr(self, addr_name) is None:
                setattr(self, addr_name, self._resolve_pointer_chain(
                    self._pm,
                    self._module_base,
                    base_offset,
                    offsets,
                    final_offset,
                ))
            result = self._pm.read_float(getattr(self, addr_name))
            return result
        except Exception as e:
            logger.debug(f"读取数据失败: {e}")
            return None

    def _read_unity_string(self, string_obj: int) -> str | None:
        """读取 Unity Mono System.String（UTF-16LE；length@+0x10，chars@+0x14）。"""
        try:
            length = self._pm.read_int(string_obj + self._scene_name_length_offset)
            if length <= 0 or length > 128:
                return None
            raw = self._pm.read_bytes(string_obj + self._scene_name_chars_offset, length * 2)
            return raw.decode("utf-16-le", errors="ignore")
        except Exception as e:
            logger.debug(f"读取字符串失败: {e}")
            return None

    def _get_scene_name_slot_once(self) -> int | None:
        """解析静态链，得到 GameManager.sceneName 的 8 字节指针槽地址（非字符串本体）。"""
        try:
            if self._scene_name_slot_addr is None:
                self._scene_name_slot_addr = self._resolve_pointer_chain(
                    self._pm,
                    self._scene_name_module_base,
                    self._scene_name_base_offset,
                    self._scene_name_offsets,
                    self._scene_name_ptr_offset,
                )
            return self._scene_name_slot_addr
        except Exception as e:
            logger.debug(f"解析场景名地址失败: {e}")
            return None

    def get_scene_name(self) -> str | None:
        """
        当前场景名。链终点是指针槽 → read_u64 → Unity 字符串对象 → UTF-16。
        """
        if self._pm is None:
            self.attach()
        try:
            slot = self._get_scene_name_slot_once()
            if slot is None:
                self._clean_addr()
                slot = self._get_scene_name_slot_once()
            if slot is None:
                return None
            string_obj = int(self._pm.read_ulonglong(slot))
            if string_obj == 0:
                self._scene_name_slot_addr = None
                return None
            scene_name = self._read_unity_string(string_obj)
            if scene_name is None:
                self._scene_name_slot_addr = None
            return scene_name
        except Exception as e:
            logger.warning(f"读取场景名失败: {e}")
            self._clean_addr()
            return None

    def _get_game_state_addr_once(self) -> int | None:
        """解析静态链，得到 GameManager.gameState 字段地址（直接 read_int）。"""
        try:
            if self._game_state_addr is None:
                self._game_state_addr = self._resolve_pointer_chain(
                    self._pm,
                    self._game_state_module_base,
                    self._game_state_base_offset,
                    self._game_state_offsets,
                    self._game_state_offset,
                )
            return self._game_state_addr
        except Exception as e:
            logger.debug(f"解析 game_state 地址失败: {e}")
            return None

    def _label_game_state(self, value: int) -> str:
        """将 gameState 整型映射为 PLAYING/PAUSED/CUTSCENE，未知值保留数字字符串。"""
        return self._game_state_labels.get(value, str(value))

    def get_game_state(self) -> str | None:
        """
        游戏状态标签。未知 int（如进门瞬间的 6）返回 str(数字)，供调试。
        """
        if self._pm is None:
            self.attach()
        try:
            addr = self._get_game_state_addr_once()
            if addr is None:
                self._clean_addr()
                addr = self._get_game_state_addr_once()
            if addr is None:
                return None
            value = self._pm.read_int(addr)
            if value not in self._game_state_labels:
                logger.debug(f"未知 game_state 值: {value}")
            return self._label_game_state(value)
        except Exception as e:
            logger.warning(f"读取 game_state 失败: {e}")
            self._clean_addr()
            return None

    def _get_boss_cfg(self, scene_name: str) -> dict | None:
        """boss_info 的 key 与 scene_name 一致（如 GG_Hornet_1）；未配置则返回 None。"""
        boss_cfg = self._config.boss_info.get(scene_name)
        if not boss_cfg or "hp_offset" not in boss_cfg:
            return None
        return boss_cfg

    def _get_boss_hp_addr_once(self, boss_cfg: dict) -> int | None:
        """解析该 Boss 的静态链，得到 HealthManager.hp 字段地址（+0x148）。"""
        try:
            if self._boss_hp_addr is None:
                self._boss_hp_addr = self._resolve_pointer_chain(
                    self._pm,
                    boss_cfg["module_base"],
                    boss_cfg["base_offset"],
                    boss_cfg["offsets"],
                    boss_cfg["hp_offset"],
                )
            return self._boss_hp_addr
        except Exception as e:
            logger.debug(f"解析 boss_hp 地址失败: {e}")
            return None

    def get_boss_hp(self) -> int | None:
        """
        Boss 血量。仅当 scene_name 在 boss_info 且已配置链时读取；
        换场景会清 _boss_hp_addr，避免跨 Boss 房误用 Hornet 链。
        """
        if self._pm is None:
            self.attach()
        scene_name = self.get_scene_name()
        boss_cfg = self._get_boss_cfg(scene_name) if scene_name else None
        if boss_cfg is None:
            self._boss_hp_addr = None
            self._boss_hp_scene = None
            return None
        if self._boss_hp_scene != scene_name:
            # 场景切换：丢弃旧 Boss 的 HealthManager 链
            self._boss_hp_addr = None
            self._boss_hp_scene = scene_name
        try:
            addr = self._get_boss_hp_addr_once(boss_cfg)
            if addr is None:
                self._boss_hp_addr = None
                addr = self._get_boss_hp_addr_once(boss_cfg)
            if addr is None:
                return None
            hp = self._pm.read_int(addr)
            # max_hp 为 Boss 满血上界（Hornet=900），用于过滤野指针；与当前血量无关
            max_hp = boss_cfg.get("max_hp")
            # 合理范围校验（Hornet 满血 900）；越界则清缓存，下次重解链
            if max_hp is not None and not (0 <= hp <= int(max_hp)):
                self._boss_hp_addr = None
                return None
            return hp
        except Exception as e:
            logger.warning(f"读取 boss_hp 失败: {e}")
            self._boss_hp_addr = None
            return None

    def get_is_battle(self) -> bool:
        """
        派生：PLAYING ∧ scene 在 boss_info ∧ boss_hp>0。
        暂停/过场/进门几帧的 game_state≠PLAYING 时为 False。
        """
        if self.get_game_state() != "PLAYING":
            return False
        scene_name = self.get_scene_name()
        if self._get_boss_cfg(scene_name) is None:
            return False
        boss_hp = self.get_boss_hp()
        return boss_hp is not None and boss_hp > 0

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
            x = self._get_float_data_once("_position_x_addr", self._position_base_offset, self._position_offsets, self._position_x_offset)
            if x is None:
                # 清理地址，重试一次
                self._clean_addr()
                x = self._get_float_data_once("_position_x_addr", self._position_base_offset, self._position_offsets, self._position_x_offset)
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
            y = self._get_float_data_once("_position_y_addr", self._position_base_offset, self._position_offsets, self._position_y_offset)
            if y is None:
                # 清理地址，重试一次
                self._clean_addr()
                y = self._get_float_data_once("_position_y_addr", self._position_base_offset, self._position_offsets, self._position_y_offset)
            return y
        except Exception as e:
            logger.warning(f"读取数据失败: {e}")
            self._clean_addr()
            return None

    def _get_facing(self):
        """
        获取玩家朝向（右=True，左=False）
        """
        if self._pm is None:
            self.attach()
        right_value = self._config.player_facing["right_value"]
        left_value = self._config.player_facing["left_value"]
        try:
            facing = self._get_float_data_once(
                "_facing_addr",
                self._facing_base_offset,
                self._facing_offsets,
                self._facing_final_offset,
            )
            if facing is None:
                self._clean_addr()
                facing = self._get_float_data_once(
                    "_facing_addr",
                    self._facing_base_offset,
                    self._facing_offsets,
                    self._facing_final_offset,
                )
            if facing is None:
                return None
            if abs(facing - right_value) < 1e-3:
                return True
            if abs(facing - left_value) < 1e-3:
                return False
            self._facing_addr = None
            logger.debug(f"朝向值异常: {facing}")
            return None
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
        facing = self._get_facing()
        return PlayerStates(player_hp=hp, max_hp=max_hp, soul=soul, player_x=x, player_y=y, player_facing_right=facing)


if __name__ == "__main__":
    config = load_config()
    player_info = PlayerInfo(config)
    player_info.get_pid()
