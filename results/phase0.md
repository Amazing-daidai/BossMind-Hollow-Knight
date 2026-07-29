# Phase 0 验收报告

| 项 | 值 |
|----|-----|
| 日期 | 2026-07-29 |
| 设备 | B（`E:\BossMind`） |
| 环境 | conda `BossMind` · Python 3.12.13 |
| 游戏 | Hollow Knight · `hollow_knight.exe` |
| 窗口 | 窗口化 / 无边框（用户实机） |
| 存档 | 神居 Boss 房路线 `godhome_boss_room.hornet` |
| 验收脚本 | `python scripts\probe_loop.py` |

## 验收标准（AGENTS.md L4）

- [x] 菜单读档重置 ×10，无 traceback
- [x] 每次 reset 后 `goto_boss_room("hornet")` 成功
- [x] 每次 HP 与基线一致
- [x] `attach` / `detach` 正常结束

## 运行结果

**通过的一次完整运行**（终端记录，PID 33300）：

| 轮次 | HP | 与基线一致 |
|------|-----|------------|
| baseline | 9 | — |
| 1 | 9 | True |
| 2 | 9 | True |
| 3 | 9 | True |
| 4 | 9 | True |
| 5 | 9 | True |
| 6 | 9 | True |
| 7 | 9 | True |
| 8 | 9 | True |
| 9 | 9 | True |
| 10 | 9 | True |

**结论**：10/10 全部 match；脚本正常退出。

## 备注

- 此前有数次中断（`KeyboardInterrupt`）或仅完成部分轮次，不计入正式验收。
- 重置后端：`menu`（`Menu.reset_game`）；`mod` 仍为 Phase 1 占位。
- 配置：`configs/game_info.yaml` → `menu.quit_to_title` / `reload_save` / `godhome_boss_room.hornet`。

## Phase 0 结论

**通过。** 可进入 Phase 1（采集 / DebugMod 重置轨 / WSL 训练栈）。
