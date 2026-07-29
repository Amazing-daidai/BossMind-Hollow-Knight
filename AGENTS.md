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
| 评估场景 | Hall of Gods；MVP：**Pantheon 1 + Attuned** |
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
| 阶段 | **Phase 0 收官** → 下轮 **Phase 1** |
| 子课 | L4 B 验收完成 |
| 完成 | L1–L4 **B 机全部验收通过** |
| 阻塞 | 无；Phase 1 前可后置 WSL/ROCm |
| 更新 | 2026-07-29 |

**Phase 0 清单**

- [x] L1 `probe_attach`（B）
- [x] L2 `probe_hp`（B）
- [x] L3 `probe_input`（B）
- [x] L4 B：`probe_loop` ×10 + `results/phase0.md`（2026-07-29，10/10 HP match）
- [ ] WSL/ROCm（Phase 1 前，可后置）

---

## 3. 下一步（Phase 1 准备）

Phase 0 **已收官**（见 `results/phase0.md`）。

| 优先级 | 任务 |
|--------|------|
| 1 | B 机：`git pull` / `commit` + `push` 本轮回档 |
| 2 | Phase 1：DebugMod + `ModResetBackend`；专家轨迹采集协议 |
| 3 | B 机：WSL2 + ROCm 冒烟（训练前） |

### Phase 0 验收摘要（勿删）

```text
python scripts\probe_loop.py  →  10/10 HP match（2026-07-29，B 机）
```

### Phase 1 备忘

- DebugMod → `Mod.reset_game`；采集用 mod，评估强制 menu  
- 训练：Windows 采集 → WSL `~/bossmind-train/` ext4（勿每 epoch 扫 `/mnt/e`）

---

## 4. 仓库（L4 现状）

```text
configs/game_info.yaml
  # process_name, player_info, keybinds
  # menu.quit_to_title / load_save / godhome_boss_room.hornet
scripts/probe_{attach,hp,input,loop}.py     # ✅
src/bossmind/env_tools/
  memory.py  input.py  session.py           # ✅
  reset_backends/menu.py                    # ✅ 菜单读档
  reset_backends/mod.py                     # ☐ 空壳，Phase 1
results/phase0.md                           # ✅ B 验收报告
```

安装：`pip install -e .` · 配置经 `paths.GAME_INFO_FILE`

**API 摘要**

| 类/脚本 | 作用 |
|---------|------|
| `PlayerInfo` | attach / 读 HP / detach |
| `InputController` | tap / press / hold / `run_action` |
| `Menu` | `quit_to_title` / `load_save` / `goto_boss_room` / `reset_game` |
| `GameSession` | 组装上三者；`reset_game("menu"|"mod")` |
| `probe_loop.py` | ×10 验收入口 |

---

## 5. 里程碑日志

| 日期 | 事件 |
|------|------|
| 2026-07-29 | **Phase 0 收官**：L4 B 验收 `probe_loop` 10/10 HP match；`results/phase0.md` |
| 2026-07-29 | L4 A 就绪：session + Menu 读档 + probe_loop |
| 2026-07-28 | 进度同步：L1–L3 B 验收完成 |
| 2026-07-27 | L3 B 验收；AGENTS.md 精简；双轨重置架构定稿 |
| 2026-07-23 | L2 B 验收 |
| 2026-07-21 | L1 B 验收；B 环境就绪 |
