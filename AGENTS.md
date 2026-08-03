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
| 阶段 | **Phase 1 — B 机 smoke 已通过，进入 CE N2** |
| 子课 | CE 挖 scene / game_state / 坐标 / boss → 接 `memory.py` → 再开 `expert_v1_*` |
| Git | `main` @ `92d1828`（Phase 1.2）；B 机本地有 smoke 数据 + frame0 修复（待 commit） |
| 采集判定 | **GO pipeline smoke only**（`batch_id` 须 `smoke_` / `pipeline_`） |
| 正式训练批次 | **NO**（等 CE N2 + 真 `is_battle`） |
| B 机 smoke | **3 局** `data/raw/smoke_1/`；最新 `20260801_215332`：3493 帧、60Hz、0 dropped |
| 记拍 | **冻结** `held` + `pressed`（快速按键无 held 漏记；pressed 保留子帧边沿） |
| soul | **已接** `MPCharge` @ PlayerData `+0x1D4`（yaml 已有；smoke 验证 35→2 随治疗） |
| frame0 | **已修** `collect_expert` 录帧前 `snapshot()` 清积压 |
| 更新 | 2026-08-01 |

- [x] Phase 0 收官（`probe_loop` 10/10，`results/phase0.md`）
- [x] Phase 1.1：`keyboard_hook` + `probe_keyboard`（`6b61b60`）
- [x] Phase 1.2：采集管线 config/schema/writer/`collect_expert`（`92d1828`）
- [x] B 机 smoke：`smoke_1` 三局；frame0 / heal / 快速按键验收通过
- [ ] CE N2：scene / game_state / player x,y / boss / 真 `is_battle`

---

## 3. 本轮清单与验收

### 代码侧（`92d1828` 已 push，B 待跑）

| ID | 任务 | 状态 |
|----|------|------|
| S0/S1 | smoke 前门禁 | ✅ |
| F0-2/3/4 | timeout / finally / batch+boss 口径 | ✅ |
| F1-4 | collect 阈值进 yaml | ✅ |
| F0-1 soul | `MPCharge` @ `+0x1D4` 已写入 yaml 并 smoke 验证 | ✅ |
| B smoke | probe 全套 + `smoke_*` 采集 | ✅ |
| CE N2 | scene / game_state / 坐标 / boss | ☐ **当前** |
| F1-2 日志降噪 | backlog | — |
| F1-3 check_episode | backlog | — |

### B 机 smoke 顺序（pull 后）

```text
1. git pull && pip install -e .
2. probe_attach → probe_hp（hp/max_hp 非 None；soul 未接可能刷日志）
3. probe_keyboard（held 稳、pressed 边沿合理）
4. probe_loop（读档 10 轮；Boss 场景 `GG_Hornet_1`）
5. python scripts/collect_expert.py  # batch_id=smoke_YYYYMMDD_*
   2～5 局（含 F12 / death 或 timeout）
   检查 meta：dt_p95、n_dropped、hp 有变化、read_error_streak 近 0
```

**B 机 smoke 摘要（2026-08-01）**：`smoke_1` 三局；`215332` 局 frame0 干净、治疗 frame 2826–2927 / HP 1→2、快速按键无 held 漏记；`held`+`pressed` 保留。

### 明确不做（底层冻结）

```text
PointerChain / Config 大重构 / 完整 tests+CI / Writer 大改
启发式假 is_battle / expert_v1_* / train_bc
为「优雅」改记拍或 held/pressed
```

### 波 N2 — CE（smoke 已通过，当前）

scene / game_state / player x,y / boss / 真 `is_battle` 派生 → 抽检 → 再开 `expert_v1_*`。（soul 已完成）

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
| 2026-08-01 | **B smoke 通过**：`smoke_1` 三局；frame0 修复；soul/治疗/快速按键验收；记拍保留双轨 |
| 2026-08-01 | **进度同步**：Phase 1.2 已 push；`GG_Hornet_1` 为当前 Boss 场景 |
| 2026-08-01 | Phase 1.2 提交 `92d1828`：collect 管线 + F0/F1 加固 |
| 2026-08-01 | F1-4：collect 阈值进 yaml；batch 闸门；底层冻结宣言 |
| 2026-08-01 | F0：timeout / try-finally；soul `MPCharge` @ `+0x1D4` 已接 |
| 2026-08-01 | Opus 复评 S0/S1；非 CE 加固大部完成 |
| 2026-07-31 | 观测源/schema 版本/`is_battle` 语义定稿 |
| 2026-07-30 | 协作铁律；Phase 1 启动 |
| 2026-07-29 | Phase 0 收官 10/10 |
