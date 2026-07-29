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
| 阶段 | **Phase 0 — 真环境探针** |
| 子课 | **第 4 课 B 机验收（今晚）** |
| 完成 | L1–L3 B✅；**L4 A 代码就绪**（审阅通过） |
| 阻塞 | 菜单 delay / 神居寻路事件需 B 机对着实机调；`Mod` 仍为占位 |
| 更新 | 2026-07-29 |

**Phase 0 清单**

- [x] L1 `probe_attach`（B）
- [x] L2 `probe_hp`（B）
- [x] L3 `probe_input`（B）
- [x] L4 A：`session.py` + `reset_backends/menu.py` + `probe_loop.py` + yaml `menu`
- [ ] L4 B：`probe_loop` ×10 + `results/phase0.md` ← **当前**
- [ ] WSL/ROCm（Phase 1 前，可后置）

---

## 3. 下一步（设备 B · 今晚）

### 前置

```text
git pull
cd /d E:\BossMind
conda activate BossMind
pip install -e .
```

- 游戏：**窗口化 / 无边框**；关自动更新  
- 存档：能「继续」进到与 yaml 寻路匹配的起点（当前配置名 `godhome_boss_room.hornet`）  
- 键位与 `game_info.yaml` → `keybinds` 一致（确认键目前用 `jump`=space）

### 跑验收

```text
python scripts\probe_loop.py
# 5 秒内点到游戏窗口
# 期望：×10 菜单读档 + goto；每次 HP 与基线一致；无 traceback
```

流程（代码已实现）：

```text
load_save → attach → goto(hornet) → 记 baseline HP
×10: reset(menu) → attach → goto → 对比 HP
finally: detach
```

### 调参（卡了再改 yaml，少改代码）

| 现象 | 改哪里 |
|------|--------|
| 退不出游戏 / 选错菜单 | `menu.quit_to_title.event` 的键与 delay |
| 标题「继续」失败 | `menu.load_save.event` |
| 走到错误位置 | `menu.godhome_boss_room.hornet.event` |
| 读档后 HP 失败 | 确认 `attach` 在 reset 后执行（脚本已有）；偏移见 L2 |

### 验收通过后

1. 写 `results/phase0.md`（日期、窗口模式、平均耗时、10 次是否全 match）  
2. 更新本文件 §2（L4 B✅）+ §5 里程碑  
3. `commit` + `push` → Phase 0 收官，下轮 Phase 1  

### Phase 1 备忘（现在不写）

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
results/phase0.md                           # ☐ B 验收后写
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
| 2026-07-29 | **L4 A 就绪**：session + Menu 读档 + probe_loop；待 B 验收 |
| 2026-07-28 | 进度同步：L1–L3 B 验收完成 |
| 2026-07-27 | L3 B 验收；AGENTS.md 精简；双轨重置架构定稿 |
| 2026-07-23 | L2 B 验收 |
| 2026-07-21 | L1 B 验收；B 环境就绪 |
