# BossMind — Agent 交接

> Git 同步代码；本文档同步进度。换设备先读 **§2 §3**，再动手。  
> 每轮结束：改 §2/§3 → 有里程碑写 §5 → `commit` + `push`。

### 文档说明（2026-07-27 精简）

本文档由 **~555 行 → ~100 行** 主动压缩，**未改项目约定**，只为省 Agent 上下文。  
**找旧内容**：`git log -p -- AGENTS.md`；WSL 细节需要时再写 `docs/env-b.md`。

---

## 1. 约定（已确认，勿重复讨论）

| 项 | 内容 |
|----|------|
| 目标 | 神居 Pantheon 单 Boss **速通/无伤**；BC + LLM Option + 局外训练师（弱融合） |
| 评估场景 | Hall of Gods；MVP：Hornet Protector（`GG_Hornet_1`）/ Pantheon Attuned |
| 重置 | **评估/演示** = 菜单读档；**训练采数** = DebugMod SL（Phase 1 中段） |
| 不做（Phase 1） | CNN 主输入、LLM、在线 RL、评估用 mod **重置** |

### 观测源决策（2026-07-31 定稿）

| 项 | 决定 |
|----|------|
| Phase 1 观测源 | **进程内存**（CE / Mono 指针链），不用 Mod 广播 |
| 采集与评估 | **必须同源**（同一套 `get_observation()`） |
| Boss 字段 | 短期 CE/Mono；挖不通则批次标 `pipeline_only`，不进训练集 |
| 采样率 | 正式批次 **60Hz**；游戏锁 60fps；试采测 dt 后再考虑提高 |
| Boss 标识 | meta.`boss` 为 `str`，取值建议场景名如 `GG_Hornet_1` |
| 动作标签 | 键盘钩子：`held` + `pressed` 边沿 |
| hp 语义 | `session` 读失败时用上一帧填充；**真失败看 `read_error_streak>0`**，训前过滤 |

### Schema 版本规则

| 变更 | 版本 | 老数据 |
|------|------|--------|
| 加可空字段 | minor（1.0→1.1） | 可混训（补 None） |
| 改名 / 改语义 / 改必填 | **major**（1→2） | **禁止混训** |

### `is_battle` 语义（派生，原料必须落盘）

```text
is_battle = (game_state == PLAYING)
         AND (scene_name in 允许的 Boss 场景)
         AND (boss.hp is not None AND boss.hp > 0)
```

当前 `memory.get_is_battle` 仍为占位恒 `True` → **不会产生 `end_reason=win`**；在 CE 接好之前只允许 `smoke_*` / `pipeline_*` 批次，**禁止** `expert_v1_*`。

### 协作铁律（Agent 必读）

| 规则 | 说明 |
|------|------|
| **师父模式** | 用户自行实现；Agent：讲思路、给步骤、审代码、排错 |
| **禁止代写** | 除非用户明确要求「请代写 xxx」 |
| **推进节奏** | 本轮：B 机 smoke → 实采（仍 smoke_/pipeline_）→ CE N2 |

**双设备**：A=`D:\BossMind`；B=`E:\BossMind`（HK/采数）；conda `BossMind` 3.12.13。

---

## 2. 当前状态（2026-08-01）

| 字段 | 值 |
|------|-----|
| 阶段 | **B 机 smoke / 管线实采** |
| 子课 | pull 后 probe 全绿 → `smoke_*` 连打验收 |
| 采集判定 | **GO pipeline smoke only**（`batch_id` 须 `smoke_` / `pipeline_`） |
| 正式训练批次 | **NO**（等 CE + `is_battle` 真值） |
| 底层策略 | **冻结**（memory/记拍/schema major 勿再抠）；例外：可复现崩坏 + CE 波次 |
| soul | **暂搁**：拿到 CE 偏移再接；未接前 soul 可为 None |

**已完成**

- [x] 采集管线：config / schema / writer / collect（60Hz、追帧、held/pressed、meta、失焦、HP streak）
- [x] S0/S1：拼写、`except`、max_hp 上界、pressed 去重、boss 名、`probe_keyboard`
- [x] F0：timeout、`wait is_battle` 进 try/finally、batch 前缀闸门
- [x] F1-4：采集阈值进 `collect:`（`max_episode_s` / `max_hp_read_fail` / `max_focus_lost` / `max_dropped`）
- [x] `max_hp_offset: 0x19C`；probe 走 `get_player_states` / `get_observation`

---

## 3. 本轮清单与验收

### 代码侧（已齐，可 push）

| ID | 任务 | 状态 |
|----|------|------|
| S0/S1 | smoke 前门禁 | ✅ |
| F0-2/3/4 | timeout / finally / batch+boss 口径 | ✅ |
| F1-4 | collect 常量外置 yaml | ✅ |
| F0-1 soul 短路 | **用户选择暂搁**（等偏移） | ⏸ |
| F1-1 stale hp 文档 | 见 §1 hp 语义 | ✅ |
| F1-2 日志降噪 | 可选 backlog | — |
| F1-3 check_episode | 可选 backlog | — |

### B 机 smoke 顺序（pull 后）

```text
1. probe_attach → probe_hp（hp/max_hp 非 None；注意 soul 未接可能刷日志）
2. probe_keyboard（held 稳、pressed 边沿合理）
3. probe_loop（读档 10 轮）
4. collect：batch_id=smoke_* ，2～5 局（含 F12 / death或timeout）
   检查 meta：dt_p95、n_dropped、hp 有变化、read_error_streak 近 0
```

### 明确不做（底层冻结）

```text
PointerChain / Config 大重构 / 完整 tests+CI / Writer 大改
启发式假 is_battle / expert_v1_* / train_bc
为「优雅」改记拍或 held/pressed
```

### 波 N2 — CE（smoke 稳定之后）

scene / game_state / soul / x,y / boss / `is_battle` 派生 → 抽检 → 再开 `expert_v1_*`。

---

## 4. 仓库

```text
configs/game_info.yaml          # collect.max_* 在此改，勿改代码硬编码
scripts/{probe_*,collect_expert}.py
src/bossmind/{config,paths,utils}.py
src/bossmind/data/{schema,writer}.py
src/bossmind/env_tools/{memory,input,session,keyboard_hook}.py
src/bossmind/env_tools/reset_backends/{menu,mod}.py
results/phase0.md
```

---

## 5. 里程碑日志

| 日期 | 事件 |
|------|------|
| 2026-08-01 | F1-4：collect 阈值进 yaml；batch 闸门；底层冻结宣言；准备 push → B smoke |
| 2026-08-01 | F0：timeout / try-finally；soul 暂搁等 CE 偏移 |
| 2026-08-01 | Opus 复评 S0/S1；非 CE 加固大部完成 |
| 2026-07-31 | 观测源/schema 版本/`is_battle` 语义定稿 |
| 2026-07-30 | 协作铁律；Phase 1 启动 |
| 2026-07-29 | Phase 0 收官 10/10 |
