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
| 采样率 | 正式批次 **60Hz** 事件；视觉旁路 **10Hz** 固定战斗 ROI |
| Boss 标识 | meta.`boss` 为 `str`，取值建议场景名如 `GG_Hornet_1` |
| 动作标签 | 键盘钩子：`held` + `pressed` 边沿；逻辑键含 **tab**（12 维） |
| hp 语义 | `session` 读失败时用上一帧填充；**真失败看 `read_error_streak>0`**，训前过滤 |
| 图像 | **硬需求**：截图/写盘失败 → `end_reason=error`；队列丢帧超限 → `discard` |

### Schema 版本规则

| 变更 | 版本 | 老数据 |
|------|------|--------|
| 加可空字段 | minor（1.0→1.1） | 可混训（补 None） |
| 改名 / 改语义 / 改必填 | **major**（1→2） | **禁止混训** |

当前工作树 `SCHEMA_VERSION = 1.1.1`：vision provenance 保留；新增 `tab`；`PlayerStates`/`BossStates` 字段改为 `player_hp` / `player_x` 等前缀名（**与 20260803 旧 smoke 的 `hp/x/y` 不兼容**，BC 用新采或 `pipeline_fake`）。

### `is_battle` 语义（派生，原料必须落盘）

```text
is_battle = (game_state == PLAYING)
         AND (scene_name in 允许的 Boss 场景)
         AND (boss.hp is not None AND boss.hp > 0)   # 落盘字段名以 schema 为准（现为 boss_hp）
```

当前 `memory.get_is_battle` 仍为占位恒 `True` → **不会产生可靠 `end_reason=win`**；在 CE 接好之前只允许 `smoke_*` / `pipeline_*`，**禁止** `expert_v1_*`。

### 协作铁律（Agent 必读）

| 规则 | 说明 |
|------|------|
| **师父模式** | 用户自行实现；Agent：讲思路、给步骤、审代码、排错 |
| **禁止代写** | 除非用户明确要求「请代写 xxx」 |
| **推进节奏** | **双线**：CE N2（scene/game_state/boss）∥ L3 BC stub（BC.2→过拟合）；正式 `train_bc` / `expert_v1` 仍门禁 |

**双设备**：A=`D:\BossMind`（可 CPU PyTorch 写/测 BC）；B=`E:\BossMind`（HK/采数/CE）；conda `BossMind` 3.12.13。  
正式大训仍预定 **WSL + ROCm**（见 `requirements.txt` 头注释）；A 机 CPU torch **仅临时开发**。

---

## 2. 当前状态（2026-08-04）

| 字段 | 值 |
|------|-----|
| 阶段 | **双线：CE N2 进行中 ∥ L3 BC.0–1 已完成，下一课 BC.2** |
| 子课 A | BC.2：`PolicyMLP` + BCEWithLogits；假数据/`load_episode` 能 backward |
| 子课 B | CE N2：scene / game_state / boss → 真 `is_battle` |
| Git | `origin/main` @ `3dba95b`；**本地未提交**：`learning/`、schema/tab、deps 等 |
| 采集判定 | **GO** `smoke_*` / `pipeline_*`；**NO** `expert_v1_*` |
| B 机 x/y+vision smoke | 三局 `20260803_*` 已通过（字段名为旧 `hp/x/y`） |
| 视觉 | ROI `190,230,1550×740`；`capture_ms_p95` 6.8–8.9ms → **暂不异步截图** |
| L3 BC | `src/bossmind/learning/`：`actions.py`（BC.0）+ `dataset.py`（BC.1） |
| BC 标签 | `held`→12 维（含 tab）；样本 `(x, a)`；第一版只用 held |
| BC 过滤 | `load_batch` 仅 `end_reason==win`（真数据暂少）；通路/过拟合用 **`load_episode`** |
| PyTorch（A） | 计划/可装 **CPU Stable**：`pip install torch --index-url https://download.pytorch.org/whl/cpu` |
| 依赖 | `jsonlines>=4.0,<5` 已写入 `requirements.txt` / `pyproject.toml` `[data]` |
| 朝向 | 未接；低优先级 |
| 更新 | 2026-08-04 |

- [x] Phase 0～1.3：探针 / 采集 / vision / x/y 联合冒烟（见既有里程碑）
- [x] BC.0：`ACTION_KEY` + `key_to_vec` / `obs_to_vec`（含 tab；obs 可含 None/bool，进张量前再收）
- [x] BC.1：`load_episode` + `load_batch`（假局 `pipeline_fake` 验证）
- [ ] BC.2：PolicyMLP + BCEWithLogits + backward
- [ ] BC.3：单局过拟合
- [ ] CE N2 余下：scene / game_state / boss / 真 `is_battle`
- [ ] BC.4 / 正式 `train_bc`：等 CE + `expert_v1` 门禁

