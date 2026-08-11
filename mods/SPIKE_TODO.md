# P2.1 Spike — C# 自学清单（不代写业务）

空壳工程：[`BossMind.Mod/`](BossMind.Mod/)。先完成 [`README.md`](README.md) 环境，再按下面顺序改代码。  
卡关再叫我代写对应小节即可。

## 建议顺序

### S0. 环境验收（脚手架已具备）

- [ ] B 机 `dotnet build -c Release` 成功  
- [ ] 游戏左上角出现 BossMind.Mod，`ModLog` 有 loaded  
- [ ] （可选）改一行 `Log("hello")` 重编，确认能热更新流程  

### S1. 读一个 HealthManager

参考：Unity `Object.FindObjectsOfType<HealthManager>()`（**先每秒最多 1～2 次**，不要每帧）。

- [ ] 在 `ModHooks.HeroUpdateHook`（或等价）里计时，到期才 Find  
- [ ] 对第一个 HM：`Log($"hp={hm.hp} max={hm.hpMax}")`  
- [ ] 进有怪的房间，Log 里数字会变  

提示：`HealthManager` 在游戏程序集里；`using` 按 IDE 补全即可。

### S2. 读位置与场景名

- [ ] `hm.transform.position.x/y`  
- [ ] `UnityEngine.SceneManagement.SceneManager.GetActiveScene().name`  
- [ ] 仍先只打 Log，不发网络  

### S3. UDP 发出去

约定：`127.0.0.1:28765`，UTF-8 JSON + `\n`。

- [ ] `System.Net.Sockets.UdpClient` 发到本机  
- [ ] 用任意方式拼 JSON（手拼字符串即可，Spike 不必上重型库）  
- [ ] 发送也要限流（例如 ≤20Hz）；与 Find 频率分开  

包形状见 [`README.md`](README.md) §4。

### S4. 列表缓存（2.2 可再加强）

- [ ] 字段保存 `List<HealthManager>` 或轻量结构  
- [ ] Find 低频更新缓存；发送循环只读缓存  
- [ ] 换场景时清空（可 hook 场景切换，或每次 Find 前清）  

### S5. Python 侧（你自己写）

- [ ] `socket` bind `127.0.0.1:28765`（或 `0.0.0.0`）  
- [ ] 打印最新包；粗算间隔  
- [ ] 未挖链房间也能看到血  

建议脚本名（可自定）：`scripts/probe_mod_udp.py`；IPC 封装可放 `src/bossmind/env_tools/mod_ipc.py`（2.3 再用）。

## 明确先不做

- Mod 快读档（2.4）  
- 改 `schema` / 接 `GameSession`（2.3）  
- 共享内存、TCP RPC、每帧全图 Find  

## 求助时请带

1. 卡在 S几  
2. 相关 `.cs` 片段或报错全文  
3. ModLog 几行  
