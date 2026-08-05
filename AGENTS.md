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
| 动作标签 | 键盘钩子：`held` + `pressed` 边沿；逻辑键含 **tab**（12 维）；`inventory`/`esc` 可在 yaml 但不进 `_state` |
| hp 语义 | `session` 读失败时用上一帧填充；**真失败看 `read_error_streak>0`** |
| 图像 | **硬需求**：截图/写盘失败 → `error`；队列丢帧超限 → `discard` |
| max_hp 验链 | 与配置比对校验指针链；失败可清空全部地址缓存（刻意连坐）后重解析 |

### Schema 版本规则

| 变更 | 版本 | 老数据 |
|------|------|--------|
| 加可空字段 | minor | 可混训（补 None） |
| 改名 / 改语义 / 改必填 | **major** | **禁止混训** |

当前 `SCHEMA_VERSION = 1.1.1`：`tab`；`player_*` / `boss_*` 前缀名（**与 20260803 旧 smoke 的 `hp/x/y` 不兼容**）。loader **尚未**强制校验 version（刻意后置）。

### `is_battle` 语义（派生，原料必须落盘）

```text
is_battle = (game_state == PLAYING)
         AND (scene_name in 允许的 Boss 场景)
         AND (boss_hp is not None AND boss_hp > 0)
```

`get_is_battle` 仍占位恒 `True` → 无可靠 `win`；仅 `smoke_*` / `pipeline_*`，**禁止** `expert_v1_*`。

### 协作铁律（Agent 必读）

| 规则 | 说明 |
|------|------|
| **师父模式** | 用户自行实现；Agent：讲思路、给步骤、审代码、排错 |
| **禁止代写** | 除非用户明确要求「请代写 xxx」 |
| **推进节奏** | **双线**：B 采数/CE N2 ∥ A `Phase-BC` 上 BC 实数据验收→过拟合；正式 `train_bc`/`expert_v1` 门禁 |

**双设备**：A=`D:\BossMind`（CPU PyTorch 写/测 BC）；B=`E:\BossMind`（HK/采数/CE）；conda `BossMind` 3.12.13。  
正式大训预定 **WSL + ROCm**；A 机 CPU torch 仅开发。  
**分支**：BC 开发在本地 **`Phase-BC`**（基线曾为 `e089aa1`）；B 机改动需 push 后再与 `main` 合并。

---

## 2. 当前状态（2026-08-05）

| 字段 | 值 |
|------|-----|
| 阶段 | **BC 训练骨架已齐；等 B 真数据验收 ∥ CE N2** |
| 子课 A | B 机/新 schema 数据跑通 `BCPolicy.train` → BC.3 单局过拟合 |
| 子课 B | CE：scene / game_state / boss → 真 `is_battle` |
| Git | 分支 **`Phase-BC`**（基于 `e089aa1`）；hook/dataset/policy/collect 等 **本地未提交**；`models/` 已 gitignore |
| 采集判定 | **GO** `smoke_*` / `pipeline_*`；**NO** `expert_v1_*` |
| L3 BC | `learning/{actions,dataset,policy}.py`：FrameDataset、DataLoader、BCEWithLogits 训练循环、存 `MODEL_DIR/bc_model.pth` |
| BC 样本 | `(x,a)`；`held` 12 维；**含 `None` 的 obs 帧 skip**（不填 0 污染）；`load_batch` 仅 `end_reason==win` |
| 特征表 | 仍含 facing/boss 等 → CE 未接前真数据可能大量 skip；训前可临时收窄 `PLAY_INFO`/`BOSS_INFO` |
| 视觉 | ROI 已标定；`capture_ms_p95`≈7–9ms → 暂不异步截图 |
| 朝向 | 未接 |
| 更新 | 2026-08-05 |

