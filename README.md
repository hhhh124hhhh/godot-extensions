# Godot MCP Stack — Godot 游戏开发专家团工作台

把 **Godot 游戏开发工作室专家团**（方法论 2.0 + 四轴上架迭代 + 阶段门控 + 五人团路由）能力接入 dsh 的完整可分发单元。

```
dsh web (3080) ──stdio──► godot-mcp-server（自研，23 工具）
                              │  直接文本化读写 .tscn/.gd + 按需调用 Godot 4.7.1 二进制
                              ▼
                        你的 Godot 工程
```

## 组件

| 组件 | 说明 |
|---|---|
| **godot-codely/** | dsh 客户端插件：`dsh-godot-mount.patch.yml`（挂载 `mcp__godot__*`）+ `SYSTEM_PROMPT.md`（专家团 persona 源文档）+ `presets/godot`（Godot Codely 预设）+ 可选的 `godot-codely-addon/`（Godot 编辑器内嵌 dsh web 面板）+ `install.ps1`（addon 安装器）+ CEF 补丁与构建笔记 |
| **godot-mcp-server/** | 自研 Godot MCP 主权聚合器：better-godot-mcp 17 复合工具主干 + coding-solo 4 独有 + Volcengine 文生图 2。单一 Server / 无前缀 / 离线可用 |
| **agent-presets/** | 专家团预设 7 个：`Godot Game Studio` 队长 + 架构/玩法/世界/界面/质量 5 角色 + `Godot Codely` 工程助手 |
| **install-godot-stack.mjs** | 一键幂等安装器（dsh 插件 + MCP server 构建/link + 专家团预设 + AgentTeams） |

## 快速开始

```bash
# 1. 一键安装（幂等，可重复跑）
node install-godot-stack.mjs

# 2. 改 dsh-godot-mount.patch.yml 的 env（每机不同）：GODOT_PROJECT_PATH / GODOT_PATH

# 3. 起 dsh 挂工具源
dsh --profile web --patch <本目录>/godot-codely/dsh-godot-mount.patch.yml

# 4. 3080 新会话选「Godot Game Studio」（拉团队）或「Godot Codely」（单 agent 改工程）
```

完整步骤见 [AGENTS.md](./AGENTS.md)（安装指南 + 排错）与 [godot-codely/QUICKSTART.md](./godot-codely/QUICKSTART.md)（端到端 + 编辑器内嵌面板）。

## 专家团（AgentTeams 角色）

| 角色 | 成员 | 职责 |
|---|---|---|
| architect | 梁栋 | 场景树 / 信号解耦 / Resource / GDScript·C# 类型安全 |
| systems-engineer | 动枢 | 物理 / 角色移动手感 / 动画 / 音频 / 多人 |
| world-designer | 境拓 | TileMap / 程序化关卡 / 地形 / 着色器 |
| ui-engineer | 屏绘 | Control 布局 / 无窗几何断言 / 商业化 UI |
| qa-release | 验舟 | 三道闸（编译/冒烟/功能自测）+ 导出 |

## 方法论基线（纪律随仓）

- **方法论 2.0**：不灰盒，第一版就是「能玩的核心循环游戏」（占位美术 + 合成音效 + 手感三件套）。
- **四轴上架迭代**（体验/产品/商业/技术）：从 t=0 按「能不能上架、能不能卖」倒推。
- **阶段门控**：Phase 0 脚手架 → Phase 1 核心循环 → Phase 2 内容质感 → Phase 3 三道闸发布。
- **三道闸**：`godot-verify`（编译，--boot-scene 全量 load）→ `godot-runtime-smoke`（headless 冒烟）→ `godot-functional-playtest`（功能自测）。

## 分享边界

机制壳 + 纪律条款随仓；方法论数据（本机台账/私有沉淀）不随仓——见 [AGENTS.md §6.7](./AGENTS.md)。

## License

MIT（godot-mcp-server 内含 Apache-2.0 成分，见其 LICENSE/NOTICE）。
