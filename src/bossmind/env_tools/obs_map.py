from bossmind.data.schema import Observation, EnemyStates, PlayerStates


class ObservationMapper:

    def __init__(self, config):
        self._config = config
        self._game_state_labels = {
            config.game_state["playing_value"]: "PLAYING",  # 实测 4：能操控
            config.game_state["paused_value"]: "PAUSED",  # 实测 5：ESC 暂停
            config.game_state["cutscene_value"]: "CUTSCENE",  # 实测 3：白屏过场
            # 进门偶发 6 等未知值：原样 str(value)，不算 PLAYING
        }

    def _facing_to_right(self, facing: float) -> bool | None:
        """判断是否朝向右边

        Args:
            facing (float): 朝向值

        Returns:
            bool: 是否朝向右边
        """
        right_value = self._config.player_facing["right_value"]
        left_value = self._config.player_facing["left_value"]
        if abs(facing - right_value) < 1e-3:
            return True
        if abs(facing - left_value) < 1e-3:
            return False

    def _map_game_state(self, game_state: int) -> str:
        return self._game_state_labels.get(
            game_state, str(game_state)
        )  # 未知值返回字符串

    def _map_player(self, raw: dict) -> PlayerStates:
        return PlayerStates(
            player_hp=raw["hp"],
            player_x=raw["x"],
            player_y=raw["y"],
            soul=raw["soul"],
            player_facing_right=self._facing_to_right(raw["facing"]),
        )

    def _map_enemies(self, raw_list: list[dict]) -> list[EnemyStates]:
        return [
            EnemyStates(
                enemy_hp=enemy["hp"],
                enemy_x=enemy["x"],
                enemy_y=enemy["y"],
                enemy_facing_right=self._facing_to_right(enemy["facing"]),
                name=enemy["name"],
            )
            for enemy in raw_list
        ]

    def _is_battle(self, game_state: str, boss_hp: int) -> bool:
        if game_state != "PLAYING":
            return False
        return (
            boss_hp > 0 and boss_hp < 2501
        )  # 空洞骑士boss最高血量为2500，有时候击杀boss后，血量会变成一个非常大的数字，所以这里限制一下

    def udp_dict_to_observation(
        self,
        latest: dict,
        *,
        window_focused: bool,
    ) -> Observation:
        """将mod发送的数据转化为Observation

        Args:
            latest (dict): mod发送的数据
            window_focused (bool): 窗口是否聚焦
        """
        game_state = self._map_game_state(int(latest["gamestate"]))
        

        return Observation(
            player=self._map_player(latest["player"]),
            enemies=self._map_enemies(latest["enemies"]),
            n_enemies=len(latest["enemies"]),
            window_focused=window_focused,
            is_battle=is_battle,
            scene_name=latest["scene"],
            game_state=game_state,
        )


if __name__ == "__main__":
    latest = {
        "player": {
            "hp": 100,
            "x": 0,
            "y": 0,
            "soul": 100,
            "facing": 1.0,
        },
        "enemies": [{"hp": 100, "x": 0, "y": 0, "facing": 1.0, "name": "enemy1"}],
        "scene": "scene1",
    }
    observation = udp_dict_to_observation(
        latest, window_focused=True, is_battle=True, game_state="game_state1"
    )
    print(observation)
