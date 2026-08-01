import time

from bossmind.env_tools.keyboard_hook import KeyboardHook
from bossmind.config import load_config

def main():
    config = load_config()
    keyboard_hook = KeyboardHook(config)
    keyboard_hook.start()
    print("F12 结束；试按住方向键看 held/pressed")
    try:
        while keyboard_hook.is_running:
            ks = keyboard_hook.snapshot()
            held = ks.held.model_dump()
            pressed = ks.pressed.model_dump()
            for key, value in held.items():
                if value:
                    print(f"held: {key}")
            for key, value in pressed.items():
                if value:
                    print(f"pressed: {key}")
            time.sleep(1/60)
    finally:
        keyboard_hook.stop()

if __name__ == "__main__":
    main()