- [x] Phase 0～1.3 + B x/y+vision 冒烟
- [x] BC.0 / BC.1 / BC.2 骨架（MLP+train+save；空 loader 会报错）
- [x] 评审修复（主流程相关）：hook 白名单 + `is_running` property；半局 `close`；load 缺 meta 跳过；None 帧 skip
- [ ] BC.2 真数据验收（B）→ BC.3 过拟合
- [ ] CE N2 → 真 `is_battle` → `expert_v1` → BC.4 正式训

---

## 3. 本轮清单与验收

### 代码侧

| ID | 任务 | 状态 |
|----|------|------|
| Phase 0～1.3 / smoke | 既有 | ✅ |
| BC.0–2 骨架 | actions / dataset / policy | ✅（待真数据验收） |
| Hook | `logic_key in _state`；`@property is_running` | ✅ |
| collect `_end_collect` | 未 close 则 `close`；防 pre_write 后泄漏 | ✅ |
| dataset | None skip；缺 meta/events 跳过；空 loader 保护 | ✅ |
| `models/` gitignore | ✅ | |
| 评审后置 | schema 强制校验、失焦过滤、train_bc 脚本、checkpoint 元信息、`.gitattributes`、调度器边角、键一致性测试 | **不做（非主流程）** |
| CE N2 | scene / game_state / boss | ☐ **当前（B）** |
| BC.3 / BC.4 | 过拟合 / 正式训 | ☐ 等数据与 CE |

### B 机下一步（采数 / 验收 BC）

```text
1. 同步 Phase-BC 或合并后的代码；pip install -e .；CPU/适用 torch
2. 用新 schema 采 smoke/pipeline（注意 win 过滤与特征 None→大量 skip）
3. 调用 BCPolicy.train(batch_name) 或等价入口；确认 loss 与 models/bc_model.pth
4. 可选：单局过拟合（BC.3）
闸门：hook 按 i 不脏标签；半局有 meta；空样本立刻报错
```

### L3 BC 步骤

```text
BC.0 ✅  BC.1 ✅  BC.2 骨架 ✅ / 真数据验收 ☐
BC.3 ☐ 过拟合   BC.4 ☐ 正式训（等 CE + expert_v1）
标签：held；含 None 的帧 skip；bool 可进 tensor
日志：默认无 basicConfig 时 logger.info 不显示 → 入口配 INFO 或用 print
```

### 明确不做 / 后置

```text
正式 train_bc 工程化、checkpoint 契约、schema loader 校验、失焦帧过滤
启发式 is_battle / expert_v1_* / 在线 RL / CNN 主输入 / LLM（Phase 1）
异步截图；为「优雅」改记拍
max_hp 验链失败连坐清缓存 —— 保留设计，不改
```

### 波 N2 — CE

坐标已采。**待做**：scene / game_state / boss → 真 `is_battle` → `expert_v1_*`。

---

## 4. 仓库

```text
configs/game_info.yaml
scripts/{probe_*,collect_expert}.py
src/bossmind/{config,paths,utils}.py   # MODEL_DIR = models/
src/bossmind/data/{schema,writer}.py
src/bossmind/env_tools/{memory,input,session,keyboard_hook,vision}.py
src/bossmind/learning/{actions,dataset,policy}.py
models/                                 # gitignore；权重本地
tests/{test_vision,test_episode_writer_images}.py
results/phase0.md
```

---

## 5. 里程碑日志

| 日期 | 事件 |
|------|------|
| 2026-08-05 | **BC 骨架 + 主流程评审修复**：Phase-BC；hook/`is_running`；None skip；writer 半局 close；policy 空数据保护；Step6/7 工程项后置；等 B 真数据 |
| 2026-08-04 | L3 BC 开工：BC.0/1；tab；schema 1.1.1 前缀名；jsonlines |
| 2026-08-03 | B x/y+vision 冒烟；坐标接线；vision 合入 |
| 2026-08-01 | B 事件 smoke；Phase 1.2；soul |
| 2026-07-31 | 观测源/schema/`is_battle` 定稿 |
| 2026-07-29 | Phase 0 收官 |
