# godot-mcp-server

Godot MCP **主权聚合器**（真·去重合并版）。

把两个第三方 Godot MCP 服务器去重合并成「我自己的」单一 MCP 端点：**单一 McpServer / 单一注册 / 无前缀 /
统一 SDK（`@modelcontextprotocol/sdk ^1.30.0`）**，并补上 cocos-mcp-bridge 同款的 Volcengine 文生图能力
与统一配置 / API Key 读取。剥离任何 phone-home / 遥测（两上游已核实无外呼）。

## 架构

```
对外：单一 MCP Server（stdio 默认 / MCP_TRANSPORT=http 单端点）
  │
  ├─ better-godot-mcp 17 复合工具（主干，纯文件解析 .tscn/.gd，~70 动作）
  │     project / scenes / nodes / scripts / editor / config / resources /
  │     input_map / signals / animation / tilemap / shader / physics /
  │     audio / navigation / ui / help
  │
  ├─ coding-solo 独有 4 工具（移植，其余 10 个被 better 覆盖已删除）
  │     list_projects（纯目录扫描，无 Godot 依赖）
  │     export_mesh_library / get_uid / update_project_uids（godot_operations.gd 进程驱动）
  │
  └─ image-gen 原生 2 工具（Volcengine 文生图 → 写 Godot assets/，Godot 自动 import）
        generate_sprite / generate_image
```

> 合并说明：coding-solo 14 个平铺工具中，launch_editor / run_project / get_debug_output /
> stop_project / get_godot_version / get_project_info / create_scene / add_node / load_sprite /
> save_scene 全部被 better 的 17 复合工具（含 project.run / editor.launch / scenes / nodes…）等价覆盖，
> 故整体删除；仅移植 4 个真正独有能力。两上游 SDK 不再冲突——统一到 sdk ^1.30.0，无子进程代理、无前缀。

## 目录

```
src/
  index.ts            单 Server 入口（配置读取 + 检测 Godot + registerTools + 传输）
  cs-unique/          coding-solo 独有工具移植（list_projects + 3 个 godot 进程工具）
  godot-scripts/      bundled godot_operations.gd（驱动 export_mesh_library/get_uid/resave_resources）
  image-gen/          移植自 cocos-mcp-bridge 的 Volcengine 文生图
  better/             better-godot-mcp 源码（Apache-2.0，保留 LICENSE/LICENSE-MIT/NOTICE + addons）
LICENSE.md            MIT（sovereign 层 + 移植成分说明）
LICENSE-apache.md     Apache-2.0 全文（better 成分）
NOTICE                三方署名与许可声明
```

## 构建

```bash
npm install          # 安装依赖（@modelcontextprotocol/sdk ^1.30.0 + typescript）
npm run build        # 一次 tsc 编译 src/（含 better/cs-unique/image-gen）→ build/
```

## 配置（sovereign 层统一读取）

`godot-mcp-server.config.json`（放仓库根，已被 .gitignore 排除，不入库）：

```json
{
  "host": "127.0.0.1",
  "port": 8785,
  "godotPath": "D:/Godot_v4.7.1-stable_win64.exe",
  "godotProjectPath": "D:/projects/game-prototypes/tomb-delver",
  "volcArkApiKey": ""
}
```

环境变量覆盖（优先级高于配置文件）：`GODOT_PATH`、`GODOT_PROJECT_PATH`、`VOLC_ARK_API_KEY`、
`GODOT_MCP_HOST`、`GODOT_MCP_PORT`、`MCP_TRANSPORT`。
API Key 也可放 `.env`（同 cocos-bridge：~/.claude/skills/volcengine-generation/.env）。

## 运行

```bash
npm start                 # stdio 传输（对接 dsh / Cursor / Claude 等）
npm run start:http        # http 单端点 http://127.0.0.1:8785/mcp
```

## 接入 dsh（可分享，无绝对路径）

把 `godot-codely/dsh-godot-mount.patch.yml` 挂进 dsh。**先装一次全局 bin**（软链到本仓库，改代码只需重新 build）：

```bash
cd godot-mcp-server
npm install && npm run build && npm link
```

之后 patch 里 `command: godot-mcp-server`（全局命令）即可，别人克隆仓库照做一遍就能用同一份 patch：

```yaml
- insert:
    - id: mcp-godot
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        transport: stdio
        serverName: godot
        command: godot-mcp-server
        args: []
        env:
          GODOT_PROJECT_PATH: "D:/projects/game-prototypes/tomb-delver"   # ← 改成你的工程根
          GODOT_PATH: "D:/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64.exe"  # ← 可选
```

> 启动时序：godot 是纯 stdio、**无编辑器依赖**，装好 `npm link` 后无需任何常驻进程。MCP 工具在 dsh 会话初始化时挂载，所以**改了代码/配置后重启 dsh 会话**（新开一个）即生效。

## 许可

- sovereign 聚合层 + image-gen：MIT（见 LICENSE.md）
- src/better：Apache-2.0 © 2026 n24q02m（见 src/better/LICENSE，部分 MIT 见 src/better/LICENSE-MIT，
  署名见 src/better/NOTICE）
- coding-solo 移植工具 + godot_operations.gd：MIT © 2025 Solomon Elias（原仓源码已删，仅保留
  移植的 4 工具与 src/godot-scripts/godot_operations.gd，MIT 许可随附）

三方许可与署名见 NOTICE。