---

## 3. 本轮清单与验收

### 代码侧

| ID | 任务 | 状态 |
|----|------|------|
| … | Phase 0～1.3 / B smoke / vision 审阅（既有） | ✅ |
| schema 1.1.1 | `tab`；`player_*` / `boss_*` 字段前缀；探针/collect 已跟名 | 本地 ✅ 待 commit |
| BC.0 | `learning/actions.py` | ✅ |
| BC.1 | `learning/dataset.py`（`(x,a)`；`jsonlines`） | ✅ |
| deps | `jsonlines`；A 机 CPU torch（用户装） | ✅ / 进行中 |
| BC.2 | `learning/policy.py` MLP | ☐ **当前（A）** |
| CE N2 | scene / game_state / boss / 真 `is_battle` | ☐ **当前（B）** |
| 朝向 / 异步截图 / F1-2/3 | backlog | — |
| 正式 `train_bc` / `expert_v1` | **冻结**至 CE 门禁 | 冻 |

### B 机采集冒烟（2026-08-03 已通过）

```text
1. git pull && pip install -e .
2. window_title / vision_region
3. probe_attach → probe_hp → probe_keyboard → probe_loop
4. collect_expert smoke_* ；查 meta + frames
闸门：capture_ms_p95 < 10ms → 暂不异步截图
```

**B 机 x/y+vision 冒烟（2026-08-03）** — `smoke_1/20260803_{221846,222026,222253}`：

```text
闸门：≈60.08Hz；n_dropped=0；image_dropped=0；capture_ms_p95 6.8–8.9ms；
  x/y 无 null；read_error_streak=0；frame0 pressed 干净。
局2 受击：HP 当帧↓，y 延迟 ~19 帧升。局3 超冲：长按 h 松手后 x 爆发、y 平坦。
```

**分析注意**：判受伤看 HP 当帧 + 延迟 y；判超冲看长按 `super_dash` + 松手后 x；`pressed.jump`≠起跳。

### L3 BC stub 步骤（A 机）

```text
BC.0 ✅ 键序+向量   BC.1 ✅ 读局   BC.2 ☐ MLP+backward
BC.3 ☐ 单局过拟合   BC.4 ☐ 过滤+正式训（等 CE）
过拟合/通路：load_episode(路径)；勿依赖 load_batch 的 win 过滤
进 tensor 前：None→0.0，bool→0/1 float；BCEWithLogits（logits 勿先 sigmoid）
```

### 明确不做（仍冻结）

```text
启发式假 is_battle / expert_v1_* / 正式 train_bc
PointerChain / Config 大重构 / 完整 tests+CI
为「优雅」改记拍；未紧张不上异步截图 / DXGI
A 机不装 CUDA/ROCm 版 PyTorch（临时 CPU 即可）
```

### 波 N2 — CE

坐标已采。**待做**：scene / game_state / boss → 真 `is_battle` → `expert_v1_*`。  
不用 `GameManager._instance`；朝向可后补。

---

## 4. 仓库

```text
configs/game_info.yaml
scripts/{probe_*,collect_expert}.py
src/bossmind/{config,paths,utils}.py
src/bossmind/data/{schema,writer}.py          # 1.1.1；ImageWriter
src/bossmind/env_tools/{memory,input,session,keyboard_hook,vision}.py
src/bossmind/learning/{actions,dataset}.py    # L3 BC stub；policy 待写
src/bossmind/env_tools/reset_backends/{menu,mod}.py
tests/{test_vision,test_episode_writer_images}.py
results/phase0.md
```

---

## 5. 里程碑日志

| 日期 | 事件 |
|------|------|
| 2026-08-04 | **L3 BC 开工**：BC.0/1（`learning/actions|dataset`）；tab→12 维；schema 1.1.1 字段前缀；`jsonlines`；下一步 BC.2；CE N2 并行 |
| 2026-08-03 | **B x/y+vision 冒烟通过**：三局 `20260803_*`；坐标+按键+受击/超冲模式核对 |
| 2026-08-03 | 坐标链 + `memory` x/y；冒烟合入 `3dba95b`；vision 合入 `89c3a7a` |
| 2026-08-01 | B 事件 smoke；Phase 1.2；soul `+0x1D4` |
| 2026-07-31 | 观测源/schema/`is_battle` 定稿 |
| 2026-07-30 | 协作铁律；Phase 1 启动 |
| 2026-07-29 | Phase 0 收官 10/10 |
