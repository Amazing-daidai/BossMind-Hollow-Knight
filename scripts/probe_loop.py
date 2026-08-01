import logging
import time

from bossmind.env_tools.session import GameSession
from bossmind.config import load_config

logging.basicConfig(level=logging.WARNING)


def main():
    print("开始读档测试，请确保已经打开当前存档并将窗口焦点在5秒内切换到游戏窗口")
    print("=" * 40)
    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    config = load_config()
    game_session = GameSession(config)
    try:
        game_session.attach()
        game_session.goto_boss_room("GG_Hornet_1")
        hp_baseline = game_session.get_observation().player.hp
        print(f"基线血量: {hp_baseline}")
        for i in range(10):
            print(f"第{i + 1}次读档")
            game_session.reset_game("menu")
            game_session.attach()
            game_session.goto_boss_room("GG_Hornet_1")
            obs = game_session.get_observation()
            hp_after_reset = obs.player.hp
            print(
                f"当前血量: {hp_after_reset}，"
                f"是否与基线一致: {hp_after_reset == hp_baseline}，"
                f"read_error_streak={obs.read_error_streak}"
            )
    except KeyboardInterrupt:
        print("退出")
    except ValueError as e:
        print(f"错误: {e}")
    finally:
        game_session.detach()


if __name__ == "__main__":
    main()
