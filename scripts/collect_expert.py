import time
from datetime import datetime

from bossmind.config import load_config
from bossmind.data.writer import EpisodeWriter
from bossmind.env_tools.keyboard_hook import KeyboardHook
from bossmind.env_tools.session import GameSession
from bossmind.env_tools.vision import Vision
from bossmind.utils import config_hash, git_sha, percentile_ns


class CollectExpert:
    def __init__(self, batch_id: str, boss_name: str):
        self.batch_id = batch_id
        self.eps_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + boss_name
        self.boss_name = boss_name
        self._config = load_config()
        self._session = GameSession(self._config)
        self._keyboard_hook = KeyboardHook(self._config)
        self._vision = Vision(self._config)
        self._writer = None
        self._recording_state = False
        self._end_reason = "aborted"

    def _pre_collect(self):
        """
        收集前的准备，连接进程，准备写入器，打开键盘监听
        """
        print("请确认打开游戏并已经加载存档")
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
        # 连接进程
        self._session.attach()
        # 先解析一次地址链
        self._session.get_observation()
        # 先校验窗口，再开写盘线程，避免 pre_write 后找窗失败泄漏线程
        self._vision.pre_capture()
        # 创建写入器
        c = self._config.collect
        self._writer = EpisodeWriter(
            self.batch_id,
            self.eps_id,
            self.boss_name,
            image_queue_size=30,
            image_ext=c.get("vision_format", "jpg"),
            jpeg_quality=int(c.get("vision_jpeg_quality", 85)),
        )
        # 写入前准备
        self._writer.pre_write()
        print("收集准备完成")
        return True

    def _collect_data(self):
        # 采集数据主逻辑
        # 配置
        c = self._config.collect
        # 采集间隔
        INTERVAL_NS = 1_000_000_000 // c["sample_hz"]
        # 采集帧索引
        frame_idx = 0
        # 胜利计数
        false_streak = 0
        # 胜利阈值
        DEBOUNCE = 3
        # 最大滞后周期
        MAX_LAG_PERIODS = 2
        # 丢弃帧数
        n_dropped = 0
        # 最大丢弃帧数
        MAX_DROPPED = c["max_dropped"]
        # 最大失焦帧数
        MAX_FOCUS_LOST = c["max_focus_lost"]
        # 失焦数
        n_loss = 0
        # 最大HP读取失败次数
        MAX_HP_READ_FAIL = c["max_hp_read_fail"]
        # 最大持续时间
        MAX_DURATION_NS = int(c["max_episode_s"] * 1e9)
        # 图像采集间隔
        VISION_INTERVAL_NS = int(1e9 / c["vision_hz"])
        # 初始采集时间
        last_vision_ns = -VISION_INTERVAL_NS
        # 最大图像丢弃帧数
        MAX_IMAGE_DROPPED = int(c.get("max_image_dropped", 3))
        # 开始时间
        started_at_unix_ns = time.time_ns()
        # 时间差列表
        dt_list: list[int] = []
        # 图像采集时间差列表
        cap_list: list[int] = []
        try:
            # 等待战斗开始
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
            # 下一采集时间
            next_ns = start_ns = time.perf_counter_ns()
            # 开始时间
            started_at_unix_ns = time.time_ns()
            # 上次采集时间
            prev_t_abs_ns = None
            # 数据采集循环
            while self._recording_state:
                # 当前时间
                now = time.perf_counter_ns()
                # 判断是否严重滞后
                if now > next_ns + MAX_LAG_PERIODS * INTERVAL_NS:
                    # 滞后时间
                    behind = now - next_ns
                    # 跳过帧数
                    skipped = behind // INTERVAL_NS
                    # 丢弃帧数
                    n_dropped += skipped
                    # 跳过滞后
                    next_ns = now
                    print(f"严重落后，跳过{skipped}帧")
                # 等到下一采集时间
                if now < next_ns:
                    time.sleep((next_ns - now) / 1e9)
                # 当前时间
                t_abs_ns = time.perf_counter_ns()
                # 记录当次采集和上次采集时间差
                if prev_t_abs_ns is not None:
                    dt_list.append(t_abs_ns - prev_t_abs_ns)
                # 记录采集时间
                prev_t_abs_ns = t_abs_ns
                # 记录滞后时间
                lag_ns = t_abs_ns - next_ns
                # 记录相对时间
                t_rel_ns = t_abs_ns - start_ns
                # 获取数据
                observation = self._session.get_observation()
                # 获取键盘输入
                keystates = self._keyboard_hook.snapshot()
                # 拼接事件
                event = {
                    "t_ns": t_abs_ns,
                    "t_rel_ns": t_rel_ns,
                    "lag_ns": lag_ns,
                    "frame_idx": frame_idx,
                    "eps_id": self.eps_id,
                    "observation": observation.model_dump(),
                    "key_states": keystates.model_dump(),
                }
                # 写入事件
                self._writer.write_event(event)
                # 采集图像
                # 判断是否需要采集图像
                if (
                    t_abs_ns - last_vision_ns >= VISION_INTERVAL_NS
                    and observation.window_focused
                ):
                    # 采集图像时间
                    t0 = time.perf_counter_ns()
                    # 采集图像
                    image = self._vision.capture()
                    # 记录图像采集时间差
                    cap_list.append(time.perf_counter_ns() - t0)
                    # 入队图像
                    self._writer.enqueue_image(image, frame_idx, t_rel_ns)
                    # 记录采集时间
                    last_vision_ns = t_abs_ns

                frame_idx += 1
                next_ns += INTERVAL_NS

                # 结束逻辑
                # 判断是否写盘错误
                if self._writer.image_error is not None:
                    # 记录结束原因
                    self._end_reason = "error"
                    break
                # 如果图像丢弃帧数超过最大丢弃帧数，记录结束原因
                if self._writer.image_dropped > MAX_IMAGE_DROPPED:
                    self._end_reason = "discard"
                    break
                # f12退出
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
                # 丢弃帧数过多
                if n_dropped >= MAX_DROPPED:
                    self._end_reason = "discard"
                    break
                # 实焦过多
                if not observation.window_focused:
                    n_loss += 1
                    if n_loss >= MAX_FOCUS_LOST:
                        self._end_reason = "discard"
                        break
                else:
                    n_loss = 0
                # 内存读取失败过多
                if observation.read_error_streak >= MAX_HP_READ_FAIL:
                    self._end_reason = "discard"
                    break
                # 胜利
                if not observation.is_battle:
                    false_streak += 1
                    if false_streak >= DEBOUNCE:
                        self._end_reason = "win"
                        self._recording_state = False
                        break
                else:
                    false_streak = 0
        except Exception:
            # 意外终止
            self._end_reason = "error"
            raise
        finally:
            if self._writer is not None:
                # 计算整帧采样性能
                dt_p50 = percentile_ns(dt_list, 0.50)
                dt_p95 = percentile_ns(dt_list, 0.95)
                # 计算整帧采样率
                hz_meas = (1e9 / dt_p50) if dt_p50 else None
                # 计算图像采集性能
                cap_p50 = percentile_ns(cap_list, 0.50)
                cap_p95 = percentile_ns(cap_list, 0.95)
                self._writer.close(
                    self._end_reason,
                    n_dropped,
                    started_at_unix_ns=started_at_unix_ns,
                    code_git_sha=git_sha(),
                    config_hash=config_hash(),
                    sample_hz_nominal=self._config.collect["sample_hz"],
                    sample_hz_measured=hz_meas,
                    dt_p50_ns=dt_p50,
                    dt_p95_ns=dt_p95,
                    vision_hz=float(c["vision_hz"]),
                    vision_region=dict(c["vision_region"]),
                    vision_format=c.get("vision_format", "jpg"),
                    vision_quality=int(c.get("vision_jpeg_quality", 85)),
                    vision_color_order="RGB",
                    capture_ms_p50=(cap_p50 / 1e6) if cap_p50 else None,
                    capture_ms_p95=(cap_p95 / 1e6) if cap_p95 else None,
                )

    def start_collect(self):
        try:
            if not self._pre_collect():
                return
            self._collect_data()
        finally:
            self._end_collect()

    def _end_collect(self):
        self._writer = None
        self._keyboard_hook.stop()
        self._session.detach()
        self._vision.stop()
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
