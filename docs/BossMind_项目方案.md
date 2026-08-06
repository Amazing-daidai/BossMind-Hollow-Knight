# BossMind 项目方案（详细版）

> 版本：2026-08-06  
> 与 `AGENTS.md` 对齐；本文展开细节与未落地模块，供理解与评审。  
> 场景：空洞骑士 · 神居 Pantheon；MVP Boss：Hornet Protector（`GG_Hornet_1`）。

---

## 目录

1. [项目定位与双目标](#1-项目定位与双目标)  
2. [问题定义与约束](#2-问题定义与约束)  
3. [总体架构](#3-总体架构)  
4. [已完成部分（P0～现状）](#4-已完成部分p0现状)  
5. [数据与 Schema](#5-数据与-schema)  
6. [P1：BC 闭环与评估（进行中）](#6-p1bc-闭环与评估进行中)  
7. [P2：Mod 观测层与快重置（已立项，未做）](#7-p2mod-观测层与快重置已立项未做)  
8. [P3：强化学习 RL（未做）](#8-p3强化学习-rl未做)  
9. [P4：LLM 与 Agent（未做）](#9-p4llm-与-agent未做)  
10. [P5–P6：一门与五门](#10-p5p6一门与五门)  
11. [多敌人表示：enemies + mask](#11-多敌人表示enemies--mask)  
12. [工程、双机与工具链](#12-工程双机与工具链)  
13. [风险、验收与求职交付](#13-风险验收与求职交付)  
14. [名词表](#14-名词表)

---

## 1. 项目定位与双目标

### 1.1 一句话

在 **可复现的实时游戏环境** 中，构建「观测 → 模仿学习 →（强化学习微调）→ 慢回路 LLM/Agent 复盘与编排」的完整闭环，短期形成可演示的工程作品，长期冲击神居五门速通。

### 1.2 目标分层

| 层次 | 导向 | 内容 | 成功标准 |
|------|------|------|----------|
| **短期** | 求职 | 闭环可演示：观测、BC、评估指标、（至少）复盘 Agent | Demo 视频 + 架构图 + 指标表；**不要求**必通五门 |
| **中期** | 过渡 | 速通神居 **某一门** | 该门稳定通关率 / 时长 |
| **终极** | 结果 | 速通 **五门** | 成绩；不设求职时间盒 |

技术主线服务两条线；**时间盒**拆开冲突：约 8 周内求职交付与通关率解耦。

### 1.3 技术路线一句话

```text
快回路：状态(60Hz) → BC/RL 策略(约 10Hz 决策可调) → 按键注入
慢回路：阶段边界 Option + 局后复盘 Agent + 实验编排
观测：P1 内存(CE) → P2 起 Mod 广播为主、内存对照
```

---

## 2. 问题定义与约束

### 2.1 控制问题

- **状态**：玩家/敌人/场景/游戏状态等（内存或 Mod）。  
- **动作**：键盘逻辑键多标签（left/right/jump/attack/…），当前 12 维含 `tab`。  
- **频率**：游戏与采集标称 60fps/60Hz；截图旁路 10Hz。  
- **回合结构**：一局 Boss 战；胜负由 `is_battle` 与 hp 等派生。

### 2.2 硬约束

| 约束 | 含义 |
|------|------|
| 采评同源 | 训练观测与评估观测同一 backend 接口；meta 记 `backend_id` |
| 不装 Mod 作「唯一真相」之前 | P1 仍可用 CE 内存把 Hornet 跑通 |
| LLM 不进快回路 | 禁止 LLM 逐帧出键 |
| CNN 不做主输入（本阶段） | 图用于复盘/可视化 |
| 挖链红线 | 单点 CE &gt;6h 无果 → 转方案或 `pipeline_only` |

### 2.3 现实难点（已验证）

- Boss **静态指针链不可跨 Boss 复用**。  
- 菜单读档重置约数十秒 → **在线 RL 吞吐不足**，必须 Mod SL。  
- 缺 **相对位置** 时，BC 易退化成「无空间意识的条件反射」。  
- `load_batch` 仅 `win` → 对 BC 合理，对 RL **丢失败数据**（P3 前必须改）。

---

## 3. 总体架构

### 3.1 逻辑分层

```text
┌──────────────────────────────────────────────────────────────┐
│ L4  慢回路：LLM Option / 复盘 Agent / 实验编排 / 局外训练师     │  P4+
├──────────────────────────────────────────────────────────────┤
│ L3  学习：BC Dataset/Policy → RL 微调 → Checkpoint            │  P1/P3
├──────────────────────────────────────────────────────────────┤
│ L2  采集与评估：collect_expert / BossEnv / eval               │  P0/P1
├──────────────────────────────────────────────────────────────┤
│ L1  环境工具：session / input / keyboard / vision / reset     │  P0
├──────────────────────────────────────────────────────────────┤
│ L0  观测后端：MemoryBackend(CE)  ∥  ModBackend(IPC)           │  P0/P2
└──────────────────────────────────────────────────────────────┘
         ↑ hollow_knight.exe (+ 可选 HK Mod)
```

### 3.2 运行时两条回路

**快回路（必须低延迟、可 60Hz 采样）**

```text
Backend.snapshot() → Observation
       → Featurizer → π_θ(a|s) 或 π_θ(a|s, option)
       → InputController 按键
```

**慢回路（秒～局级，可高延迟）**

```text
局中事件摘要 / 阶段切换
       → LLM 选 Option（或保持上一 option）
局后 jsonl + 截图 + 指标
       → 复盘 Agent → 诊断 JSON →（人工批准）改课程/奖励/下一实验
```

### 3.3 仓库映射（现状）

| 路径 | 职责 |
|------|------|
| `configs/game_info.yaml` | 键位、指针、vision ROI、boss 链 |
| `scripts/collect_expert.py` | 专家采集主循环 |
| `scripts/probe_*.py` | 探针验收 |
| `env_tools/memory,session,keyboard_hook,vision,input,reset_*` | L1 |
| `data/schema,writer` | 事件/meta/异步写图 |
| `learning/actions,dataset,policy` | BC 骨架 |
| `models/` | 权重（gitignore） |

**计划新增（未建）**：`BossEnv`、`eval.py`、`train_rl.py`、`ModBackend`、HK Mod 工程、Agent/LLM 包等。

---

## 4. 已完成部分（P0～现状）

### 4.1 采集与记拍

- 60Hz：`observation` + `key_states(held/pressed)` → `events.jsonl`。  
- 追帧、失焦、hp 读失败 streak、timeout、batch 前缀闸门。  
- 录帧前 `snapshot()` 清积压；倒计时；`_end_collect` 保证 writer close。

### 4.2 视觉

- `Vision`：客户区 ROI + DPI；10Hz；JPEG 异步队列写盘。  
- B 机实测 `capture_ms_p95`≈7–9ms（240Hz 屏）；暂不异步截图线程。  
- 图为硬需求：写盘失败 → `error`；丢帧超限 → `discard`。

### 4.3 内存观测（Hornet 可用）

| 字段 | 状态 |
|------|------|
| player hp/max_hp/soul/x/y | ✅ |
| facing | ✅（float 符号与常见 bool 相反，以实测为准） |
| scene_name / game_state | ✅ |
| boss_hp（仅 `GG_Hornet_1`） | ✅ |
| is_battle 派生 | ✅ |
| boss_x/y 等 | ❌ 未接（特征表可能仍占位 → None skip） |

### 4.4 BC 骨架（L3）

- `ACTION_KEY` 12 维；`obs_to_vec` / `key_to_vec`。  
- `load_episode` / `load_batch`（默认 win）；含 **None 的帧跳过**（不填 0 污染）。  
- `FrameDataset` + DataLoader；`BCPolicy`：MLP + BCEWithLogits + 保存 `MODEL_DIR`。  
- **未完成**：真数据过拟合验收、在线推理闭环、`eval`、相对位置特征。

### 4.5 键盘

- `logic_key in _state` 白名单；`is_running` 跟 listener；yaml 可有 inventory 但不进动作状态。

---

## 5. 数据与 Schema

### 5.1 一局目录

```text
data/raw/<batch>/<eps_id>/
  meta.json       # end_reason, schema_version, provenance, backend_id(计划)
  events.jsonl    # 60Hz
  frames/*.jpg    # ~10Hz
```

### 5.2 当前 schema 要点（1.1.1）

- 字段前缀：`player_hp` / `boss_hp` 等；与 20260803 旧 smoke 不兼容。  
- `is_battle` 语义：`PLAYING ∧ scene∈boss_info ∧ boss_hp>0`。  
- 计划 2.x：`enemies[]` + `mask` +（可选）`phase`；loader **强制 major 校验**。

### 5.3 过滤策略（现状 vs 计划）

| 用途 | 现状 | 计划 |
|------|------|------|
| BC | 局级 win + 帧级无 None | + 可选失焦/`read_error`；特征收窄 |
| RL | 未做 | **含 death/timeout**；在线时失焦暂停 |
| 评估 | 未自动化 | 固定 N 局协议，meta 记 reset/backend |

---

## 6. P1：BC 闭环与评估（进行中）

### 6.1 目标

不是「必须打赢 Hornet」，而是：

1. 新 schema 真数据可训；  
2. 单局过拟合证明通路；  
3. **无人工**连跑 N 局，产出 win_rate / 受伤 / 时长等 CSV。

### 6.2 待做明细

| 项 | 说明 |
|----|------|
| B 验收 `is_battle` | 走廊 / 房内 / 暂停 |
| 采集 | smoke/pipeline 或试开 expert |
| 特征 | 收窄 facing/boss 未接字段；**补 dx,dy 或 boss_x/y** |
| BC.3 | 单局过拟合 + 逐键指标（不只看 loss） |
| `BossEnv` | `reset/step`，包 `GameSession`+`Input`+backend |
| `eval.py` | 固定存档/护符/局数；写指标 |
| 推理延迟 | 测注入→画面延迟；必要时标签 shift |

### 6.3 BossEnv 草图

```text
obs = env.reset()          # 菜单或（后）Mod SL
loop:
  a = policy.act(obs)      # 0/1 向量或宏动作
  obs, r, done, info = env.step(a)
  # r 在 P1 可先占位；P3 再定义
```

### 6.4 求职叙事（P1 结束应能讲）

「60Hz 观测与专家模仿学习基线 + 可复现评估协议；指标从采集管线到自动 eval 打通。」

---

## 7. P2：Mod 观测层与快重置（已立项，未做）

### 7.1 为何立项

| 痛点 | Mod 解法 |
|------|----------|
| 每 Boss 挖静态链 | 场景内找 `HealthManager` |
| 多敌/召唤 | 枚举多个 HM → `enemies[]` |
| 菜单重置太慢 | DebugMod 式 SL，目标 &lt;3s |
| 与社区一致 | 对齐「血条 mod」的发现模型，但不把 Mod 当训练标签源以外的黑盒依赖——观测契约仍由我们定义 |

### 7.2 架构

```text
[hollow_knight + BossMind.Mod]
    Update/伤害回调：更新敌人列表缓存（避免每帧 FindObjects）
    写共享缓冲 / UDP 广播：{t, scene, player?, enemies:[{hp,max,x,y,id?}]}
                │
                ▼ IPC（本机，单向推送）
[Python ModBackend]
    读最新快照 → 填 Observation / enemies+mask
[MemoryBackend]
    对照测试、fallback
```

**延迟**：采用 **推送 + 读最新**，可满足 60Hz 采样；禁止 Python 每 tick 同步 RPC + 全场景 Find。Spike 需打点 p50/p95 间隙。

### 7.3 交付切分

| 步骤 | 内容 | 验收 |
|------|------|------|
| Spike ≤3 日 | C# 枚举 HM，IPC 打出 hp（+xy） | 未挖链房间也能看到血量 |
| ModBackend | 与 Memory 同接口；一致性测试 | 同局字段误差可解释 |
| Mod SL | `reset_backends/mod.py` 实现 | 重置 &lt;3s；meta 记录 |
| Schema 2.x | enemies+mask | loader 拒错 major |

### 7.4 风险与降级

- C#/API 学习成本 → spike 失败则记录原因，议降级（手挖 3 Boss + 离线 RL）。  
- 游戏版本破碎 → 锁定游戏版本与 mod 版本进 meta。

---

## 8. P3：强化学习 RL（未做）

### 8.1 定位（写死）

**BC 初始化上的微调**，不是从零 PPO 通关。  
前置：**P2 快重置** + `BossEnv` + 合理状态（含相对几何）+ 动作空间治理。

### 8.2 算法与技巧（方案级）

| 项 | 建议 |
|----|------|
| 算法 | PPO（或同类 on-policy）；对 BC 策略 **KL 正则** 或 **残差 RL**：`a = a_BC + Δ` |
| 决策频率 | frame-skip，约 6–10Hz 决策，降低 APM 与方差 |
| 动作 | 忌裸 2^12；宏动作（~20）或强 BC 先验的因子化 Bernoulli |
| 奖励 | 主：`Δboss_hp`；重罚：`Δplayer_hp`；小时间惩罚；终局 win 大奖；查 reward hacking（蹲角落磨血等） |
| 数据 | 训练用 **win+death+timeout**；评估协议固定 |
| 离线 RL | IQL/CQL 等作对照/保底；仅 win 数据时收益≈BC |

### 8.3 样本账（量级）

Hornet ~40s/局 + 3s 重置 → 约 80 局/小时量级 → 适合 **微调**，不适合从零堆百万步「无先验」通关。

### 8.4 工程交付物（未建）

- `train_rl.py`：配置、seed、日志、曲线。  
- Checkpoint 元信息：BC 来源、特征版本、schema、backend、reset 后端。  
- 止损：例如 48h 无提升则停，交付 BC vs 离线/失败对照表。

### 8.5 求职怎么讲

讲约束下的决策：重置成本、动作空间、时序对齐、reward hacking，而不是「我用了 PPO」。

---

## 9. P4：LLM 与 Agent（未做）

### 9.1 原则

| 做 | 不做 |
|----|------|
| 慢回路：复盘、编排、阶段 Option | 60Hz 出键、LLM 直接输出长按键序列 |
| 结构化输出 + 评测集 | 只调 prompt 无 eval |
| Tool-calling 包已有脚本 | Agent 无审批直接改生产配置 |

### 9.2 三个切片（建议优先序）

**(A) 战斗复盘 Agent（性价比最高，可先于「能打赢」）**

- **输入**：一局 `events.jsonl` + 关键帧截图 + 派生指标（死亡时刻、DPS 段、受击与 boss 行为邻近性等）。  
- **输出**：JSON：失败类型、证据帧、建议（多采哪类局 / 改奖励项 / 禁模仿片段）。  
- **评测**：人工标 ~20 局失败原因，报诊断准确率。  
- **现有资产**：10Hz 截图旁路终于有「主消费方」。

**(B) 实验编排 Agent**

- 自然语言 → 调用 `eval` / 对比两个 checkpoint → 出 markdown 报告。  
- 实现：function calling + 固定工具白名单。

**(C) LLM Option 选择器（亮点，靠后）**

- 在阶段切换/间隙调用；选项集小（如 8～16：猛攻/保守回血/诱冲刺…）。  
- 底层：`π(a|s, option)`；超时（如 200–800ms）则保持上一 option，**绝不阻塞快回路**。  
- Option 标签：采集时快捷键打标（已有 hook 经验）比事后猜更靠谱。  
- **依赖**：底层策略已有一定强度，否则切哪个 option 都输——可与 P3 并行开发 A/B，C 后接。

### 9.3 「局外训练师」

- 角色：定课程（下一练哪房）、禁招、奖励偏好。  
- 实现：可先人工 checklist；再换成 LLM 提案 + 人工批准。  
- 与五门长期进度强相关，但求职 demo 用 A+B 足够。

### 9.4 与五门的关系

| 五门痛点 | Agent/LLM 作用 |
|----------|----------------|
| 门间资源/路线 | 局外课程与休息决策 |
| 多阶段 | Option：躲阶段 / 输出阶段 |
| 多目标/召唤 | Option：集火谁 / 清小怪 |
| 数据质量 | 复盘 → 过滤毒片段 |

---

## 10. P5–P6：一门与五门

### 10.1 P5 一门 Pantheon

- 能力门禁：`enemies[]+mask`、多 Boss 条件（embedding/分头）、Mod 观测稳定、快重置。  
- 课程：先手工排 Boss 顺序，再考虑自动课程。  
- 评估：可先「单 Boss 串行评分」，再「整门连战」。

### 10.2 P6 五门

- 结果导向；不设求职期限。  
- **不做**五门全静态挖链；以 Mod 枚举 + 每门课程/条件策略为主。  
- 可选：更强视觉分支、并行采样等 —— 均后置。

---

## 11. 多敌人表示：enemies + mask

### 11.1 动机

单槽 `boss_*` 无法表达三螳螂、收藏家召唤、多阶段换对象。

### 11.2 方案

```text
enemies[i] = { kind?, hp, max_hp, x, y, phase?, ... }
mask[i]    = 0/1
N 固定（如 4～8）；Hornet 阶段 N=1 兼容
```

- **槽对齐**：固定角色 id / 稳定排序 / 帧间最近邻追踪；主目标可固定槽 0。  
- **网络**：mask 乘特征或 attention mask；集合编码（DeepSet 等）抗排序噪声。  
- **结束规则**：按 Boss 类型定义（全灭 vs 本体死亡 vs 阶段）。  

落地随 P2 Schema 2.x；P1 可继续单槽。

---

## 12. 工程、双机与工具链

| 项 | 说明 |
|----|------|
| A 机 | `D:\BossMind`，CPU torch，写学习/Agent |
| B 机 | `E:\BossMind`，游戏、采数、CE、Mod 开发与 spike |
| 训练 | 正式大训预定 WSL+ROCm |
| Conda | `BossMind` Python 3.12 |
| 协作 | 师父模式；少临时脚本 |

---

## 13. 风险、验收与求职交付

### 13.1 风险 Top

1. 求职时间盒被挖链/调参吃掉 → 硬 deadline + demo 允许先输。  
2. Mod spike 不及预期 → 降级手挖少数 Boss + 离线 RL。  
3. RL 不收敛 → BC-init+KL+宏动作+止损对照表。  
4. 采集（人键）与注入（程序键）时序不一致 → 测延迟并写入 meta。  
5. 评估不可复现 → 锁存档/护符/版本/局数协议。

### 13.2 求职交付清单（建议 T+8 周）

- [ ] README 架构图（快/慢回路）  
- [ ] 5～10 分钟 Demo 视频  
- [ ] 指标表：BC baseline（及若有 RL）  
- [ ] 复盘 Agent 至少能跑通结构化输出 + 小评测集  
- [ ] 局限与五门规划一页纸  

### 13.3 当前下一步（执行序）

```text
并行：
  P1：B 采数 → 特征/过拟合 → BossEnv+eval
  P2：Mod spike（HM→IPC→hp）
然后：
  P2 全量 + 快重置 → P3 RL 微调
  交错：P4 复盘 Agent / 编排
中期：P5 一门 → 终极 P6 五门
```

---

## 14. 名词表

| 词 | 含义 |
|----|------|
| BC | Behavior Cloning，行为克隆 / 模仿学习 |
| RL | Reinforcement Learning；本文指 BC 上的在线微调为主 |
| Option | 高层离散模式，条件化底层策略 |
| Agent | 带工具调用的慢回路系统（复盘/编排），非每帧控制器 |
| ModBackend | 游戏内 Mod 经 IPC 提供观测 |
| MemoryBackend | 外部进程读内存（CE 链） |
| is_battle | 是否在有效 Boss 战中的派生布尔 |
| Pantheon / 五门 | 神居万神殿挑战结构 |

---

## 附录 A：与旧「Phase 1 冻结」对照

| 旧 | 新 |
|----|-----|
| Phase1 不做在线 RL | P3 做；依赖 P2 快重置 |
| Phase1 不做 LLM | P4 慢回路做；禁止快回路 |
| 观测仅内存、不用 Mod | P1 内存；**P2 起 Mod 为主（已立项）** |
| 目标单写速通/无伤 | 短求职 / 中一门 / 终五门 |

---

## 附录 B：文档维护

- 进度日报仍以 **`AGENTS.md` §2§3** 为准（短）。  
- 本文为 **方案详述**；重大路线变更时同步改两者，并在 `AGENTS.md` §5 记一笔。
