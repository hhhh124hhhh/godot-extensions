# Godot Codely — Agent 说明

`godot-codely` 是 dsh 客户端插件（bundle）：告诉 dsh 怎么挂 `mcp__godot__*` 工具源，并注入短 persona。长方法论在 `docs/`，按需再读。

## 组成

| 文件 | 作用 |
|---|---|
| `dsh-godot-mount.patch.yml` | dsh 补丁层：spawn 自研 `godot-mcp-server`（全局命令），挂成 `mcp__godot__*` |
| `SYSTEM_PROMPT.md` | 短 persona **源正文**（无 YAML）。与下面两处 `config.text` 必须逐字相同 |
| `docs/` | 长材料，按需加载：方法论 2.0、分层验证、Loop 示例、zfoo 表、五人团路由 |
| `presets/godot/` | 「Godot Codely」预设（复制到 `~/.dsh/.agent-presets/godot/` 启用，只覆盖 persona） |
| `QUICKSTART.md` | 端到端教程（构建 server / 挂 patch / 选预设 / 编辑器内嵌面板 / 离线方案 / 已知边界） |
| `README.md` | 组件速览 |

## 同步纪律

- **三处 persona 必须逐字相同**（热路径，给 DeepSeek-V4.1-Flash 的短系统提示）。改一句就要改齐这三处的正文，不要只改一处：
  1. `SYSTEM_PROMPT.md`（源正文，无 YAML）
  2. `presets/godot/agent.cordis.yml` 里 `@deepseek-ai/dsh-persona` 的 `config.text`
  3. `agent-presets/godot-codely/agent.cordis.yml` 里 `@deepseek-ai/dsh-persona` 的 `config.text`（主仓 `../agent-presets/`）
- **长材料不进热路径**：方法论 2.0、四轴、阶段门控、分层验证、Loop 示例、zfoo 表、五人团路由写在 `docs/`。单智能体 Codely 不要「先五人团再动手」；团队路由只在 `docs/team-routing.md`（给 Godot Game Studio / AgentTeams）。分层验证：结构编辑用 `scenes.info`；行为要引擎才 `project.run` 一次；宣称可上架 / Phase 3 完成才跑满三道闸。小改动不自动冒烟或功能自测。
- **patch 改法**：`dsh-godot-mount.patch.yml` 的新增行必须用 `- insert:` 包裹（否则 dsh 报 `entry not found` 静默不挂）；env 的 `GODOT_PROJECT_PATH` / `GODOT_PATH` 每台机器必改。
- **分享边界**：纪律条款随仓；方法论数据（本机台账/私有工程沉淀）**不随仓**。见主仓 `AGENTS.md §6.7`。
