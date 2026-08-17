# Godot MCP Stack — 接收方安装指南 (QUICKSTART)

> 本仓库是 **Godot AI 工程助手** 的完整可分发单元：`godot-codely`（dsh 客户端插件）+ `godot-mcp-server`（自研 MCP 聚合器，23 工具）+ `agent-presets`（专家团预设）+ 安装器。
> 完整分工/排查见 `AGENTS.md`。本文只讲"拿到仓库 → 装好 → 能用"。

## 0. 前置

- Windows 10/11，已装 **Git** 与 **Node.js 18+**（推荐 20+）
- 一个 **Godot 4.x** 可执行文件（推荐 4.7.1；用于 run/export/launch 和 3 个 .gd 进程工具，纯文件解析类工具可不设）
- 你的 Godot 工程（可选，默认用 dsh 会话里 `config set project_path` 自选）
- 可选：火山方舟 API Key（用于 `generate_sprite` / `generate_image` 出图）

## 1. 克隆（私有仓，需被加成协作者）

```bash
git clone https://github.com/hhhh124hhhh/godot-extensions.git
cd godot-extensions
```

## 2. 安装服务器（一次）

```bash
cd godot-codely/godot-mcp-server
npm install
npm run build
npm link        # 装成全局命令 godot-mcp-server（软链到本仓库，改代码只需重新 npm run build）
```

> **npm link 被拦截（EDR/杀软）**：回退系统 npm 再试：
> ```bash
> "C:/Program Files/nodejs/npm.cmd" link
> ```

## 3. 配置你自己的机器参数（关键）

创建 `godot-codely/godot-mcp-server/godot-mcp-server.config.json`（**已被 gitignore，不会提交/泄漏**）：

```json
{
  "godotPath": "D:/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64.exe",
  "godotProjectPath": "D:/你的工程路径",
  "volcArkApiKey": "你的火山方舟Key（可选）"
}
```

> 不想写工程路径也行：dsh 会话里用 `config set project_path=<路径>` 运行时切换（零重启）。
> 出图 Key 也可放 `.env`（`VOLCENGINE_API_KEY=...`，已被 gitignore）或环境变量 `VOLC_ARK_API_KEY`。

## 4. 挂进 dsh

用 `godot-codely/dsh-godot-mount.patch.yml`（已指向全局命令 `godot-mcp-server`，**无机器路径**，可分享）：

```bash
cd D:/deepseek-harness
node --import tsx/esm apps/cli/src/bin.ts web --patch D:/path/to/godot-codely/dsh-godot-mount.patch.yml
```

patch 里 `env:` 的 `GODOT_PROJECT_PATH` / `GODOT_PATH` 可留空（服务器会读第 3 步的 config.json）。

## 5. 验证

1. 重启 dsh（**必须新开会话**——MCP 工具在会话初始化时挂载）
2. 新会话里让 AI 跑：
   - `mcp__godot__config detect_godot` → 应 `found: true` + 你的 Godot 版本
   - `mcp__godot__list_projects` → 列出你的工程
   - `mcp__godot__project` action=info → 读出工程信息
3. 工具表应有 **23 个** `mcp__godot__*` 工具（better 17 + coding-solo 4 + image-gen 2，无子前缀）

## 常见坑

| 症状 | 原因/解法 |
|---|---|
| `mcp__godot__*` 没出现 | MCP 在会话初始化挂载 → **新开会话**，不是刷新 UI |
| `config detect_godot` 报 not found | config.json 的 `godotPath` 没写或写错（工具实际用的是 config.json，不是 PATH） |
| `project info` 报 `Access denied: outside the project root` | 路径安全模型：`project_path` 必须在当前工程根内 → 先 `config set project_path` 切过去 |
| `npm link` 失败 | 回退系统 npm（见第 2 步） |
| 出图报"未找到 API Key" | 配 `volcArkApiKey` / `VOLCENGINE_API_KEY`，并确认默认端点是你账号的（他人需设 `VOLC_IMAGE_ENDPOINT`） |

## 其他

- **专家团预设**：`agent-presets/` 7 个预设，配合 AgentTeams 用（见 AGENTS.md）
- **Godot 编辑器内嵌 dsh 面板**（可选）：`godot-codely/godot-codely-addon/`，需额外装 godot-cef webview 扩展，见其 README
- **卸载/换机器**：重新 clone + 第 2、3 步即可；`npm link` 是软链，不占空间
