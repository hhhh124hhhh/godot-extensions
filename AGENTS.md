# Godot MCP Stack — Agent 安装指南

本目录是 **Godot AI 工程助手** 的完整可分发单元，包含两套必须同时存在的组件。
任何 agent（dsh / Claude Code / 其他编码 agent）都可以照本指南把整套装好。

---

## 1. 这套东西由什么组成

| 组件 | 角色 | 装到哪里 | 缺了会怎样 |
|---|---|---|---|
| **godot-codely** | dsh 客户端插件（bundle）。告诉 dsh「spawn 自研 godot-mcp-server」并注入 Godot 方法论预设 | dsh `web` profile | dsh 没有 `mcp__godot__*` 工具，连不上 |
| **godot-mcp-server** | 自研 Godot MCP 服务器（23 工具：better-godot-mcp 17 复合工具主干 + coding-solo 4 独有 + Volcengine 文生图 2）。stdio 传输，直接文本化读写 `.tscn`/`.gd` | 本机构建 + `npm link` 全局命令 | `mcp__godot__*` spawn 失败，工具全缺 |
| **agent-presets/** | 专家团预设（7 个：架构/玩法/世界/界面/质量 5 角色 + `Godot Codely` 工程助手 + `Godot Game Studio` 队长）+ AgentTeams 多 agent 协作 | `~/.dsh/.agent-presets/` + profile `bundles` | 没有可选的专家角色预设 / 不能拉团队 |

**关键心智模型**：dsh 插件是「电话线」，godot-mcp-server 是「对面接电话的人」。
线装对了但没人接（server 没起）= 打不通。两者必须同时在线。

---

## 2. 前置条件

- 已安装 **dsh**（存在 profile `web`，默认路径 `~/.dsh/profiles/web`）。
- 已安装 **Godot 4.7.1 stable**（非 mono；3.5+ 也可用，但专家团锚定 4.7.1）。
- 运行环境：Node.js（用于跑安装器）；Windows / macOS / Linux 均可。

---

## 3. 一键安装（推荐 agent 直接跑）

```bash
node install-godot-stack.mjs
```

安装器会**幂等**地完成：
1. 把 `godot-codely` 装进 dsh profile：**默认覆盖式手工同步**（复制白名单文件到 `node_modules/godot-codely` + 校准 profile `package.json` 的 `dependencies`/`bundles`）。传 `--try-dsh` 才先尝试官方 `dsh plugin add`，失败自动回退手工。
2. 构建 `godot-mcp-server`（`npm install && npm run build && npm link`），让全局命令 `godot-mcp-server` 可用。依赖/构建产物已存在时自动跳过（幂等）。失败会提示退化方案（改 patch 的 command 为 node + 绝对路径）。
3. 把 `agent-presets/`（7 个专家团预设）同步到 `~/.dsh/.agent-presets/`，并激活 `@nanmicoder/dsh-agent-teams`（AgentTeams 多 agent 协作插件，包在 profile `node_modules` 时挂 bundle；新机未装会提示装法）。
4. 打印验证命令与下一步。

参数：
- `--profile <name>`：dsh profile 名，默认 `web`。
- `--try-dsh`：先试官方 `dsh plugin add`（本机 EDR 会拦，会自动回退）。
- `--no-mcp-build`：跳过 godot-mcp-server 的构建/链接（已装过时用）。
- `--dry-run`：只打印将要做什么，不落盘。

> **为什么默认不走 `dsh plugin add` / 不删旧文件**：WorkBuddy 运行环境注入了 `genie-safe-delete` shim，会把 **node 自身的 `fs.rmSync`** 也路由到「回收站(trash)」，而本机 EDR 拦回收站操作 → 抛 `[safe-delete] 操作失败: Some operations were aborted`。这不只影响 pnpm，**任何在 WorkBuddy 里跑的 node 删除操作都会中招**。因此安装器 STEP 1 **完全不删、只覆盖同步**。全程**不需要关闭/排除任何杀软**。

---

## 4. 手动安装（无脚本时）

### 4.1 dsh 客户端插件
```bash
dsh plugin --profile web add <本目录>/godot-codely
```
等价手工法（EDR 阻断 pnpm 时用）：
- 将 `godot-codely` 的白名单文件（`package.json` / `dsh-godot-mount.patch.yml` / `presets/` / `SYSTEM_PROMPT.md` / `README.md` / `QUICKSTART.md` / `AGENTS.md`）复制到
  `~/.dsh/profiles/web/node_modules/godot-codely/`。
- 在 `~/.dsh/profiles/web/package.json` 的 `dependencies` 加 `"godot-codely": "file:<绝对路径>/godot-codely"`，并在 `dsh.profile.bundles` 数组追加 `"godot-codely"`。

### 4.2 Godot MCP server
```bash
cd <本目录>/godot-codely/godot-mcp-server
npm install && npm run build && npm link   # 全局命令 godot-mcp-server 可用
```

---

## 5. 验证（装完必做）

```bash
# 1) server 本体（不依赖 dsh/Godot）：
godot-mcp-server --help
# 或跑自带冒烟（spawn server → tools/list → 应见 23 个工具）：
cd <本目录>/godot-codely/godot-mcp-server && npm run smoke
```

dsh 侧验证（不依赖 Godot 工程）：
```bash
dsh --profile web --dump-config 2>&1 | grep -A6 "mcp-godot"
# 期望：看到 mcp-godot -> name '@deepseek-ai/dsh-mcp-client' / command godot-mcp-server
```

---

## 6. 让整套真正可用（运行时必做）

1. `dsh-godot-mount.patch.yml` 的 env **默认留空即可**（工程自选模式）：
   - `GODOT_PROJECT_PATH` 留空 → agent 会话开场自动按工作目录选工程：`list_projects` 扫目录 → `config set project_path=<路径>` 运行时切换（全局生效、可来回切，不改 patch 不重启）。想固定默认工程也可填具体路径。
   - `GODOT_PATH` 填你的 Godot 4.7.1 二进制（可留空自动探测）。
2. 起 dsh 并挂 godot 工具源：
   ```bash
   dsh --profile web --patch <本目录>/godot-codely/dsh-godot-mount.patch.yml
   ```
   （或走 bundle 自动挂载：`dsh plugin add file:<本目录>/godot-codely` 后重启。）
3. dsh web 3080 **`Ctrl+Shift+R`** 硬刷新 → 开新会话选 **「Godot Codely」** 或 **「Godot Game Studio」** 预设 → `mcp__godot__*` 工具出现，即可用。

### 6.5 多 agent 团队（AgentTeams，可选但推荐）

装完重启 dsh 后，新会话选 **「Godot Game Studio」** 队长预设，直接说「用 AgentTeams 做 X」：

1. 队长 `agent_teams_create` 建队（你变队长）。
2. `agent_teams_add_member` 按角色加成员：`architect` 架构（梁栋）/ `systems-engineer` 玩法（动枢）/ `world-designer` 世界（境拓）/ `ui-engineer` 界面（屏绘）/ `qa-release` 质量（验舟）。
3. `agent_teams_create_task` 把目标拆成**有依赖**的任务 → 成员领任务、`send_message` 互相协调、`update_task` 汇报。
4. `agent_teams_status` 轮询进度，队长汇总拍板；收尾 `agent_teams_delete` 归档。
5. Web UI 有实时团队活动面板；状态存 `<workspace>/.agent-teams/`。

降级路径：若 `agent_teams_*` 不可用，队长预设会退回原生 `subagent` 工具逐个委派角色预设，结果同样由你汇总。

### 6.6 生图配置（generate_sprite / generate_image 要能出图）

godot-mcp-server 的 AI 出图走**火山方舟（Volcengine Ark）**，需要 API Key：

| 项 | 配置位置 | 必填？ |
|---|---|---|
| **API Key** | 环境变量 `VOLC_ARK_API_KEY` 或 `godot-mcp-server.config.json` | ✅ 必填 |
| **Endpoint（推理接入点 ep-xxx）** | `VOLC_IMAGE_ENDPOINT` / config | 视模型而定 |
| **Model** | `VOLC_IMAGE_MODEL` / config | 可选（接入点自带默认） |

- 判定：配置好后，dsh 里调一次 `mcp__godot__generate_sprite` 能出图即通。
- ⚠️ 分享给他人：对方必须填**自己的** ep- 推理接入点与 key（作者账号内置的接入点不随仓、不随配置）。

---

## 6.7 分享边界（方法论资产，勿越界）

本仓的分享边界是**刻意设计**的，改动前先读：

| 层 | 内容 | 是否随仓 |
|---|---|---|
| **机制壳** | godot-mcp-server、AgentTeams 团队、安装器、预设框架、godot-codely-addon、CEF 补丁 | ✅ 随仓（分享价值） |
| **纪律条款** | SYSTEM_PROMPT / presets 里的 Loop Engineering、方法论 2.0、四轴、阶段门控、三道闸、五人团路由、AgentTeams 协议 | ✅ 随仓（**纪律是插件的灵魂，没有纪律插件就无意义**） |
| **方法论数据** | `~/.workbuddy/lab-intel/` 台账（情报/坑库/设计关键）、各游戏工程的私有方法论沉淀 | ❌ **不随仓**（作者私有飞轮资产） |

- 预设里对台账/组件库的引用一律是**条件化文字**（"仅作者本机有；若不存在则跳过"）——这是设计，不是遗漏。
- **禁止**把 `lab-intel`、`_cocos-kit`、`bp-*.md`、私有工程目录等数据实体加进本仓（会泄露方法论 IP，且对他人无意义）。
- 本机使用不受影响：agent 仍从本机路径读真实数据。
- **禁止**把 `godot-codely/downloads/`（CEF 下载物，数 GB）加进本仓——gitignore 已排除。

---

## 7. 常见坑（排错）

- **`mcp__godot__*` 全部缺失 / spawn 失败** → ① 确认 `godot-mcp-server` 全局命令可用（`godot-mcp-server --help`）；② patch 必须用 `insert:` 包裹（否则报 `entry "mcp-godot" not found`，MCP 静默不挂）；③ 硬刷新 dsh 3080。
- **`dsh plugin add` 报 `safe-delete` / `Some operations were aborted`** → 本机 EDR 拦了回收站操作，属预期。用本目录安装器（已带手工回退）或第 4.1 的手工法，不要加杀软排除项。
- **`project.run` / `project.export` 起不来** → `GODOT_PATH` 没配对（patch env），或配的路径不是 4.7.1 stable 控制台版。`project_path` 指向的目录要有 `project.godot`（会话内用 `config set project_path` 切换；`config status` 看当前指向）。
- **npm link 被 EDR 拦 / 全局命令不可用** → 退化方案：patch 的 `command` 改成 `node`、`args` 改成 `["<仓库路径>/godot-codely/godot-mcp-server/build/index.js"]`（绝对路径，每机不同），见 QUICKSTART「离线/受限方案」。
- **想分享给别人**：对方 `git clone` 后跑 `node install-godot-stack.mjs` 即可，无本机路径依赖（patch env 每机必填）。junction 指向的必须是**对方自己的**路径。
- **AgentTeams 拉不起团队 / 没有 `agent_teams_*` 工具** → ① 确认 `@nanmicoder/dsh-agent-teams` 已装进 profile `node_modules`（新机先 `npm install` 或 `dsh plugin add`，再重跑安装器挂 bundle）；② 改完 bundle 必须**重启 dsh**（Vite HMR 不重载 host 组合）再硬刷新 3080；③ 一个队长同时只能带一个活动团队。
- **Godot 编辑器 Dock 面板不出来（路A）** → 插件启用顺序：Project Settings → Plugins 勾选 `Godot Codely` 与 webview 扩展（godot-cef）；CEF 必须按 `BUILD-NOTES.md` 自编（官方 release dll 不可用）。
