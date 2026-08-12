# BossMind — Agent 交接

> 换机先读 **§1～§3**。更深设计见 `docs/BossMind_项目方案.md`。  
> 每轮：改 §2/§3 → 里程碑 §5 → commit/push。  
> 协作：**Python / 业务 C# 学员自写**；Agent 给计划与审阅；明确「请代写」才代写。

---

## 1. 约定

### 1.1 目标

| 层次 | 导向 | 内容 | 验收 |
|------|------|------|------|
| 短期 | 求职 | 观测→BC→执行→评估→（后）复盘 Agent | demo+架构图+指标；**不绑通关率** |
| 中期 | 过渡 | 速通神居某一门 | 通关率/时长 |
| 终极 | 结果 | 速通五门 | 成绩 |

红线：单点 CE 挖链 **>6h 无果** → Mod / `pipeline_only`。

### 1.2 技术主线

```text
快回路：Observation → BC /（后）RL → 按键
慢回路：LLM Option + 复盘 Agent + 编排
观测：Mod UDP 推送为主（P2）；CE 可作 hybrid/对照（yaml 内存链曾大幅精简，恢复前 memory 路径不可用）
```

- **BC**：held 12 维；None skip。多敌：`enemies[] + mask`（`MAX_ENEMIES=8`，Step C 未做完）。  
- **Mod**：HM 缓存 + UDP；Python `ModIpc.read_latest()`；Find 禁每帧。  
- **Schema**：已升 **`2.0.0`**（破坏性；旧 1.1.x / `boss_*` 事件不兼容）。

### 1.3 阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| P0 | 采集/视觉/Hornet CE/BC 骨架 | ≈完成（CE 配置现被精简，见 §2） |
| P1 | 真数据 BC / BossEnv | 可并行，依赖观测稳定 |
| **P2** | Mod + schema2 + Session/BC 接线 | **进行中（A 机开发；B 未验收）** |
| P3+ | RL / Agent / 一门 | 等 2.4 SL 等 |

### 1.4 观测契约（2.0 冻结）

**Observation（无 `max_hp` / 无 `boss` 对象）：**

| 块 | 字段 |
|----|------|
| player | `player_hp, player_x, player_y, soul, player_facing_right` |
| enemies[] | `enemy_hp, enemy_x, enemy_y, enemy_facing_right, name` |
| 顶层 | `n_enemies, window_focused, is_battle, scene_name, game_state` |

**UDP JSON（Mod → Python，当前实现）：**

```text
t, scene, gamestate(int),
player: {hp, soul, x, y, facing},
enemies: [{hp, x, y, name, facing}, ...]
```

映射：`obs_map.ObservationMapper`；短键 → schema 长键。

**`is_battle`（已定，待你在 obs_map 落地）：**

```text
PLAYING ∧ scene ∈ 配置的 boss 场景表
∧ primary 主敌（名字子串匹配）的 hp > 0
```

- **不要** `any(enemies.hp>0)`（杀完 Boss 小怪还在会误判仍在战）。  
- yaml 为每场景配置 `primary_name_substr`（如 Hornet → `["Hornet"]`）；从 `enemies` 里 name 命中者取主敌（多个则 hp 最大）。  
- `gamestate` 用 Mod 已推的 int → 映射 PLAYING/PAUSED/CUTSCENE。

**采样**：事件目标 60Hz；图 10Hz。Mod 发送仍约 **1Hz**（双频率 Find/Send 未拆）。

### 1.5 协作 / 双机

| 项 | 值 |
|----|-----|
| A | `D:\BossMind` 开发 |
| B | `E:\BossMind` 游戏/编译 Mod/真机 |
| conda | `BossMind` 3.12 |
| UDP | `127.0.0.1:28765`（`configs` `client`） |

---

## 2. 当前状态（2026-08-12）

| 字段 | 值 |
|------|-----|
| 进度 | Schema 2.0 + Mod UDP + ModIpc + obs_map 草稿；Session/BC/yaml 未对齐 |
| 已齐 | 见下方「今日改动」 |
| 缺口 | obs_map 写完 is_battle（名字匹配）；补 boss 场景配置；修 session/actions；C# 敌 facing；双频率；B 验收 |
| Git | `main`（大量未提交） |

