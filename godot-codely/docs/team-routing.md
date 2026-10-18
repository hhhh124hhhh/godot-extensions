# 五人团路由（Game Studio / 多 agent）

**单智能体 Godot Codely 不要「先五人团再动手」。** 默认直接实现当前最小一层（用户这一次点名的文件、节点或行为）。本文只在使用 **「Godot Game Studio」** 队长预设或 AgentTeams 时加载。

队长预设在 `agent-presets/godot-game-studio/`。角色预设在 `agent-presets/godot-architect/`、`godot-systems-engineer/`、`godot-world-designer/`、`godot-ui-engineer/`、`godot-qa-release/`。

## 角色

| 角色 | 预设 id | 负责 |
|---|---|---|
| 架构（梁栋） | `architect` | 场景树 / 信号解耦 / Resource / GDScript·C# 类型安全 |
| 玩法（动枢） | `systems-engineer` | 物理 / 角色移动手感 / 动画状态机 / 音频总线 / 多人 |
| 世界（境拓） | `world-designer` | TileMap / 程序化关卡 / 地形 / 着色器 |
| 界面（屏绘） | `ui-engineer` | Control 响应式布局 / 无窗几何断言 / 商业化 UI 基准 |
| 质量（验舟） | `qa-release` | 三道闸 + 导出（godot-verify / godot-runtime-smoke / godot-functional-playtest / godot-export） |

## 何时路由

用户明确要团队 / 工作室协作，或目标跨多个支柱且要用 AgentTeams 时，由队长编排，不由 Codely 单会话先输出路由再实现：

1. `agent_teams_create` 建队（调用者成为队长）。
2. `agent_teams_add_member` 按角色加人，一人一角色。
3. `agent_teams_create_task` 把目标拆成**有依赖**的任务。
4. 成员领任务、`send_message` 协调、`update_task` 汇报。
5. `agent_teams_status` 轮询；收尾 `agent_teams_delete` 归档。

任务跨多个支柱时，队长先按上表分派，再让成员实现当前最该下的那一层（通常是 Phase 1 的核心动词层，而不是最安全的 UI 层）。产品阶段与四轴见 [methodology-2.0.md](methodology-2.0.md)。

`agent_teams_*` 不可用时，队长退回原生 `subagent`，逐个委派角色预设，结果仍由队长汇总。一个队长同时只带一个活动团队。

## 质量角色与验证档

验舟负责三道闸和导出，但三道闸不是每个小改动的默认动作。分层验证见 [methodology-2.0.md](methodology-2.0.md)：

- 结构 / 编辑器编辑 → `scenes.info`（或等价轻检查）
- 行为必须引擎 → `project.run` 一次
- 宣称可上架 / Phase 3 完成 → 完整三道闸

小改动不要派质量角色去跑冒烟或功能自测。
