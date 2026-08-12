using System;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using Modding;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace BossMind.Mod
{
    // BossMind 观测 Mod：游戏内读玩家/敌人，UDP 推给 Python（当前约 1Hz）
    public class BossMindMod : Mod
    {
        internal static BossMindMod Instance { get; private set; }

        // 敌人 HealthManager 缓存（只在限流时 Find，禁止每帧刷）
        private readonly List<HealthManager> _enemies = new List<HealthManager>();
        // 玩家：控制器（位置/朝向）+ 数值（血/魂）
        private HeroController _hero;
        private PlayerData _player;

        // 与 configs client / Python ModIpc 一致
        private const string UdpHost = "127.0.0.1";
        private const int UdpPort = 28765;
        private UdpClient _udp;

        // 上次刷新+发送的时间（Time.time，秒）
        private float _lastLogTime;

        // 左上角 Mod 列表显示名
        public BossMindMod() : base("BossMind.Mod")
        {
        }

        public override string GetVersion()
        {
            return Assembly.GetExecutingAssembly().GetName().Version.ToString();
        }

        // API 加载入口；可能多次调用，钩子先 -= 再 +=
        public override void Initialize()
        {
            Instance = this;
            Log("BossMind.Mod loaded");

            ModHooks.HeroUpdateHook -= OnHeroUpdate;
            ModHooks.HeroUpdateHook += OnHeroUpdate;
            Log("HeroUpdateHook registered");

            if (_udp == null)
            {
                _udp = new UdpClient();
            }
            Log($"UDP ready → {UdpHost}:{UdpPort}");
        }

        // 骑士更新钩子：很频繁，Find/发送必须限流
        private void OnHeroUpdate()
        {
            float now = Time.time;
            if (now - _lastLogTime < 1f)
            {
                return;
            }

            _lastLogTime = now;
            RefreshEnemyCache(); // 贵
            SendSnapshot(now);   // 读缓存 + UDP
        }

        // 低频刷新敌人列表
        private void RefreshEnemyCache()
        {
            _enemies.Clear();
            HealthManager[] hms = UnityEngine.Object.FindObjectsOfType<HealthManager>();
            HeroController hero = HeroController.instance;

            foreach (HealthManager hm in hms)
            {
                if (hm == null)
                {
                    continue;
                }

                // 玩家走单例，不进 enemies
                if (hero != null && hm.gameObject == hero.gameObject)
                {
                    continue;
                }

                _enemies.Add(hm);
            }
        }

        // 菜单/切场景时可能为 null
        private void RefreshHeroCache()
        {
            _hero = HeroController.instance;
            _player = PlayerData.instance;
        }

        // JSON DTO：public 字段名 = JsonUtility 键名
        [Serializable]
        private class PlayerDto
        {
            public int hp;
            public int soul;
            public float x;
            public float y;
            public float facing;
        }

        [Serializable]
        private class EnemyDto
        {
            public int hp;
            public float x;
            public float y;
            public string name;
            public float facing;
        }

        // 整包，对应 Python read_latest() 的 dict
        [Serializable]
        private class SnapshotDto
        {
            public float t;
            public string scene;
            public int gamestate;
            public PlayerDto player;
            public EnemyDto[] enemies;
        }

        // hero/player 缺失时返回 null
        private PlayerDto BuildPlayerDto()
        {
            if (_hero == null || _player == null)
            {
                return null;
            }

            Vector3 p = _hero.transform.position;
            return new PlayerDto
            {
                hp = _player.health,
                soul = _player.MPCharge,
                x = p.x,
                y = p.y,
                facing = _hero.cState.facingRight,  // 待实机确认
            };
        }

        // 组包 → JSON → UDP；失败只 Log，不抛出钩子
        private void SendSnapshot(float now)
        {
            if (_udp == null)
            {
                return;
            }

            RefreshHeroCache();

            var enemies = new List<EnemyDto>(_enemies.Count);
            foreach (HealthManager hm in _enemies)
            {
                if (hm == null)
                {
                    continue;
                }

                Vector3 p = hm.transform.position;
                enemies.Add(new EnemyDto
                {
                    hp = hm.hp,
                    x = p.x,
                    y = p.y,
                    name = hm.gameObject.name,
                    facing = hm.cState.facingRight,  // 待实机确认
                });
            }

            var snap = new SnapshotDto
            {
                t = now,
                scene = SceneManager.GetActiveScene().name,
                gamestate = (int)GameManager.instance.gameState,
                enemies = enemies.ToArray(),
                player = BuildPlayerDto(),
            };

            string json = JsonUtility.ToJson(snap);
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            try
            {
                _udp.Send(bytes, bytes.Length, UdpHost, UdpPort);
            }
            catch (Exception e)
            {
                Log($"UDP send failed: {e.Message}");
            }
        }
    }
}
