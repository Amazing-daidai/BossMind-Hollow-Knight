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
| 不做（Phase 1） | CNN **主**输入、LLM、在线 RL、评估用 mod **重置** |

### 观测源决策（2026-07-31 定稿）

| 项 | 决定 |
|----|------|
| Phase 1 观测源 | **进程内存**（CE / Mono 指针链），不用 Mod 广播 |
| 采集与评估 | **必须同源**（同一套 `get_observation()` / `Vision.capture`） |
| Boss 字段 | 短期 CE/Mono；挖不通则批次标 `pipeline_only`，不进训练集 |
| 采样率 | 正式批次 **60Hz** 事件；视觉旁路 **10Hz** 固定战斗 ROI（先测再调） |
| Boss 标识 | meta.`boss` 为 `str`，取值建议场景名如 `GG_Hornet_1` |
| 动作标签 | 键盘钩子：`held` + `pressed` 边沿 |
| hp 语义 | `session` 读失败时用上一帧填充；**真失败看 `read_error_streak>0`**，训前过滤 |
| 图像 | **硬需求**：截图/写盘失败 → `end_reason=error`；队列丢帧超限 → `discard` |

### Schema 版本规则

| 变更 | 版本 | 老数据 |
|------|------|--------|
| 加可空字段 | minor（1.0→1.1） | 可混训（补 None） |
| 改名 / 改语义 / 改必填 | **major**（1→2） | **禁止混训** |

当前 `SCHEMA_VERSION = 1.1.0`（vision provenance：`vision_*` / `capture_ms_*` / `image_error` 等可空）。

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
| **推进节奏** | 本轮：B 机 pull → vision smoke（看 `capture_ms_*`）→ CE N2 |

**双设备**：A=`D:\BossMind`；B=`E:\BossMind`（HK/采数）；conda `BossMind` 3.12.13。

---

## 2. 当前状态（2026-08-03）

| 字段 | 值 |
|------|-----|
| 阶段 | **Phase 1.3 vision 已合入 main；B 机待 vision smoke** |
| 子课 | B 测 ROI/`capture_ms` → CE 挖 scene / game_state / 坐标接线 / boss → 真 `is_battle` |
| Git | `main` = `vision_feature` @ `89c3a7a`（1.2 + B soul/坐标 yaml + 1.3 vision） |
| 采集判定 | **GO pipeline smoke only**（`batch_id` 须 `smoke_` / `pipeline_`） |
| 正式训练批次 | **NO**（等 CE N2 + 真 `is_battle`） |
| B 机事件 smoke | **3 局** `data/raw/smoke_1/`（2026-08-01）；frame0 / heal / 快键已过 |
| 视觉 | 同步 `mss.grab`@主循环 10Hz；JPEG 写盘异步；ROI 占位 `200×200`（须实机标定） |
| 截图性能 | B 显示器 **240Hz**；先读 meta `capture_ms_p50/p95`，紧张再异步截图 |
| soul | **已接** `MPCharge` @ `+0x1D4` |
| 坐标 | yaml 有 `player_position`（B CE）；**尚未**接 `memory.py` 读 x/y |
| frame0 | **已修** 录帧前 `snapshot()` 清积压 |
| 更新 | 2026-08-03 |

- [x] Phase 0 收官（`probe_loop` 10/10，`results/phase0.md`）
- [x] Phase 1.1：`keyboard_hook` + `probe_keyboard`（`6b61b60`）
- [x] Phase 1.2：采集管线 config/schema/writer/`collect_expert`（`92d1828`）
- [x] B 机事件 smoke：`smoke_1` 三局；frame0 / heal / 快速按键验收通过
- [x] Phase 1.3：`Vision` + ImageWriter JPEG + schema 1.1.0；与 B `main` 合并（`89c3a7a`）
- [ ] B 机 vision smoke：标定 `vision_region`；验收帧文件 + `capture_ms_*`
- [ ] CE N2：scene / game_state / player x,y 接线 / boss / 真 `is_battle`

---

## 3. 本轮清单与验收

### 代码侧（`89c3a7a` 已 push）

| ID | 任务 | 状态 |
|----|------|------|
| S0/S1 | smoke 前门禁 | ✅ |
| F0 / F1-4 | timeout / finally / batch / collect 阈值 yaml | ✅ |
| F0-1 soul | `+0x1D4` yaml + memory | ✅ |
| B 事件 smoke | probe + `smoke_*` | ✅ |
| V1 vision | `vision.py` / writer 队列 / collect 10Hz / tests | ✅ |
| V1 审阅 | 改动 1–9 保留（3 去掉客户区/黑图判定） | ✅ |
| B vision smoke | ROI + `capture_ms` + 帧落盘 | ☐ **当前** |
| CE N2 | scene / game_state / 坐标接线 / boss | ☐ |
| 异步截图 | 仅当 `capture_ms_p95` 紧张再做 | backlog |
| F1-2 / F1-3 | 日志降噪 / check_episode | backlog |

### B 机 vision smoke（pull 后）

```text
1. git pull && pip install -e .
2. 确认 window_title / 实机标定 collect.vision_region
3. probe_attach → probe_hp（soul 应非 None）→ probe_keyboard → probe_loop
4. python scripts/collect_expert.py  # smoke_* ；2～3 局
5. 查 meta：dt_p95、n_dropped、image_dropped、n_frames、
   capture_ms_p50/p95、image_error；目检 frames/*.jpg
闸门：capture_ms_p95 < 10ms → 暂不异步截图；≥30ms 或频繁丢帧再开 VisionWorker
```

**B 机事件 smoke 摘要（2026-08-01）**：`smoke_1` 三局；`215332` frame0 干净、治疗 HP 1→2、快键无 held 漏记。

### 明确不做（仍冻结）

```text
PointerChain / Config 大重构 / 完整 tests+CI
启发式假 is_battle / expert_v1_* / train_bc
为「优雅」改记拍或 held/pressed
未测紧张前不上异步截图 / DXGI
```

### 波 N2 — CE

scene / game_state / player x,y（yaml 已有链，待接线）/ boss / 真 `is_battle` → 抽检 → `expert_v1_*`。

---

## 4. 仓库

```text
configs/game_info.yaml          # collect.max_* / vision_*；player_position
scripts/{probe_*,collect_expert}.py
src/bossmind/{config,paths,utils}.py
src/bossmind/data/{schema,writer}.py   # schema 1.1.0；ImageWriter 异步 JPEG
src/bossmind/env_tools/{memory,input,session,keyboard_hook,vision}.py
src/bossmind/env_tools/reset_backends/{menu,mod}.py
tests/{test_vision,test_episode_writer_images}.py
results/phase0.md
```

---

## 5. 里程碑日志

| 日期 | 事件 |
|------|------|
| 2026-08-03 | **main ← vision_feature**：`89c3a7a`；soul/坐标 yaml + vision 管线；AGENTS 同步 |
| 2026-08-03 | Phase 1.3：10Hz ROI 截图、JPEG 写盘、meta provenance；性能评估：B 240Hz 先测再异步 |
| 2026-08-01 | **B smoke 通过**：`smoke_1` 三局；frame0；soul/治疗/快键；记拍双轨 |
| 2026-08-01 | Phase 1.2 `92d1828`：collect 管线 + F0/F1；soul `+0x1D4` |
| 2026-07-31 | 观测源/schema 版本/`is_battle` 语义定稿 |
| 2026-07-30 | 协作铁律；Phase 1 启动 |
| 2026-07-29 | Phase 0 收官 10/10 |
