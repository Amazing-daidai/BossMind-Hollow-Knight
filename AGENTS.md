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

`get_is_battle()` **已实现**（`PLAYING` + `boss_info` 场景 + `boss_hp>0`）；`game_state==6` 过场几帧不算战斗。

### 协作铁律（Agent 必读）

| 规则 | 说明 |
|------|------|
| **师父模式** | 用户自行实现；Agent：讲思路、给步骤、审代码、排错 |
| **禁止代写** | 除非用户明确要求「请代写 xxx」 |
| **推进节奏** | **双线**：B 采数/CE N2 ∥ A BC 真数据验收→过拟合；正式 `train_bc`/`expert_v1` 门禁 |
| **脚本纪律** | 不新增临时验收/CE 脚本；验收用既有 `probe_*`；CE 链存机外 sqlite |

**双设备**：A=`D:\BossMind`（CPU PyTorch 写/测 BC）；B=`E:\BossMind`（HK/采数/CE）；conda `BossMind` 3.12.13。  
正式大训预定 **WSL + ROCm**；A 机 CPU torch 仅开发。

---

## 2. 当前状态（2026-08-05）

| 字段 | 值 |
|------|-----|
| 阶段 | **CE N2（Hornet）齐；真 `is_battle` 已接；可采 expert 前需 B 验收** |
| 子课 A | B 机新 schema + `boss_hp` 采数 → `BCPolicy.train` → BC.3 过拟合 |
| 子课 B | B 验收：走廊/房内/暂停 `is_battle`；正式 `expert_v1_*` 门禁 |
| Git | **`main` ← `Phase-BC` 已合并** |
| 采集判定 | **GO** `smoke_*` / `pipeline_*`；**NO** `expert_v1_*` |
| B 机 x/y+vision smoke | 三局 `20260803_*` 已通过（字段名为旧 `hp/x/y`） |
| L3 BC | `learning/{actions,dataset,policy}.py`：FrameDataset、DataLoader、BCEWithLogits、存 `MODEL_DIR/bc_model.pth` |
| BC 样本 | `(x,a)`；`held` 12 维；**含 `None` 的 obs 帧 skip**；`load_batch` 仅 `end_reason==win` |
| 特征表 | 仍含 facing/boss 等 → CE 未接前真数据可能大量 skip；训前可临时收窄 `PLAY_INFO`/`BOSS_INFO` |
| 视觉 | ROI `190,230,1550×740`；`capture_ms_p95` 6.8–8.9ms → **暂不异步截图** |
| 朝向 | yaml + `memory.py`（右=True 左=False） | ✅ |
| scene_name | yaml + memory + session；链 `+0x01F28838` 多场景/重启已验 | ✅ |
| game_state | 同链 `+0x18C`；4/5/3=PLAYING/PAUSED/CUTSCENE；进门偶发 6 几帧 | ✅ |
| boss_hp | `GG_Hornet_1` 链 `+0x01F1FBC8`；`HealthManager+0x148`；重启 879/满血 900 验 | ✅ |
| is_battle | 派生：`PLAYING`+场景在 `boss_info`+`boss_hp>0` | ✅ |
| 更新 | 2026-08-06 |

- [x] Phase 0～1.3 + B x/y+vision 冒烟
- [x] BC.0 / BC.1 / BC.2 骨架（MLP+train+save；空 loader 会报错）
- [x] 评审修复：hook 白名单 + `is_running` property；半局 `close`；load 缺 meta 跳过；None 帧 skip
- [x] 朝向 CE：±1.0 扫描 → pointer scan → yaml `player_facing`；重启后与 x/y 同验通过
- [x] 朝向 CE + memory 接线
- [x] scene_name CE + yaml + memory + session（多场景/重启验）
- [x] game_state Mono+同链验证（4/5/3）+ yaml + memory + session
- [x] boss_hp（GG_Hornet_1）CE + yaml + memory + session；重启满血 900 验
- [x] 真 `get_is_battle()`（非占位）
- [ ] BC.2 真数据验收（B）→ BC.3 过拟合 → `expert_v1_*` 试采

---

## 3. 本轮清单与验收

### 代码侧

| ID | 任务 | 状态 |
|----|------|------|
| Phase 0～1.3 / smoke | 既有 | ✅ |
| schema 1.1.1 | `tab`；`player_*` / `boss_*` 前缀 | ✅ |
| BC.0–2 骨架 | actions / dataset / policy | ✅（待真数据验收） |
| Hook | `logic_key in _state`；`@property is_running` | ✅ |
| collect `_end_collect` | 未 close 则 `close`；防 pre_write 后泄漏 | ✅ |
| dataset | None skip；缺 meta/events 跳过；空 loader 保护 | ✅ |
| `models/` gitignore | | ✅ |
| CE 朝向 yaml | `player_facing` 静态链 B 验证 + 写入 | ✅ |
| memory facing | 读 float → `player_facing_right` | ✅ |
| CE scene_name | pointer scan + 多场景/重启验证 | ✅ |
| memory scene_name | `get_scene_name()` → `Observation.scene_name` | ✅ |
| CE game_state | Mono `GameManager+0x18C`；与 scene 同静态链 | ✅ |
| memory game_state | `get_game_state()` → `Observation.game_state` | ✅ |
| CE boss_hp Hornet | pointer scan → 最短链 `0x1F1FBC8`；重启 rescan 验 | ✅ |
| memory boss_hp | `get_boss_hp()` 按 `scene_name` 选链；换房清缓存 | ✅ |
| 真 is_battle | `get_is_battle()` 派生 | ✅ |
| BC.3 / BC.4 | 过拟合 / 正式训 | ☐ **当前（B）** |
| 评审后置 | schema 强制校验、失焦过滤、train_bc 脚本、checkpoint 元信息等 | **不做（非主流程）** |

