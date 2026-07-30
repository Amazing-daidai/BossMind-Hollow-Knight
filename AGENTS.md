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
| 评估场景 | Hall of Gods；MVP：`godhome_boss_room.hornet` / Pantheon Attuned |
| 重置 | **评估/演示** = 菜单读档；**训练采数** = DebugMod SL（Phase 1 中段） |
| 不做（Phase 1） | CNN 主输入、LLM、在线 RL、评估用 mod |

### 协作铁律（Agent 必读 — 2026-07-30 重申）

| 规则 | 说明 |
|------|------|
| **师父模式** | 用户**自行实现**代码；Agent 只做：讲思路、给步骤、审代码、排错、定接口/验收 |
| **禁止代写** | **不要**主动写整模块/整脚本完工代码；Cursor Plan「Implement」**不能**覆盖本条 |
| **唯一例外** | 用户用明确措辞要求代写，例如：「请代写 xxx」「帮我把这个文件写完」 |
| **文档同步** | 可改 `AGENTS.md` / 进度；改业务代码须先征得同意或属于上述例外 |
| **讲解方式** | **自上而下**：新模块先讲概况/职责/接口；用户某块不懂再 **自下而上** 拆代码 |
| **推进节奏** | 用户先写 → 交 Agent 审 → 通过再进下一步；不跳步代写 |

> 失误记录（2026-07-30）：Plan 点了 Implement 后 Agent 代写了 Phase 1 采集骨架；已撤回。之后一律按师父模式。

**双设备**

| | A | B（7900 XT · 必须 Windows） |
|--|---|-------------------------------|
| 路径 | `D:\BossMind` | `E:\BossMind` |
| Python | conda `BossMind` **3.12.13** | 同左 |
| 写代码 | ✅ | ✅ |
| HK / 采数 / 评估 | ❌ | ✅ |
| GPU 训练 | ❌ | WSL2 + ROCm（待装） |

---

## 2. 当前状态（每轮必改）

| 字段 | 值 |
|------|-----|
| 阶段 | **Phase 1 — 专家 BC**（刚启动，讨论/定协议中） |
| 子课 | **1.1 采集协议**（尚未写代码） |
| 完成 | **Phase 0 全部 B 验收通过** |
| 阻塞 | 无；先对齐采集 schema / 动作来源 / 第一刀顺序 |
| 更新 | 2026-07-30 |

**Phase 0 清单（已关闭）**

- [x] L1–L4 B 验收；`probe_loop` **10/10 HP match**（2026-07-29）
- [x] `results/phase0.md`

**Phase 1 清单**

- [ ] 1.1 采集 schema + `collect_expert`（用户实现；Agent 指导）
- [ ] B 试采 2–3 局
- [ ] DebugMod + `Mod.reset_game`
- [ ] WSL/ROCm + 纯内存 BC + menu 轨 `eval_bc`

---

## 3. 下一步

### Phase 0 收官摘要

```text
python scripts\probe_loop.py  →  10/10 HP match（B，2026-07-29）
底座：session + Menu 菜单读档 + InputController + PlayerInfo(HP)
```

### Phase 1 目标（讨论用）

手打专家轨迹 → 纯内存 BC → **菜单轨**固定评估；Mod 只加速采数。

**建议默认（待用户确认后再开写）：**

1. 动作标签 = **键盘钩子**读真实按键（非只记脚本注入）  
2. 第一刀 = schema + 菜单 reset 采集；Mod / WSL 不挡开工  

**本轮 Agent 应做**：对齐字段与脚本职责 → 给实现步骤 → 等用户交代码再审。  
**本轮 Agent 不应做**：代写 `collect_expert` / dataset / train。

---

## 4. 仓库（Phase 0 末状态）

```text
configs/game_info.yaml
scripts/probe_{attach,hp,input,loop}.py
src/bossmind/env_tools/{memory,input,session}.py
src/bossmind/env_tools/reset_backends/{menu,mod}.py   # mod 仍空壳
results/phase0.md
```

---

## 5. 里程碑日志

| 日期 | 事件 |
|------|------|
| 2026-07-30 | **协作铁律重申**：师父模式优先于 Plan Implement；Phase 1 启动讨论（代写已撤回） |
| 2026-07-29 | **Phase 0 收官**：L4 B 10/10；`results/phase0.md` |
| 2026-07-28 | L1–L3 B 验收完成 |
| 2026-07-27 | L3 B；AGENTS 精简；双轨重置定稿 |
| 2026-07-23 | L2 B |
| 2026-07-21 | L1 B |
