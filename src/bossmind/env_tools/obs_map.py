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
        self._boss_info = config.boss_info

    def _find_primary_enemy(self, substr_list, enemies):
        """找到主敌

        Args:
            substr_list (list): 场景名字对应的主敌的子串列表
            enemies (list): 敌人列表

        Returns:
            EnemyStates: 主敌
        """

        # 小写的子串列表
        substr_list = [substr.lower() for substr in substr_list]
        # 主敌列表
        enemy_list = []
        # 遍历敌人列表，如果敌人的名字包含子串列表中的任意一个，则将敌人添加到主敌列表中
        for enemy in enemies:
            name = (enemy.name or "").lower()
            if any(s in name for s in substr_list):
                enemy_list.append(enemy)
        # 如果主敌列表为空，则返回None
        if len(enemy_list) == 0:
            return None
        # 如果主敌列表只有一个敌人，则返回该敌人
        if len(enemy_list) == 1:
            return enemy_list[0]
        # 如果主敌列表有多个敌人，则返回血量最大的敌人
        return max(enemy_list, key=lambda x: x.enemy_hp)

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
        """将游戏状态映射为字符串

        Args:
            game_state (int): 游戏状态

        Returns:
            str: 游戏状态字符串
        """
        return self._game_state_labels.get(
            game_state, str(game_state)
        )  # 未知值返回原始值

    def _map_player(self, raw: dict) -> PlayerStates:
        """将收到的玩家数据映射为PlayerStates

        Args:
            raw (dict): 收到的玩家数据

        Returns:
            PlayerStates: 玩家状态
        """
        return PlayerStates(
            player_hp=raw["hp"],
            player_x=raw["x"],
            player_y=raw["y"],
            soul=raw["soul"],
            player_facing_right=self._facing_to_right(raw["facing"]),
        )

    def _map_enemies(self, raw_list: list[dict]) -> list[EnemyStates]:
        """将收到的敌人数据映射为EnemyStates

        Args:
            raw_list (list[dict]): 收到的敌人数据

        Returns:
            list[EnemyStates]: 敌人列表
        """
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

    def _is_battle(self, game_state: str, scene_name: str, enemies: list[EnemyStates]) -> bool:
        """判断是否在战斗中

        Args:
            game_state (str): 游戏状态
            scene_name (int): 场景名
            enemies (list[EnemyStates]): 敌人列表

        Returns:
            bool: 是否在战斗中
        """
        # 判断游戏状态
        if game_state != "PLAYING":
            return False
        # 判断是否是指定的场景
        cfg = self._boss_info.get(scene_name)
        if cfg is None:
            return False
        # 判断主敌是否存在
        primary_enemy = self._find_primary_enemy(cfg["primary_name_substr"], enemies)
        if primary_enemy is None:
            return False
        # 判断主敌是否存活
        return (
            0 < primary_enemy.enemy_hp < 2501
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
        scene_name = latest["scene"]
        enemies=self._map_enemies(latest["enemies"])
        is_battle = self._is_battle(game_state, scene_name, enemies)

        return Observation(
            player=self._map_player(latest["player"]),
            enemies=enemies,
            n_enemies=len(latest["enemies"]),
            window_focused=window_focused,
            is_battle=is_battle,
            scene_name=scene_name,
            game_state=game_state,
        )


if __name__ == "__main__":
    pass
