# BossMind — Agent 交接

> Git 同步代码；本文档同步进度。换设备先读 **§2 §3**，再动手。  
> 每轮结束：改 §2/§3 → 有里程碑写 §5 → `commit` + `push`。

### 文档说明（2026-07-27 精简）

本文档由 **~555 行 → ~100 行** 主动压缩，**未改项目约定**，只为省 Agent 上下文。

| 仍在这里 | 已移出（双方已确认，不必每次重读） |
|----------|-----------------------------------|
| §2 状态、§3 当前任务 | WSL/ROCm 逐步安装教程 |
| 双设备分工与路径 | CNN/数据对齐/八步训练流水线（Phase 2+ 再单开 doc） |
| 神居 + 双轨重置架构 | 已完成环境清单（conda、CE、probe_attach 等） |
| 仓库结构、里程碑 | 协作约定长表、阶段地图、ASCII 架构图 |

**找旧内容**：`git log -p -- AGENTS.md` 看精简前版本；Phase 1 环境细节以后可写 `docs/env-b.md`，需要时再引用。

---

## 1. 约定（已确认，勿重复讨论）

| 项 | 内容 |
|----|------|
| 目标 | 神居 Pantheon 单 Boss **速通/无伤**；BC + LLM Option + 局外训练师（弱融合） |
| 评估场景 | Hall of Gods；MVP：**Pantheon 1 + Attuned**（`game_info.yaml` → `godhome`） |
| 重置 | **评估/演示** = 菜单读档（无 mod）；**训练采数** = DebugMod SL（Phase 1） |
| 不做 | 大地图 Boss 主线、LLM 每帧按键、战斗内热更新权重 |
| 协作 | 用户自写代码；Agent 师父模式（思路/审代码/排错，不代写整模块） |

**双设备**

| | A | B（7900 XT · 必须 Windows） |
|--|---|-------------------------------|
| 路径 | `D:\BossMind` | `E:\BossMind` |
| Python | `…/conda/envs/BossMind/python.exe` **3.12.13** | 同左 |
| 写代码 | ✅ | ✅ |
| 跑 HK / 内存 / 按键 / 采集 / 评估 | ❌ | ✅ |
| GPU 训练 | ❌ | WSL2 + ROCm（Phase 1 再装） |

游戏相关验收**只在 B**。`data/`、`artifacts/` 留 B；大文件不进 Git。

---

## 2. 当前状态（每轮必改）

| 字段 | 值 |
|------|-----|
| 阶段 | **Phase 0 — 真环境探针** |
| 子课 | **第 4 课：session + probe_loop（菜单重置 ×10）** |
| 完成 | L1 B✅ · L2 B✅ · L3 B✅ · L4 进行中 |
| 阻塞 | 神居进度/DLC；菜单 `delays` 需 B 机调 |
| 更新 | 2026-07-27 |

**Phase 0 待办（B 机）**

- [x] `probe_hp` 验收（B，2026-07-23）
- [x] `probe_input` 验收（B，2026-07-27）
- [ ] `probe_loop` ×10 + `results/phase0.md`
- [ ] WSL/ROCm（Phase 1 前，可后置）

---

## 3. 下一步

### 第 4 课（当前）

**目标**：神居固定存档点 → `GameSession.reset()`（菜单轨）×10 → 每次打印时间戳 + HP。

```text
session.reset()
  ├── MenuResetBackend   # 现在实现；评估/演示只用这个
  └── ModResetBackend    # Phase 1；DebugMod 热键
```

| 设备 | 任务 |
|------|------|
| A | `session.py` + `reset_backends/menu.py` + `probe_loop.py`；yaml 加 `menu`、`godhome` |
| B | 神居门口存档 → 手操菜单路径 → 调 `menu.delays` → 验收 |

```text
python scripts\probe_loop.py
# 10 次无卡死；HP 一致；人眼同起点 → 写 results/phase0.md
```

### Phase 1 备忘（现在不写）

- DebugMod + BepInEx → `ModResetBackend`；采集 `--reset-backend mod`，评估强制 `menu`
- 训练数据：Windows 采集 → WSL `~/bossmind-train/` ext4 缓存（**勿**每 epoch 扫 `/mnt/e`）
- 发布：`artifacts/published/<run_id>/`；评估只读 published

---

## 4. 仓库

```text
configs/game_info.yaml      # process_name, player_info, keybinds, menu, godhome
scripts/probe_{attach,hp,input,loop}.py
src/bossmind/env_tools/{memory,input,session}.py
src/bossmind/env_tools/reset_backends/{base,menu,mod}.py
data/  artifacts/  results/
```

安装：`pip install -e .` · 偏移与键位进 YAML · 配置经 `paths.GAME_INFO_FILE`

---

## 5. 里程碑日志

| 日期 | 事件 |
|------|------|
| 2026-07-27 | L3 B 验收：`probe_input` 按键注入通过 |
| 2026-07-27 | **AGENTS.md 精简**（555→~100 行，见文首说明）；架构：神居+菜单评估 / Mod 训练加速；L3 A 就绪 |
| 2026-07-23 | L2 B 验收：`probe_hp`；A 就绪 `PlayerInfo` + `probe_hp` |
| 2026-07-21 | L1 B 验收；B 环境就绪 |
