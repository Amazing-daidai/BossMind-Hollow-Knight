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

- **BC**：held 12 维；None skip。多敌：`enemies[] + mask`（`MAX_ENEMIES=8`，vec 45 维已落地）。  
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

**`is_battle`（obs_map 已落地）：**

```text
PLAYING ∧ scene ∈ 配置的 boss 场景表
∧ primary 主敌（名字子串匹配）的 hp > 0
```

- **不要** `any(enemies.hp>0)`（杀完 Boss 小怪还在会误判仍在战）。  
- yaml 为每场景配置 `primary_name_substr`（如 Hornet → `["Hornet"]`）；从 `enemies` 里 name 命中者取主敌（多个则 hp 最大）。  
- `gamestate` 用 Mod 已推的 int → 映射 PLAYING/PAUSED/CUTSCENE。

**采样**：事件目标 60Hz；图 10Hz。Mod Send **90Hz**（Find 仍 0.5s；实际上限 ≈ HeroUpdate/帧率）。

### 1.5 协作 / 双机

| 项 | 值 |
|----|-----|
| A | `D:\BossMind` 开发 |
| B | `E:\BossMind` 游戏/编译 Mod/真机 |
| conda | `BossMind` 3.12 |
| UDP | `127.0.0.1:28765`（`configs` `client`） |

---

## 2. 当前状态（2026-08-21）

| 字段 | 值 |
|------|------|
| 进度 | Schema 2.0 + ModIpc + obs_map `is_battle` + session Mod 路径 + `obs_to_vec` 45 维 |
| 已齐 | B′ / B″ / C（含 `tests/test_actions.py`） |
| 缺口 | **E 收尾** meta `backend_id`；空包带 `window_focused`；**B 机**编 Mod + probe |
| Git | `main`（大量未提交） |

### 今日改动摘要（审阅）

| 模块 | 状态 | 备注 |
|------|------|------|
| [`schema.py`](src/bossmind/data/schema.py) | OK | 2.0.0；`enemies`；无 max_hp；去掉 `read_error_streak` |
| [`mod_ipc.py`](src/bossmind/env_tools/mod_ipc.py) | OK | 线程收包 + `read_latest` |
| [`obs_map.py`](src/bossmind/env_tools/obs_map.py) | OK | `is_battle` 名字匹配主敌；facing 仍按 yaml ±1 解 |
| [`session.py`](src/bossmind/env_tools/session.py) | OK | `ipc.read_latest` → mapper；无 `boss` |
| [`actions.py`](src/bossmind/learning/actions.py) | OK | 45 维；dx/dy + mask；空包全 0 |
| [`policy.py`](src/bossmind/learning/policy.py) | OK | `_input_dim = 5+8*4+8` |
| [`tests/test_actions.py`](tests/test_actions.py) | OK | 6 项：空包 / 相对坐标 / 排序 / 截断 |
| [`BossMindMod.cs`](mods/BossMind.Mod/BossMindMod.cs) | 已改待 B 编 | Find 0.5s / Send 90Hz；facing=`localScale.x`→±1 |
| [`collect_expert.py`](scripts/collect_expert.py) | 主路径 OK | 已去 `read_error_streak`；空 `player` 已判；**缺** close 时写 `backend_id` |
| [`tests/test_episode_writer_images.py`](tests/test_episode_writer_images.py) | OK | 假事件已改 schema 2.0 `enemies[]` |
| 内存 CE | 暂不用 | session 纯 Mod；yaml 无内存链 |

### C# / 映射待对齐（D）

- UDP 键仍叫 `facing`（float）。Python `_facing_to_right` 用 yaml：`right_value: -1.0` / `left_value: 1.0`（骑士朝右时 scale.x 为负）。
- **不要** 把 bool 赋给 float（true→1.0 会被解成朝左或 `None`）。
- 敌人：**禁止** `hm.cState`。用 `transform.localScale.x` 映射成 ±1。
- 玩家：`cState.facingRight` 可用，写成 `facingRight ? -1f : 1f`，或同样用 `localScale.x`。
- `n` 字段：DTO 已无单独 `n`，Python 用 `len(enemies)`。

---

## 3. 下一步（你改，我审）

| 顺序 | 内容 |
|------|------|
| B′ / B″ / C / D代码 | 已完成（D 待 B 机编译） |
| **E（当前）** | `MetaData.backend_id`；collect `close(..., backend_id="mod")`；空包 Observation 带上 `window_focused` |
| **B 机** | 编译加载 + `probe_mod_udp` 真包 |

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
| 2026-08-21 | `obs_to_vec` 45 维 + `tests/test_actions.py`；进入 D（C# 双频率 / facing） |
| 2026-08-12 | Schema 2.0；Mod UDP+JsonUtility；ModIpc/probe；obs_map 进行中；is_battle 改为名字匹配主敌；yaml CE 段精简需决策恢复与否 |
| 2026-08-07 | P2 脚手架；Python 自写 / C# 先试 |
| 2026-08-06 | P2 立项；P0–P6 |
| 更早 | `git log` |
