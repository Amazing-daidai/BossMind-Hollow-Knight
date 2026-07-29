import logging
import time

from bossmind.env_tools.session import GameSession

logging.basicConfig(level=logging.WARNING)

def main():
    print("开始读档测试，请将窗口焦点在5秒内切换到游戏窗口")
    print("=" * 40)
    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    game_session = GameSession()
    try:
        game_session.load_save()
        game_session.attach()
        game_session.goto_boss_room("hornet")
        hp_baseline = game_session.get_hp()
        time.sleep(5)
        for i in range(10):
            print(f"第{i+1}次读档")
            game_session.reset_game("menu")
            game_session.attach()
            game_session.goto_boss_room("hornet")
            hp_after_reset = game_session.get_hp()
            print(f"当前血量: {hp_after_reset}，是否与基线血量{hp_baseline}一致: {hp_after_reset == hp_baseline}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("退出")
    except ValueError as e:
        print(f"错误: {e}")
    finally:
        game_session.detach()


if __name__ == "__main__":
    main()