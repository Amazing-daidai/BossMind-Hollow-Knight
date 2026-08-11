import socket
import json

from bossmind.config import load_config

def main():
    # 获取服务器配置
    config = load_config()
    host = config.client['UdpHost']
    port = config.client['UdpPort']
    # 创建socket套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 允许端口复用
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 绑定端口
    sock.bind((host, port))
    sock.settimeout(1.0)  # 最多阻塞 1 秒；超时抛 socket.timeout

    try:
        while True:
            # 接收数据
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            data = data.decode('utf-8')
            try:
                # 解析json
                json_data = json.loads(data)
                print(f"t: {json_data['t']}, scene: {json_data['scene']}, n: {json_data['n']}")
                for enemy in json_data['enemies']:
                    print(f"  name: {enemy['name']}, hp: {enemy['hp']}, max: {enemy['max']}, x: {enemy['x']}, y: {enemy['y']}")
            except json.JSONDecodeError:
                print(f"Invalid JSON: {data}")
                continue
    except KeyboardInterrupt:
        print("Keyboard interrupt")
    finally:
        sock.close()


if __name__ == "__main__":
    main()