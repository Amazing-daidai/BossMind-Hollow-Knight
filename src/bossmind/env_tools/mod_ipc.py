import socket
import json
import threading
import logging


logger = logging.getLogger(__name__)


class ModIpc:

    def __init__(self, config):
        self.config = config
        self.host = self.config.client["UdpHost"]
        self.port = self.config.client["UdpPort"]
        self.sock = None
        self._latest = None
        self._lock = threading.Lock()
        self._thread = None
        self._running = False

    def start(self):
        """启动接收数据线程"""
        if self._running:
            return
        # 创建socket套接字
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 允许端口复用
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 绑定端口
        self.sock.bind((self.host, self.port))
        # 设置超时时间
        self.sock.settimeout(1.0)
        self._running = True
        # 创建线程
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def _recv_loop(self):
        while self._running:
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:  # stop 时 close 可能触发
                break
            self._update_latest(data)

    def _update_latest(self, data):
        """解析mod发送的数据，并转化为PlayerStates和EnemyStates

        Args:
            data (bytes): mod发送的数据
        """
        try:
            # 转码
            text = data.decode("utf-8")
            # 解析json
            json_data = json.loads(text)
            if not isinstance(json_data, dict):
                return
            # 更新信息
            with self._lock:
                self._latest = json_data
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.error(f"Invalid data: {data}")
            return

    def stop(self):
        """停止接收并清理缓存"""
        self._running = False

        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        with self._lock:
            self._latest = None

    def read_latest(self):
        """返回状态快照

        Returns:
            dict: 最新状态
        """
        with self._lock:
            return None if self._latest is None else dict(self._latest)
