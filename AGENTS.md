# BossMind — Agent 交接

> 换机先读 **§1～§3**。更深设计（Mod/RL/LLM 展开）见 `docs/BossMind_项目方案.md`。  
> 每轮：改 §2/§3 → 里程碑 §5 → commit/push。

---

## 1. 约定

### 1.1 目标

| 层次 | 导向 | 内容 | 验收 |
|------|------|------|------|
| 短期 | 求职 | 观测→BC→执行→评估→（后）复盘 Agent 可演示 | demo+架构图+指标表；**不绑通关率** |
| 中期 | 过渡 | 速通神居 **某一门** | 通关率/时长 |
| 终极 | 结果 | 速通 **五门** | 成绩；不设求职期限 |

红线：单点 CE 挖链 **>6h 无果** → 转 Mod / `pipeline_only`。求职建议 **~8 周**交付切片。

### 1.2 技术主线

```text
快回路：Observation → BC /（后）RL微调 → 按键注入
慢回路：LLM Option（阶段边界）+ 复盘 Agent + 实验编排
观测：P1 内存(CE) ∥ P2 起 Mod 推送为主、内存对照
```

- **BC**：模仿 held（12 维含 tab）；None 帧 skip，不填 0 污染。  
- **RL**：BC-init 微调；需 Mod 快重置（&lt;3s）；loader 将来要含 death。  
- **LLM**：仅慢回路；**禁止** 60Hz 出键。CNN 非主输入；截图旁路 10Hz。  
- **Mod**：游戏内枚举 `HealthManager`(+transform) → **单向推送**最新快照；Python 60Hz **读最新**；列表要缓存（禁每帧全 Find）。推送限流 60～120Hz 即可（游戏可 240Hz）。

### 1.3 阶段总表

| Phase | 内容 | 状态 |
|-------|------|------|
| **P0** | 采集/视觉/Hornet CE/真 is_battle/BC 骨架 | ≈完成 |
| **P1** | 真数据 BC + 相对位置 + BossEnv/eval | 可并行 |
| **P2** | Mod 广播 + ModBackend + 快 SL | **环境脚手架已就绪；Spike 自写中** |
| **P3** | RL 微调 | 等 2.4 |
| **P4** | 复盘 Agent → 编排 → Option | 可与 P3 交错 |
| **P5/P6** | 一门 → 五门 | 中/终 |

### 1.4 观测 / 数据 / 协作

| 项 | 决定 |
|----|------|
| `is_battle` | `PLAYING ∧ scene∈boss_info ∧ boss_hp>0`（已实现） |
| 采样 | 事件 60Hz；图 10Hz |
| Schema | `1.1.1`（`player_*`/`boss_*`）；enemies+mask → 将来 2.x |
| 采集闸门 | 现：**GO** `smoke_*`/`pipeline_*`；expert 在 eval 协议固定后试开 |
| 双机 | A=`D:\BossMind` 开发；B=`E:\BossMind` 游戏/采数/Mod；conda `BossMind` 3.12 |
| 协作 | 师父模式；**Python 一律学员自写**；**C# 学员先试，卡关再代写**；Agent 先配环境/文档/空壳 |

### 1.5 Mod Spike 约定（P2.1）

| 项 | 值 |
|----|-----|
| 工程 | [`mods/BossMind.Mod/`](mods/BossMind.Mod/) |
| 环境说明 | [`mods/README.md`](mods/README.md) |
| C# 自学清单 | [`mods/SPIKE_TODO.md`](mods/SPIKE_TODO.md) |
| UDP | `127.0.0.1:28765`，单向 JSON 行 |
| Python | 学员自写 `probe_mod_udp` / `mod_ipc`（仓库暂不代写） |

---

## 2. 当前状态（2026-08-07）

| 字段 | 值 |
|------|-----|
| 进度 | **P2 环境脚手架进仓**；业务 Spike 待 B 机 + 学员实现 |
| 已齐 | `mods/README` + 空壳 `BossMindMod` + props 示例 + SPIKE_TODO；gitignore bin/obj/本机 props |
| 缺口 | B 装 VS/Scarab；C# HM+UDP；Python 收包；其后 2.2～2.5 |
| Git | `main` |
| 提醒 | A 机可能无 `dotnet`——**编译只在 B**；勿提交 `HollowKnightRefs.props` |

**B 机下一步**：`git pull` → 按 `mods/README.md` §1～§3 → 游戏出现 BossMind.Mod → 按 `SPIKE_TODO.md` 写 S1。

---

## 3. 下一步（Phase / Step）

### P2 — Mod（当前主线）

| Step | 内容 | 完成标准 |
|------|------|----------|
| **2.0** | 环境（文档+空壳） | README 可跟做；空壳能加载 — **仓库侧已做** |
| **2.1** | Spike：HM→UDP；Python 自写收包 | 未挖链房也能见血 |
| **2.2** | 敌人列表缓存 + 推送限流；间隙 p50/p95 | 高刷可玩；读最新无积压 |
| **2.3** | `ModBackend.read_latest`；与 Memory 对照；`backend_id` | 同接口 |
| **2.4** | Mod SL，重置 &lt;3s | **P3 前门禁** |
| **2.5** | 文档化 enemies[]+mask → schema 2.x | 先表结构、后合代码 |

### P1 — BC + 评估（可并行、不挡 P2）

| Step | 内容 | 完成标准 |
|------|------|----------|
| **1.1～1.5** | is_battle 验收 → 采数 → 特征/相对位置 → 过拟合 → BossEnv+eval | 见前表 |

### 本阶段不做

五门全挖静态链；CNN 主输入；LLM 出键；无快重置就上在线 RL；Agent 代写 Python。

---

## 4. 备忘（常用，不替代 yaml）

```text
Hornet boss_hp: UP+0x01F1FBC8 → … → +0x148；满血 900；仅 GG_Hornet_1
scene/game_state: UP+0x01F28838 同根；game_state +0x18C；4/5/3=PLAY/PAUSE/CUTSCENE
facing: UP+0x01F4F8B8 → … +0xB0；右=-1 左=+1（以实测为准）
CE 库: E:\缓存\tempdata\bosshp.sqlite
Mod UDP: 127.0.0.1:28765
```

```text
configs/  scripts/{probe_*,collect_expert}
src/bossmind/{env_tools,data,learning,…}
mods/BossMind.Mod/   mods/README.md   mods/SPIKE_TODO.md
docs/BossMind_项目方案.md
models/ data/raw/   # gitignore
```

---

## 5. 里程碑（最近）

| 日期 | 事件 |
|------|------|
| 2026-08-07 | P2 环境脚手架：mods 空壳+README+SPIKE_TODO；协作改为 Python 自写 / C# 先试 |
| 2026-08-06 | AGENTS 中等篇幅；P2 立项；P0–P6；boss_hp+is_battle |
| 2026-08-05 | scene/game_state；Phase-BC→main；BC 骨架 |
| 更早 | vision/x/y smoke 等 → `git log` |