### 今日改动摘要（审阅）

| 模块 | 状态 | 备注 |
|------|------|------|
| [`schema.py`](src/bossmind/data/schema.py) | OK | 2.0.0；`enemies`；无 max_hp；去掉 `read_error_streak` |
| [`mod_ipc.py`](src/bossmind/env_tools/mod_ipc.py) | OK | 线程收包 + `read_latest`；假包测通过 |
| [`probe_mod_udp.py`](scripts/probe_mod_udp.py) | OK | 用 ModIpc |
| [`BossMindMod.cs`](mods/BossMind.Mod/BossMindMod.cs) | 可用草稿 | JsonUtility；含 `gamestate`；**仍 1Hz**；`hm.cState` **会编不过**（HM 无 cState） |
| [`obs_map.py`](src/bossmind/env_tools/obs_map.py) | **未完成** | `is_battle` 未赋值；`_is_battle` 仍按 boss_hp；`__main__` 调用方式错；facing 假设 float±1，Mod 可能是 bool |
| [`session.py`](src/bossmind/env_tools/session.py) | **坏** | 仍 `boss=` / `EnemyStates(boss_hp=)`；已挂 `ModIpc` 未用 |
| [`actions.py`](src/bossmind/learning/actions.py) | **坏** | list 当单对象；`boss_facing_right` 键名错 |
| [`game_info.yaml`](configs/game_info.yaml) | **大精简** | 去掉 `process_name` / 内存链 / `boss_info` 等；[`config.py`](src/bossmind/config.py) 已同步变瘦 → **CE `PlayerInfo` 暂不可用** |
| 内存 CE | 阻断 | 需要么恢复 yaml 内存段，要么 session 纯走 Mod |

### C# / 映射待对齐

- 玩家 `facing`：Mod 写的是 `cState.facingRight`（bool）赋给 float 字段；Python `_facing_to_right` 按 ±1.0 解。应统一：**bool → `facing_right`**，或 float ±1 与 CE 一致。  
- 敌人 facing：不要用 `hm.cState`；可先不发或 `localScale.x`。  
- `n` 字段：DTO 已无单独 `n`，用 `len(enemies)` 即可（schema `n_enemies`）。

---

## 3. 下一步（你改，我审）

| 顺序 | 内容 |
|------|------|
| **B′** | 补配置：`boss_scenes` / `primary_name_substr`（可放回精简版 `boss_info`）；完成 `obs_map`：`is_battle` 名字匹配 + `.get` 容错 + 修 `__main__` |
| **B″** | `session`：Mod 路径 `ipc.read_latest` → mapper；删 `boss`；memory 仅在恢复 CE yaml 后 |
| **C** | `obs_to_vec`：`MAX_ENEMIES=8`，dx/dy + mask |
| **D** | C#：Fix 敌 facing；Find 0.5s / Send 60Hz |
| **E** | collect 接 Mod；meta `backend_id` |
| **B 机** | 编译加载 + probe 真包（可后置） |

### 本阶段不做

五门挖链；CNN 主输入；LLM 出键；无快重置上 RL；Agent 擅自代写 Python。

---

## 4. 备忘

```text
Mod UDP: 127.0.0.1:28765
Schema: 2.0.0
is_battle: PLAYING ∧ scene∈表 ∧ primary(name匹配).hp>0
CE（若恢复）: Hornet boss_hp 链见历史；game_state 4/5/3
```

```text
mods/BossMind.Mod/   mods/README.md
src/bossmind/env_tools/{mod_ipc,obs_map,session,memory}.py
configs/game_info.yaml
```

---

## 5. 里程碑

| 日期 | 事件 |
|------|------|
| 2026-08-12 | Schema 2.0；Mod UDP+JsonUtility；ModIpc/probe；obs_map 进行中；is_battle 改为名字匹配主敌；yaml CE 段精简需决策恢复与否 |
| 2026-08-07 | P2 脚手架；Python 自写 / C# 先试 |
| 2026-08-06 | P2 立项；P0–P6 |
| 更早 | `git log` |
