# Godot Codely — Agent 说明

`godot-codely` 是 dsh 客户端插件（bundle）：告诉 dsh 怎么挂 `mcp__godot__*` 工具源、并注入 Godot 专家团方法论。

## 组成

| 文件 | 作用 |
|---|---|
| `dsh-godot-mount.patch.yml` | dsh 补丁层：spawn 自研 `godot-mcp-server`（全局命令），挂成 `mcp__godot__*` |
| `SYSTEM_PROMPT.md` | 专家团 persona **源文档**（方法论 2.0 / 四轴 / 阶段门控 / 五人团路由 / 三道闸红线） |
| `presets/godot/` | 「Godot Codely」预设（复制到 `~/.dsh/.agent-presets/godot/` 启用，只覆盖 persona） |
| `QUICKSTART.md` | 端到端教程（构建 server / 挂 patch / 选预设 / 编辑器内嵌面板 / 离线方案 / 已知边界） |
| `README.md` | 组件速览 |

## 同步纪律

- **源文档 vs 预设**：`SYSTEM_PROMPT.md` 是 persona 源文档；`presets/godot/agent.cordis.yml` 与 `agent-presets/godot-codely/` 是装载形态。改专家团知识（方法论/纪律/工具指引）要**三处同步**，避免漂移：
  1. `SYSTEM_PROMPT.md`（源）
  2. `presets/godot/agent.cordis.yml`（bundle 精简版）
  3. `agent-presets/godot-codely/agent.cordis.yml`（团队完整版，在主仓 `../agent-presets/`）
- **patch 改法**：`dsh-godot-mount.patch.yml` 的新增行必须用 `- insert:` 包裹（否则 dsh 报 `entry not found` 静默不挂）；env 的 `GODOT_PROJECT_PATH` / `GODOT_PATH` 每台机器必改。
- **分享边界**：纪律条款随仓；方法论数据（本机台账/私有工程沉淀）**不随仓**。见主仓 `AGENTS.md §6.7`。
