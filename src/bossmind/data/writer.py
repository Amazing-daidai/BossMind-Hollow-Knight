import json
import logging
import os
import threading
from pathlib import Path
from queue import Empty, Full, Queue

import mss.tools
from PIL import Image

from bossmind.data.schema import MetaData, validate_event
from bossmind.paths import RAW_DATA_DIR

logger = logging.getLogger(__name__)


class EpisodeWriter:
    def __init__(
        self,
        batch_id: str,
        eps_id: str,
        boss_name: str,
        *,
        image_queue_size: int = 30,
        image_ext: str = "jpg",
        jpeg_quality: int = 85,
    ):
        self.eps_id = eps_id
        self.batch_id = batch_id
        self.boss_name = boss_name
        self.eps_dir = Path(RAW_DATA_DIR / batch_id / eps_id)
        self.image_dir = Path(self.eps_dir / "frames")
        self.n_events = 0
        self.n_frames = 0  # 兼容字段；close 时以盘上 glob 为准写入 meta
        self.n_enqueued = 0  # 入队帧数
        self.image_dropped = 0  # 丢弃帧数
        self.image_error: str | None = None  # 图像写盘错误
        self.file = None
        self.t_0 = None
        self.t_1 = None
        self.image_ext = image_ext.lstrip(".").lower()  # 图像文件扩展名
        self.jpeg_quality = jpeg_quality  # 图像质量
        self.image_queue = Queue(maxsize=image_queue_size)
        self._image_stop = threading.Event()
        self.image_thread = None
        self._closed = False

    # 写入meta数据
    def _write_meta(self, end_reason, n_dropped, n_frames_on_disk, meta_extra):
        # 计算持续时间
        if self.n_events == 0:
            duration = 0
        else:
            duration = self.t_1 - self.t_0
        # 填充meta内容
        meta = MetaData(
            eps_id=self.eps_id,
            batch_id=self.batch_id,
            duration=duration / 1e9,
            n_dropped=n_dropped,
            image_dropped=self.image_dropped,
            end_reason=end_reason,
            boss=self.boss_name,
            n_events=self.n_events,
            n_frames=n_frames_on_disk,
            **meta_extra,
        ).model_dump()
        # 写文件
        with open(self.eps_dir / "meta.json", "x", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

    # 写入前准备
    def pre_write(self):
        # 判断文件夹是否存在
        if self.eps_dir.exists():
            raise FileExistsError(f"文件夹已存在: {self.eps_dir}")
        # 创建文件夹
        self.eps_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        # 初始化写盘状态
        self._closed = False
        self._image_stop.clear()
        self.image_error = None
        # 创建写盘线程
        self.image_thread = threading.Thread(
            target=self._write_loop,
            name="ImageWriter",
            daemon=True,
        )
        # 开启写盘线程
        self.image_thread.start()
        # 创建事件文件
        self.file = open(self.eps_dir / "events.jsonl", "x", encoding="utf-8")

    # 写入事件
    def write_event(self, data: dict):
        # 判断文件是否打开
        if self.file is None:
            raise ValueError("文件未打开")
        # 验证事件数据
        event = validate_event(data)
        # 写入事件文件
        line = json.dumps(event.model_dump(), ensure_ascii=False) + "\n"
        self.file.write(line)
        # 刷新文件
        self.file.flush()
        # 更新事件计数
        if self.n_events == 0:
            self.t_0 = event.t_ns  # 记录开始时间
        self.n_events += 1
        self.t_1 = event.t_ns  # 记录结束时间

    # 图像入队
    def enqueue_image(self, image_data, frame_idx, t_rel_ns) -> bool:
        # 判断写盘是否停止或是否有错误
        if self._image_stop.is_set() or self.image_error is not None:
            logger.debug("写盘已停止，拒绝入队 frame=%s", frame_idx)
            return False
        # 整理入队元素
        item = (image_data, frame_idx, t_rel_ns)
        try:
            # 入队并增加队列计数
            self.image_queue.put_nowait(item)
            self.n_enqueued += 1
            return True
        except Full:
            # 如果队列已满，丢弃最老一帧
            self.image_dropped += 1
            if self.image_dropped == 1 or self.image_dropped % 10 == 0:
                logger.warning(
                    "队列已满，丢弃最老一帧以让位 frame=%s（累计丢弃 %d）",
                    frame_idx,
                    self.image_dropped,
                )
            try:
                # 最老一帧出队
                old = self.image_queue.get_nowait()
                # 判断是否为哨兵
                if old is None:
                    # 勿吞哨兵
                    self.image_queue.put_nowait(None)
                    return False
                # 新帧入队并更新队列计数
                self.image_queue.put_nowait(item)
                self.n_enqueued += 1
                return True
            except (Empty, Full):
                return False

    # 编码一帧图像
    def _encode_one(self, item) -> None:
        image_data, frame_idx, t_rel_ns = item
        # 文件名
        frame_name = f"frame_{frame_idx:04d}_{t_rel_ns:012d}.{self.image_ext}"
        # 文件路径
        path = self.image_dir / frame_name
        # 临时文件
        tmp = path.with_suffix(path.suffix + ".part")
        if self.image_ext in ("jpg", "jpeg"):
            # mss raw = BGRA；BGRX 直接喂 Pillow，跳过 .rgb 重排
            im = Image.frombuffer(
                "RGB",
                tuple(image_data.size),
                bytes(image_data.raw),
                "raw",
                "BGRX",
                0,
                1,
            )
            im.save(
                tmp,
                format="JPEG",
                quality=self.jpeg_quality,
                subsampling=0,
                optimize=False,
            )
        else:
            mss.tools.to_png(image_data.rgb, image_data.size, output=str(tmp))
        # 用真实文件名替换临时文件
        os.replace(tmp, path)

    # 写入磁盘
    def _write_loop(self):
        while True:
            try:
                # 获取数据
                item = self.image_queue.get(timeout=0.2)
            except Empty:
                # 如果队列为空且写盘停止，退出循环
                if self._image_stop.is_set() and self.image_queue.empty():
                    break
                continue
            # 如果为哨兵，退出循环
            if item is None:
                break
            try:
                # 编码并写入磁盘
                self._encode_one(item)
                # 记录写入数量
                self.n_frames += 1
            except Exception as e:
                # 记录写盘错误
                self.image_error = f"{type(e).__name__}: {e}"
                logger.exception("图片写盘线程异常终止")
                # 停止写盘
                self._image_stop.set()
                break

    # 关闭所有写入，写meta，并重置
    def close(self, end_reason, n_dropped, *, join_timeout_s: float = 30.0, **meta_extra):
        # 判断是否已关闭
        if self._closed:
            return
        # 停止写盘
        self._image_stop.set()
        try:
            # 入队哨兵
            self.image_queue.put_nowait(None)
        except Full:
            pass
        # 等待写盘线程退出
        join_timeout = False
        # 判断写盘线程是否存在且存活
        if self.image_thread is not None and self.image_thread.is_alive():
            # 等待写盘线程退出
            self.image_thread.join(join_timeout_s)
            # 判断写盘线程是否存活
            join_timeout = self.image_thread.is_alive()
            # 如果写盘线程未退出，记录写盘超时
            if join_timeout:
                logger.error(
                    "图片写盘线程 %.0fs 未退出，meta 标记 image_join_timeout",
                    join_timeout_s,
                )
        # 计算写入帧数
        n_frames_on_disk = len(list(self.image_dir.glob(f"*.{self.image_ext}")))
        # 清理残留 .part
        for part in self.image_dir.glob(f"*.{self.image_ext}.part"):
            try:
                part.unlink()
            except OSError:
                pass
        # 填充meta
        meta_extra.setdefault("image_join_timeout", join_timeout)
        meta_extra.setdefault("n_frames_enqueued", self.n_enqueued)
        meta_extra.setdefault("image_error", self.image_error)
        # 写meta
        self._write_meta(end_reason, n_dropped, n_frames_on_disk, meta_extra)
        # 重置
        if self.file is not None:
            self.file.close()
            self.file = None
        self.t_0 = None
        self.t_1 = None
        self.n_events = 0
        self.n_frames = 0
        self.n_enqueued = 0
        self.image_dropped = 0
        self.image_error = None
        self.image_thread = None
        self._closed = True


if __name__ == "__main__":
    pass
