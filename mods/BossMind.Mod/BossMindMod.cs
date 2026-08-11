using System.Reflection;
using Modding;
using UnityEngine;
using System.Collections.Generic;
using System;
using System.Net.Sockets;
using System.Text;
using UnityEngine.SceneManagement;

// 命名空间
namespace BossMind.Mod
{
    /// <summary>
    /// BossMind 观测 Mod 入口（空壳）。
    /// 业务（HealthManager / UDP）按 mods/SPIKE_TODO.md 自行实现。
    /// </summary>
    public class BossMindMod : Mod
    {
        internal static BossMindMod Instance { get; private set; }
        // 类的字段
        // 缓存所有HealthManager实例
        private readonly List<HealthManager> _enemies = new List<HealthManager>();
        // UDP相关配置
        private const string UdpHost = "127.0.0.1";
        private const int UdpPort = 28765;
        private UdpClient _udp;

        // 上次打 Log 的时间（秒）
        private float _lastLogTime;

        public BossMindMod() : base("BossMind.Mod")
        {
        }

        public override string GetVersion()
        {
            return Assembly.GetExecutingAssembly().GetName().Version.ToString();
        }

        // 初始化
        public override void Initialize()
        {
            Instance = this;
            Log("BossMind.Mod loaded");
            // 防重复订阅：先减再加（Initialize 可能被调多次）
            ModHooks.HeroUpdateHook -= OnHeroUpdate;
            ModHooks.HeroUpdateHook += OnHeroUpdate;
            Log("HeroUpdateHook registered");
            
            //创建UDP客户端
            if(_udp == null)
            {
                _udp = new UdpClient();
            }
            Log($"UDP ready → {UdpHost}:{UdpPort}");
        }

        // 钩子回调：游戏更新骑士时会进来（很频繁）
        private void OnHeroUpdate()
        {
            float now = Time.time;
            if (now - _lastLogTime < 1f)  // 1 秒内直接返回
            {
                return;
            }

            _lastLogTime = now;

            RefreshEnemyCache();
            LogEnemyCache(now);
            SendEnemySnapshot(now);
        }

        // 刷新敌人生存状态缓存
        private void RefreshEnemyCache()
        {
            // 清空缓存
            _enemies.Clear();
            // 重新遍历并加入到缓存列表
            HealthManager[] hms = UnityEngine.Object.FindObjectsOfType<HealthManager>();
            foreach(HealthManager hm in hms)
            {
                if(hm == null) continue;
                _enemies.Add(hm);
            }
        }

        // 读取缓存并记录游戏状态
        private void LogEnemyCache(float now)
        {
            // 记录时间和个数
            Log($"HM count={_enemies.Count} t={now:F1}");
            // 遍历
            foreach(HealthManager hm in _enemies)
            {
                if (hm == null) continue;
                // 获取位置
                Vector3 position = hm.transform.position;
                // 记录信息
                Log($"name={hm.gameObject.name} hp={hm.hp}/{hm.hpMax} x={position.x:F1} y={position.y:F1}");
            }
        }

        // 发送游戏状态
        private void SendEnemySnapshot(float now)
        {
            // 判断UDP状态
            if (_udp == null) return;
            // 拼接json串
            // 时间，场景名，敌人个数
            string scene = SceneManager.GetActiveScene().name;
            var sb = new StringBuilder(256);
            sb.Append("{\"t\":");
            sb.Append(now.ToString("F3", System.Globalization.CultureInfo.InvariantCulture));
            sb.Append(",\"scene\":\"");
            sb.Append(scene.Replace("\"", "'"));
            sb.Append("\",\"n\":");
            sb.Append(_enemies.Count);
            sb.Append(",\"enemies\":[");
            // 每个敌人的状态列表
            bool first = true;
            foreach (HealthManager hm in _enemies)
            {
                if (hm == null) continue;
                if (!first) sb.Append(',');
                first = false;
                Vector3 position = hm.transform.position;
                string name = hm.gameObject.name.Replace("\"", "'");
                sb.Append("{\"hp\":");
                sb.Append(hm.hp);
                sb.Append(",\"max\":");
                sb.Append(hm.hpMax);
                sb.Append(",\"x\":");
                sb.Append(position.x.ToString("F2", System.Globalization.CultureInfo.InvariantCulture));
                sb.Append(",\"y\":");
                sb.Append(position.y.ToString("F2", System.Globalization.CultureInfo.InvariantCulture));
                sb.Append(",\"name\":\"");
                sb.Append(name);
                sb.Append("\"}");
            }
            sb.Append("]}");

            // 使用UDP发送
            // 编码
            byte[] bytes = Encoding.UTF8.GetBytes(sb.ToString());
            // 发送
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
