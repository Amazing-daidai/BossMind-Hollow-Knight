# BossMind.Mod — 环境与部署（B 机）

本目录是 **P2 Mod** 的 C# 工程与操作说明。  
当前约定：**Python 自写**；**C# 业务你先试**（空壳已就绪）；环境/脚手架已进仓库。

官方文档：

- 环境：[ModdingDocs – Environment setup](https://prashantmohta.github.io/ModdingDocs/getting-started.html)
- 第一个 Mod：[your-first-mod](https://prashantmohta.github.io/ModdingDocs/your-first-mod.html)
- 模板：[HKMod Templates](https://prashantmohta.github.io/ModdingDocs/hk-modding-templates.html)
- API 示例：[hk-modding/api Examples](https://github.com/hk-modding/api/tree/master/Examples)

---

## 0. 机器分工

| 机器 | 做什么 |
|------|--------|
| A（可无游戏） | 改仓库文档 / 审代码；**本机当前未装 `dotnet`，勿在此编译** |
| B（有空洞骑士） | 装工具 → 填路径 → 编译 → 拷 DLL → 开游戏验收 |

仓库根：B 上建议 `E:\BossMind`，与 `AGENTS.md` 一致。

---

## 1. B 机一次性安装

### 1.1 Visual Studio / .NET

1. 安装 [Visual Studio Community](https://visualstudio.microsoft.com/)。
2. 工作负载勾选：**使用 .NET 的桌面开发**（含 .NET Framework 4.7.2 开发工具）。
3. 安装后新开终端，确认：

```powershell
dotnet --version
```

应能打印版本号（SDK 存在即可；工程目标是 **net472**）。

### 1.2 给游戏装 Modding API

任选其一：

- **推荐**：安装 [Scarab](https://github.com/fifty-six/Scarab/releases) 或 Lumafly，打开后指向你的 Hollow Knight，安装 **Modding API**。
- 手动：从 [hk-modding/api releases](https://github.com/hk-modding/api/releases) 覆盖游戏 `Managed`（新手不推荐）。

验收：启动游戏，左上角出现 Mod 列表 / 能进 Mod 菜单。

### 1.3 找到 Managed 路径

Steam 默认一般是：

```text
C:\Program Files (x86)\Steam\steamapps\common\Hollow Knight\hollow_knight_Data\Managed\
```

若 Steam 库不在 C 盘，在 Steam → 空洞骑士 → 管理 → 浏览本地文件 → 进入 `hollow_knight_Data\Managed`。

该目录下应有 `Assembly-CSharp.dll`（装过 API 后会带 `Modding` 命名空间）。

### 1.4（可选）安装官方工程模板

若你想用 `dotnet new` 另起工程对照：

```powershell
dotnet new -i HKModding.HKMod.Templates
dotnet new hkmod --name "TryMod" --author "You" --refsPath "你的Managed路径\"
```

**本仓库已提供** `mods/BossMind.Mod/`，可直接用，不必再 `dotnet new`。

---

## 2. 配置本仓库工程路径

```powershell
cd E:\BossMind\mods\BossMind.Mod
copy HollowKnightRefs.props.example HollowKnightRefs.props
```

用编辑器打开 `HollowKnightRefs.props`，把 `HollowKnightRefs` 改成 **你本机 Managed 目录**（末尾可带或不带 `\`）。

`HollowKnightRefs.props` 已在 `.gitignore`，勿提交本机路径。

---

## 3. 编译与部署

**先关闭游戏**，再编译：

```powershell
cd E:\BossMind\mods\BossMind.Mod
dotnet build -c Release
```

成功后：

- 输出 DLL：`bin\Release\BossMind.Mod.dll`
- 若 props 里 `HollowKnightMods` 正确，PostBuild 会尝试复制到  
  `...\Hollow Knight\hollow_knight_Data\Managed\..\..\Mods\BossMind.Mod\`  
  即游戏根下 `Mods\BossMind.Mod\BossMind.Mod.dll`。

若自动复制失败，手动：

1. 创建文件夹：`<游戏根>\Mods\BossMind.Mod\`
2. 复制 `BossMind.Mod.dll` 进去

启动游戏 → 左上角应出现 **BossMind.Mod**；日志见游戏目录附近的 `ModLog.txt`（或 Scarab/API 说明的路径），应有 `BossMind.Mod loaded`。

---

## 4. Spike 目标（你写业务时对照）

环境通了之后，在空壳上自己实现（详见 [`SPIKE_TODO.md`](SPIKE_TODO.md)）：

| 项 | 约定 |
|----|------|
| 传输 | UDP `127.0.0.1:28765`，单向推送 |
| 载荷 | JSON 一行，UTF-8 |
| 内容 | 场景内 `HealthManager` 的 hp / max / x / y（+ name 可选） |
| 性能 | **禁止每帧** `FindObjectsOfType`；低频刷新列表，另限流发送 |
| Python | 你自己写接收脚本；仓库暂不代写 |

示例包（可微调，改了请同步记到 `AGENTS.md`）：

```json
{"t":123.456,"scene":"GG_Hornet_1","n":1,"enemies":[{"hp":900,"max":900,"x":1.2,"y":3.4,"name":"Hornet Boss 1"}]}
```

验收：进**未挖过 CE 链**的房间，Python 能持续打出 hp。

---

## 5. 常见问题

| 现象 | 处理 |
|------|------|
| `dotnet` 不是命令 | 重装 VS 工作负载；新开终端；检查 PATH |
| 找不到 `Assembly-CSharp.dll` | `HollowKnightRefs.props` 路径错，或未装 API |
| 游戏无 Mod 列表 | API 未装好；用 Scarab 重装 API |
| 编译成功但游戏无此 Mod | DLL 不在 `Mods\BossMind.Mod\`；或游戏仍在运行时覆盖失败 |
| 引用一堆红线 | 确认打开的是 `BossMind.Mod.csproj`，且 Managed 路径存在 |

卡住时把：**完整报错**、`HollowKnightRefs` 路径（可打码盘符外信息）、是否已装 API，贴回对话即可。
