# Godot Codely

Godot 版「团结 Codely」工作台插件：把 **Godot 游戏开发工作室专家团**（方法论 2.0 / 四轴 / 阶段门控 / 五人团）能力接入 dsh。

- **聊天入口**：dsh web（默认 `http://127.0.0.1:3080`），选「Godot Codely」预设自动注入专家团大脑。
- **工具源**：自研 **godot-mcp-server**（23 个工具，stdio 挂载，无前缀、离线可用）——见 `../godot-mcp-server/`。
- **编辑器内嵌（可选）**：`godot-codely-addon/` + godot-cef 把 dsh web 渲染进 Godot 4.7.1 编辑器右侧 Dock。

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)（4 步端到端）。核心：

```bash
# 1. 构建并全局链接 MCP server（一次性）
cd ../godot-mcp-server && npm install && npm run build && npm link

# 2. 起 dsh 挂 godot 工具（--patch 指向本文件旁的补丁）
dsh --profile web --patch <仓库路径>/godot-codely/dsh-godot-mount.patch.yml
```

## 文件

| 文件 | 作用 |
|---|---|
| `SYSTEM_PROMPT.md` | 专家团 persona 源文档（方法论 2.0 / 四轴 / 阶段门控 / 五人团路由 / 红线） |
| `dsh-godot-mount.patch.yml` | dsh 补丁层：把 godot-mcp-server 挂成 `mcp__godot__*` 工具源 |
| `QUICKSTART.md` | 端到端教程（含内嵌面板路 A / 离线方案 / 已知边界） |
| `godot-codely-addon/` | Godot 编辑器 Dock 面板插件（webview 内嵌 dsh web） |
| `install.ps1` | addon 安装器（per-project junction / 真全局两种模式） |
| `patches/` | godot-cef 编辑器内嵌必需的一行补丁（`0001-cef-texture-tool-class.patch`） |
| `BUILD-NOTES.md` | godot-cef 自编可复现笔记（官方 release dll 不可用） |
| `downloads/` | CEF 下载物（不入库，gitignore 排除） |
