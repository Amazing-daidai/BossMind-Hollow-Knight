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
| **P1** | 真数据 BC + 相对位置 + BossEnv/eval | **进行中** |
| **P2** | Mod 广播 + ModBackend + 快 SL（已立项） | **spike** |
| **P3** | RL 微调 | 等 2.4 |
| **P4** | 复盘 Agent → 编排 → Option | 可与 P3 交错 |
| **P5/P6** | 一门 → 五门 | 中/终 |

### 1.4 观测 / 数据 / 协作

| 项 | 决定 |
|----|------|
| `is_battle` | `PLAYING ∧ scene∈boss_info ∧ boss_hp>0`（已实现） |
| 采样 | 事件 60Hz；图 10Hz |
| Schema | `1.1.1`（`player_*`/`boss_*`）；旧 smoke 的 `hp/x/y` **不兼容**；enemies+mask → 将来 2.x |
| 采集闸门 | 现：**GO** `smoke_*`/`pipeline_*`；expert 在 eval 协议固定后试开 |
| 双机 | A=`D:\BossMind` 开发；B=`E:\BossMind` 游戏/采数/Mod；conda `BossMind` 3.12 |
| 协作 | 师父模式；少临时脚本；`eval`/`train_*` 可常驻 |

---

## 2. 当前状态（2026-08-06）

| 字段 | 值 |
|------|-----|
| 进度 | P0≈完；**P1 ∥ P2** |
| 已齐 | 管线+视觉+facing/scene/game_state/Hornet boss_hp+is_battle+BC 骨架+P2 立项 |
| 缺口 | 真数据过拟合；Boss 相对位置；自动 eval；Mod spike |
| Git | `main` |
| 提醒 | 特征含未接字段 → 大量 None-skip；训前收窄或补 xy |

**B 机**：`git pull && pip install -e .`

---

## 3. 下一步（Phase / Step）

### P1 — BC + 评估（内存路径可先跑）

| Step | 内容 | 完成标准 |
|------|------|----------|
| **1.1** | 验收 is_battle：走廊 / 房内 / 暂停 | 与约定一致 |
| **1.2** | 新 schema 采数（smoke/pipeline） | meta+events+frames；注意 win 过滤 |
| **1.3** | 特征：收窄未接项；补 **dx,dy 或 boss_x/y**（CE 或等 Mod） | 训练不全被 skip |
| **1.4** | BC.3 单局过拟合 | loss↓；held 可复现（看逐键，不唯 loss） |
| **1.5** | BossEnv + eval：N 局无人值守，CSV 指标 | 协议固定（存档/护符/局数）可复现 |

### P2 — Mod（已立项；与 P1 并行）

| Step | 内容 | 完成标准 |
|------|------|----------|
| **2.1** | Spike：HK Modding API；枚举 HM；**UDP** 推 hp（+xy）；Python 打印 | 未挖链房/小怪也能见血；≤3 日 |
| **2.2** | 敌人列表缓存 + 推送限流；打点间隙 p50/p95 | 240Hz 不掉帧；采集可读最新 |
| **2.3** | `ModBackend.read_latest`；与 Memory 抽查对照；meta.`backend_id` | 同接口 |
| **2.4** | Mod SL，重置 &lt;3s | **P3 前门禁** |
| **2.5** | 文档化 enemies[]+mask → schema 2.x | 可先表结构、后合代码 |

Spike 失败：写清原因再议降级，不默默弃立项。稳态 IPC 可再升共享内存（方案文档）。

### 之后（摘要）

| Phase | 要做什么 |
|-------|----------|
| **P3** | BC-init PPO/KL 或残差；奖励 Δboss_hp / 罚受伤；失败局进集；止损对照表 |
| **P4** | 复盘 Agent（jsonl+图→诊断）→ 实验编排 → Option（超时不阻塞快回路） |
| **P5/P6** | enemies+课程→一门；五门结果向 |

### 本阶段不做

五门全挖静态链；CNN 主输入；LLM 出键；无快重置就上在线 RL。

---

## 4. 备忘（常用，不替代 yaml）

```text
Hornet boss_hp: UP+0x01F1FBC8 → … → +0x148；满血 900；仅 GG_Hornet_1
scene/game_state: UP+0x01F28838 同根；game_state +0x18C；4/5/3=PLAY/PAUSE/CUTSCENE
facing: UP+0x01F4F8B8 → … +0xB0；右=-1 左=+1（以实测为准）
CE 库: E:\缓存\tempdata\bosshp.sqlite（细节见方案文档 / 历史 commit）
```

```text
configs/  scripts/{probe_*,collect_expert}
src/bossmind/{env_tools,data,learning,…}
docs/BossMind_项目方案.md
models/ data/raw/   # gitignore
```

---

## 5. 里程碑（最近）

| 日期 | 事件 |
|------|------|
| 2026-08-06 | AGENTS 回调中等篇幅；P1/P2 Step 可执行；长文仍在 docs |
| 2026-08-06 | P2 Mod 立项；P0–P6；boss_hp+is_battle；路线重切 |
| 2026-08-05 | scene/game_state；Phase-BC→main；BC 骨架 |
| 更早 | vision/x/y smoke 等 → `git log` |
