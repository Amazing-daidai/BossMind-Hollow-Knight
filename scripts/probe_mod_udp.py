import time

from bossmind.env_tools.mod_ipc import ModIpc
from bossmind.config import load_config

def main():
    config = load_config()
    ipc = ModIpc(config)
    ipc.start()
    try:
        while True:
            latest = ipc.read_latest()
            print(latest)
            time.sleep(1)
    except KeyboardInterrupt:
        ipc.stop()
        print("Keyboard interrupt")
    finally:
        ipc.stop()


if __name__ == "__main__":
    main()