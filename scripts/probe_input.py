import logging
import time

from bossmind.env_tools.input import InputController

logging.basicConfig(level=logging.WARNING)

def main():
    print("=" * 40)
    print("3 秒后执行按键，请切换到空洞骑士窗口")
    print("=" * 40)
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    input_controller = InputController()
    input_controller.hold_key("right", 3.0)
    input_controller.press_key("left")
    time.sleep(3)
    input_controller.hold_key("jump", 0.3)
    input_controller.tap("attack")
    time.sleep(3)
    input_controller.release_key("left")
    print("动作序列执行完毕")
if __name__ == "__main__":
  try:
    main()
  except KeyError as e:
    print(f"错误: {e}")