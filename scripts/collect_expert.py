import time

from datetime import datetime

from bossmind.env_tools.session import GameSession
from bossmind.env_tools.keyboard_hook import KeyboardHook
from bossmind.config import load_config
from bossmind.data.writer import EpisodeWriter
from bossmind.utils import git_sha, config_hash, percentile_ns

class CollectExpert:
    def __init__(self, batch_id: str, boss_name: str):
        self.batch_id = batch_id
        self.eps_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + boss_name
        self.boss_name = boss_name
        self._config = load_config()
        self._session = GameSession(self._config)
        self._keyboard_hook = KeyboardHook(self._config)
        self._writer = None
        self._recording_state = False
        self._end_reason = "aborted"
        
    def _pre_collect(self):
        """
        收集前的准备，连接进程，准备写入器，打开键盘监听
        """
        print("请确认打开游戏并已经加载存档")
        # 确认按钮
        print("请按下F11键确认")
        # 开启键盘监听
        self._keyboard_hook.start()
        while True:
            if self._keyboard_hook.is_ok:
                break
            if not self._keyboard_hook.is_running:
                print("键盘监听已停止，终止收集")
                return False
            time.sleep(0.1)
        # 连接游戏进程
        self._session.attach()
        # 先获取一次信息，提前解析地址链(如果未进入boss房，尝试解析boss信息可能会报错，先这样，后面结合bossinfo再改)
        self._session.get_observation()
        # 创建写入器
        self._writer = EpisodeWriter(self.batch_id, self.eps_id, self.boss_name)
        self._writer.pre_write()
        print("收集准备完成")
        return True

    def _collect_data(self):
        """
        收集信息
        """
        c = self._config.collect
        # 收集帧率
        INTERVAL_NS = 1_000_000_000 // c["sample_hz"]
        frame_idx = 0
        # 防止抖动
        false_streak = 0
        DEBOUNCE = 3
        # 追帧参数
        MAX_LAG_PERIODS = 2
        n_dropped = 0
        MAX_DROPPED = c["max_dropped"]
        # 失焦上限
        MAX_FOCUS_LOST = c["max_focus_lost"]
        n_loss = 0
        # 读取异常
        MAX_HP_READ_FAIL = c["max_hp_read_fail"]
        # 最长时间
        MAX_DURATION_NS = int(c["max_episode_s"] * 1e9)
        # finally 可能在等战斗阶段就执行，先初始化
        started_at_unix_ns = time.time_ns()
        dt_list: list[int] = []

        try:
            # 判断是否进入战斗
            while True:
                if self._session.get_is_battle():
                    self._recording_state = True
                    break
                if not self._keyboard_hook.is_running:
                    print("键盘监听已停止，终止收集")
                    self._end_reason = "aborted"
                    self._recording_state = False
                    break
                time.sleep(0.01)
            # 收集信息
            next_ns = start_ns = time.perf_counter_ns()
            started_at_unix_ns = time.time_ns()
            prev_t_abs_ns = None
            while self._recording_state:
                # 记录当前时间
                now = time.perf_counter_ns()
                # 检查是否严重落后
                if now > next_ns + MAX_LAG_PERIODS * INTERVAL_NS:
                    behind = now - next_ns
                    skipped = behind // INTERVAL_NS
                    n_dropped += skipped
                    next_ns = now
                    print(f"严重落后，跳过{skipped}帧")
                # 核心记拍器
                if now < next_ns:
                    time.sleep((next_ns - now) / 1e9)
                # 采集数据
                t_abs_ns = time.perf_counter_ns()
                # 计算两帧实际间隔
                if prev_t_abs_ns is not None:
                    dt_list.append(t_abs_ns - prev_t_abs_ns)
                prev_t_abs_ns = t_abs_ns
                # 记录延迟
                lag_ns = t_abs_ns - next_ns
                # 记录相对时间
                t_rel_ns = t_abs_ns - start_ns
                # 获取游戏及键盘数据
                observation = self._session.get_observation()
                keystates = self._keyboard_hook.snapshot()
                # 拼接事件
                event = {
                    "t_ns": t_abs_ns,
                    "t_rel_ns": t_rel_ns,
                    "lag_ns": lag_ns,
                    "frame_idx": frame_idx,
                    "eps_id": self.eps_id,
                    "observation": observation.model_dump(),
                    "key_states": keystates.model_dump()
                }
                # 写数据
                self._writer.write_event(event)
                # 更新计数器
                frame_idx += 1
                # 更新next_ns
                next_ns += INTERVAL_NS

                # 结束判断
                # f12终止
                if not self._keyboard_hook.is_running:
                    self._end_reason = "aborted"
                    break
                # 死亡
                if observation.player.hp is not None and observation.player.hp <= 0:
                    self._end_reason = "death"
                    break
                # 超时
                if t_rel_ns > MAX_DURATION_NS:
                    self._end_reason = "timeout"
                    break
                # 跳过帧过多
                if n_dropped >= MAX_DROPPED:
                    self._end_reason = "discard"
                    break
                if observation.window_focused is False:
                    n_loss += 1
                    if n_loss >= MAX_FOCUS_LOST:
                        self._end_reason = "discard"
                        break
                else:
                    n_loss = 0
                # 读取异常
                if observation.read_error_streak >= MAX_HP_READ_FAIL:
                    self._end_reason = "discard"
                    break
                # 正常退出
                if not observation.is_battle:
                    false_streak += 1
                    if false_streak >= DEBOUNCE:
                        self._end_reason = "win"
                        self._recording_state = False
                        break
                else:
                    false_streak = 0
        except Exception:
            self._end_reason = "error"
            raise
        finally:
            if self._writer is not None:
                dt_p50 = percentile_ns(dt_list, 0.50)
                dt_p95 = percentile_ns(dt_list, 0.95)
                hz_meas = (1e9 / dt_p50) if dt_p50 else None
                self._writer.close(
                    self._end_reason,
                    n_dropped,
                    started_at_unix_ns=started_at_unix_ns,
                    code_git_sha=git_sha(),
                    config_hash=config_hash(),
                    sample_hz_nominal=self._config.collect["sample_hz"],
                    sample_hz_measured=hz_meas,
                    dt_p50_ns=dt_p50,
                    dt_p95_ns=dt_p95
                )
            
    def start_collect(self):
        """
        开始收集
        """
        try:
            if not self._pre_collect():
                return 
            self._collect_data()
        finally:
            self._end_collect()

    def _end_collect(self):
        """
        结束收集，关闭所有进程
        """
        self._writer = None
        self._keyboard_hook.stop()
        self._session.detach()
        print("收集结束, 所有进程已关闭")

        
if __name__ == "__main__":
    config = load_config()
    batch_id = "smoke_1"
    if not (batch_id.startswith("smoke_") or batch_id.startswith("pipeline_")):
        raise SystemExit(
            f"拒绝启动：batch_id={batch_id!r} 必须以 smoke_ 或 pipeline_ 开头"
        )
    collect_expert = CollectExpert(batch_id=batch_id, boss_name=config.collect["boss"])
    collect_expert.start_collect()