**朝向链（2026-08-04，重启已验）**：

```text
UnityPlayer.dll + 0x01F4F8B8
  → read_u64 → +0x0 → +0x3E8 → +0x0 → +0x28 → +0x60 → read_u64 → +0xB0 → read_float
右 = -1.0，左 = +1.0（与常见 facingRight bool 相反，以实测为准）
同局复验：x/y 链 +0x01F4FD90 仍有效（y≈60.658 神居平台）
```

**scene_name 链（2026-08-05，多场景+重启已验）**：

```text
UnityPlayer.dll + 0x01F28838（与 player_info 同根）
  → read_u64 → +0x20 → +0x88 → +0x18 → +0x8 → +0x20 → read_u64 → +0x20（sceneName 指针槽）
  → read_u64(slot) → string +0x10 length / +0x14 UTF-16
已验：GG_Workshop、GG_Hornet_1、GG_False_Knight；Mono 字段 GameManager+0x20
```

**game_state（2026-08-05，与 scene_name 同链）**：

```text
UnityPlayer.dll + 0x01F28838（同 scene_name / player_info 根）
  → 同 offsets → +0x18C → read_int（GameManager.gameState）
枚举实测：4=PLAYING（能操控） 5=PAUSED  3=白屏/过场（CUTSCENE）
无需单独 pointer scan；final_offset 0x18C vs scene 的 0x20
```

**boss_hp 链（2026-08-06，GG_Hornet_1，重启 879 + 满血 900 验）**：

```text
UnityPlayer.dll + 0x01F1FBC8
  → read_u64 → +0x238 → +0x130 → +0x18 → +0x0 → +0x148 → read_int（HealthManager.hp）
满血 900；仅 scene_name==GG_Hornet_1 时读取；勿跨 Boss 复用
CE 指针库：`E:\缓存\tempdata\bosshp.sqlite` 已缩至 **1 条**（resultid=2602；备份 `bosshp.sqlite.bak` 含原 3059 条）
若 yaml 链不稳定，用 CE 打开该 sqlite 或从 `.bak` 恢复后再筛
```

### B 机下一步（采数 / 验收 BC）

```text
1. git pull；pip install -e .；CPU/适用 torch
2. 用新 schema 采 smoke/pipeline（注意 win 过滤与特征 None→大量 skip）
3. 调用 BCPolicy.train(batch_name)；确认 loss 与 models/bc_model.pth
4. 可选：单局过拟合（BC.3）
闸门：hook 按 i 不脏标签；半局有 meta；空样本立刻报错
```

**B 机 x/y+vision 冒烟（2026-08-03）** — `smoke_1/20260803_{221846,222026,222253}`：

```text
闸门：≈60.08Hz；n_dropped=0；image_dropped=0；capture_ms_p95 6.8–8.9ms；
  x/y 无 null；read_error_streak=0；frame0 pressed 干净。
局2 受击：HP 当帧↓，y 延迟 ~19 帧升。局3 超冲：长按 h 松手后 x 爆发、y 平坦。
```

**分析注意**：判受伤看 HP 当帧 + 延迟 y；判超冲看长按 `super_dash` + 松手后 x；`pressed.jump`≠起跳。

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

**Hornet `boss_hp` + scene/game_state + facing 已齐；真 `is_battle` 已接。** 其它 Boss 另挖链。不用 `GameManager._instance`。

---

## 4. 仓库

```text
configs/game_info.yaml          # player_* / scene / game_state / boss_info
scripts/{probe_*,collect_expert}.py   # 不再新增临时验收脚本
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
| 2026-08-06 | **boss_hp GG_Hornet_1 定稿** + 真 `is_battle`；重启 879/满血 900；`bosshp.sqlite` 缩至 1 链 |
| 2026-08-05 | **game_state 定稿**：与 scene 同链 `+0x18C`；4/5/3 映射；memory+session |
| 2026-08-05 | **scene_name 定稿**：yaml 静态链 + `memory.get_scene_name` + session；多场景/重启 PASS |
| 2026-08-05 | **`main` ← `Phase-BC` 合并**：BC 骨架 + hook/dataset/collect 评审修复 |
| 2026-08-05 | BC 骨架：policy train/save；None 帧 skip；`models/` gitignore；等 B 真数据 |
| 2026-08-04 | **朝向静态链定稿**：yaml `player_facing`；重启后与 x/y 同验 PASS |
| 2026-08-04 | L3 BC 开工：BC.0/1；tab；schema 1.1.1 前缀名；jsonlines |
| 2026-08-03 | B x/y+vision 冒烟；坐标接线；vision 合入 |
| 2026-08-01 | B 事件 smoke；Phase 1.2；soul `+0x1D4` |
| 2026-07-31 | 观测源/schema/`is_battle` 定稿 |
| 2026-07-29 | Phase 0 收官 10/10 |
