# Godot Codely — Quickstart（基于自研 godot-mcp-server）

把 **Godot 游戏开发工作室专家团**（方法论 2.0 / 四轴 / 阶段门控 / 五人团）能力接入 dsh 的工作台插件：
dsh web 侧聊天 + 自研 **godot-mcp-server**（23 个工具，直接读写 Godot 工程）+ 可选的 **Godot 编辑器内嵌面板**（`godot-codely-addon/` + godot-cef）。
忠实对标 `cocos-codely` 的 Route B 模式。

## 为什么用自研 godot-mcp-server（而不是拉上游）
- **23 个工具 = 去重合并后的主权聚合器**：better-godot-mcp 17 复合工具主干（~70 动作）+ coding-solo 4 独有工具（list_projects / export_mesh_library / get_uid / update_project_uids）+ Volcengine 文生图 2 工具（generate_sprite / generate_image）。
- **stdio 传输**，dsh 的 `@deepseek-ai/dsh-mcp-client` 原生支持 → 直接挂，无需 HTTP 中间层。
- **直接文本化操作工程文件**（解析/改写 .tscn），**无需 Godot 编辑器常驻**；只有 run/export/launch 才要 Godot 二进制。
- **离线可用、无前缀、统一配置**：单一 McpServer / 单一注册 / 配置与 API Key 统一读 `godot-mcp-server.config.json` 或 env。剥离 phone-home / 遥测。
- 取代早期「自研 HTTP 桥接」（已归档 `_archive/`）与「npx 拉上游 better-godot-mcp」（临时方案）。

## 架构
```
dsh web (3080)  ──stdio spawn──►  godot-mcp-server（全局命令，npm link 后直接可用）
                                          │  文本化读写 .tscn/.gd + 按需调用 Godot 二进制 + 文生图
                                          ▼
                                    你的 Godot 工程目录（patch env.GODOT_PROJECT_PATH 指定）
```
聊天入口在 **dsh web(3080)**。Godot 原生面板不能 iframe，故另提供 **路A 内嵌方案**（`godot-codely-addon/`）：
用 webview GDExtension 把 dsh web 渲染进编辑器右侧 Dock，形态同 cocos-codely。详见下方「路A:Godot 编辑器内嵌 dsh web」。

## 路A:Godot 编辑器内嵌 dsh web（可选但推荐）
想要「就像 cocos-codely 那样在编辑器里直接用」，走这条路：
1. 把 `godot-codely-addon/` 整个目录拷到你的 Godot 工程 `addons/godot-codely/`（或用 `install.ps1 -Project <工程>` 挂 junction）。
2. 装一个 webview GDExtension（推荐 **godot-cef**，明确支持 Godot 4.5+，对 4.7.1 最稳；或 Godot WRY）。详见 `godot-codely-addon/README.md`。
3. 编辑器 **Project → Project Settings → Plugins** 启用 `Godot Codely` 和 webview 扩展。
4. 右侧 Dock 出现 `Codely` 面板 → 渲染 dsh web(3080) → 直接在编辑器里聊。

> ⚠️ 已实测打通（2026-08-16）：官方 release dll 不可用必须自编，完整复现见 `BUILD-NOTES.md`；
> 编辑器 Dock 内的焦点/输入法/缩放仍需真机实测。

## 4 步端到端
### 1. 装 godot-mcp-server（一次性）
```bash
cd godot-mcp-server
npm install && npm run build
npm link        # 全局命令 godot-mcp-server 可用（软链，改代码只需重新 build）
```
> npm link 被 EDR 拦时，退化为把 patch 的 command 改成 node + 绝对路径（见「离线/受限方案」）。

### 2. 工程自选（patch env 默认留空，无需改路径）
`dsh-godot-mount.patch.yml` 的 `env.GODOT_PROJECT_PATH` **默认留空**——agent 在会话开场自动按工作目录选工程：

1. `config status` 看当前指向（启动时默认 = 进程 cwd）。
2. `list_projects` 的 `directory` 传当前工作目录（`recursive=true` 带子目录），拿工程列表。
3. `config set project_path=<工程路径>` **运行时切换**（全局生效、可来回切，不改 patch 不重启）。
4. `config status` 复核后再动手。

想固定默认工程也可填具体路径（如 `D:/projects/MyGame`）；`GODOT_PATH` 指向本机 4.7.1 二进制（留空自动探测）。

### 3. 起 dsh 并挂 godot-MCP
> ⚠️ **路径用 Windows 绝对路径**（如 `D:/...`），不要用 Git Bash 的 `/d/...` 形式 ——
> dsh 的 `resolve()` 在 Node 内执行，`/d/foo` 会被落成 `D:\d\foo` 导致 ENOENT。

本机实测用 node + tsx 直跑（若 `dsh` 已在 PATH，可把 `node --import tsx/esm apps/cli/src/index.ts` 换成 `dsh`）：
```bash
cd <deepseek-harness>
node --import tsx/esm apps/cli/src/bin.ts web \
    --patch D:/path/to/godot-codely/dsh-godot-mount.patch.yml
```
正常启动后 dsh web 起在 3080，模型可见 `mcp__godot__*` 全套 23 工具。
> 若日志报 `patch: entry "mcp-godot" not found`，说明 patch 里漏了 `insert:` 包裹（见下方「已知边界」），MCP 没挂上。

### 4. 选 Godot Codely preset（专家团能力自动注入）
**不用手动粘 system prompt**。新建会话时：
1. dsh web(3080) 新会话界面右侧有「模式」芯片（默认可能是 Cocos Codely）。
2. 点开 → 选 **Godot Codely**（id=`godot-codely`，user 信任级）。
3. 新建会话带上**短 persona**（先读后写、一次检查然后停）+ 全套 godot 工具。方法论 2.0 / 四轴 / 阶段门控 / 五人团 / 工具长示例在 `docs/`，按需再读，不进每轮系统提示。单智能体 Codely 直接做最小一层，不要先五人团再动手。

> 为什么是自动的：生效的是 preset 里 `@deepseek-ai/dsh-persona` 的 `config.text`。
> 这段正文必须与另外两处逐字相同：本仓 `SYSTEM_PROMPT.md`，以及 `presets/godot/agent.cordis.yml`。
> 长材料改 `docs/`，不要写回 persona。见 `AGENTS.md` 同步纪律。

### 4.1 DeepSeek-V4.1-Flash（日常模型，用户侧 DSH 配置）

短系统提示是给 Flash 用的：思考开着，边界放在用户消息和按需文档里。本仓**没有**模型路由配置文件（搜过 patch / preset，没有 `reasoningEffort` 或 `deepseek-flash` 字段），下面是 **DSH profile / 模型路由里由用户自己设** 的建议，字段名以你本机 DSH 为准：

- 模型：`deepseek-flash`（DeepSeek-V4.1-Flash）
- 打开 thinking
- `reasoningEffort`：日常 `high`；很小的改动 `low`；只有难问题用 `max`

### 5. 开干
在 dsh web(3080) 用中文描述需求 → 模型走分层验证：
`scenes.info` 看结构 → `nodes.add` / `nodes.set_property` / `scripts.write` 改 → 结构编辑用 `scenes.info` 停；只有行为需要引擎才 `project.run` **一次**。宣称可上架 / Phase 3 完成才跑满三道闸。小改动不自动冒烟或功能自测。

## 离线 / EDR 受限方案（可选）
若 `npm link` 或全局命令被网络 / EDR 拦（本机常遇到），退化为直接用 node 跑 build 产物：
```bash
cd godot-mcp-server && npm install && npm run build   # 先构建（一次性）
```
然后把 patch 里的 command 改成（args 为你的绝对路径，每台机器不同）：
```yaml
    command: node
    args: ["<仓库路径>/godot-mcp-server/build/index.js"]
    cwd: "<仓库路径>/godot-mcp-server"
```
（默认的 `command: godot-mcp-server` 两行删掉即可；其余 env/transport 不变。）

## 工具清单（mcp__godot__*，23 个）
project(info/version/run/stop/settings_get/settings_set/export) /
scenes(create/list/info/delete/duplicate/set_main) /
nodes(add/remove/rename/list/set_property/get_property) /
scripts(create/read/write/attach/list/delete) /
editor(launch/status) / config(status/set/detect_godot/check) /
resources(list/info/delete/import_config) /
input_map(list/add_action/remove_action/add_event) /
signals(list/connect/disconnect) /
animation(create_player/add_animation/add_track/add_keyframe/list) /
tilemap(create_tileset/add_source/set_tile/paint/list) /
shader(create/read/write/get_params/list) /
physics(layers/collision_setup/body_config/set_layer_name) /
audio(list_buses/add_bus/add_effect/create_stream) /
navigation(create_region/add_agent/add_obstacle) /
ui(create_control/set_theme/layout/list_controls) /
help /
list_projects / export_mesh_library / get_uid / update_project_uids /
generate_sprite / generate_image（后两个需 VOLC_ARK_API_KEY）

## 与 cocos-codely 的差异（为何不 1:1 薄壳）
- Cocos 面板是 HTML/Chromium webview，能 `<iframe>` 嵌 dsh web → cocos-codely 是薄壳。
- Godot 面板是原生 `Control`（IMGUI），**不能 iframe** → 用 **webview GDExtension** 渲染 dsh web（路A），等价内嵌，但依赖外部扩展。
- godot-codely = dsh 编排 + 自研 godot-mcp-server（直接吃工程文件）。
- 若暂不走路A：聊天入口在 dsh web(3080)，Godot 侧只做"被驱动的工程"，开编辑器看热重载即可。

## 已知边界
- `project.run` / `project.export` 是长操作，失败或超时时在 dsh 里续写修复命令即可。
- 不确定某工具的参数 → 先调 `mcp__godot__help`（自带文档工具）。
- 自研 server 默认文本化改 .tscn。结构编辑用 `scenes.info` 复核即可；行为需要引擎时 `project.run` 一次。三道闸（godot-verify → 冒烟 → 功能自测）只在宣称可上架 / Phase 3 完成时跑满。小改动不要自动升格。
- **改 `dsh-godot-mount.patch.yml` 必须保留顶层的 `- insert:` 包裹**（见 dsh `examples/mcp-memory/engram.cordis.yml`）。
  若把 `mcp-godot` 行直接放顶层（无 `insert:`），dsh 会把它当成「覆盖已有行」而报
  `patch: entry "mcp-godot" not found`，**MCP 静默不挂载**。
- **改 patch 的 `--patch` 路径必须用 Windows 绝对路径**（`D:/...`），不要用 `/d/...`（Node 内 `resolve` 会落成 `D:\d\...`）。
- 短 persona 三处必须逐字相同：`SYSTEM_PROMPT.md`、`presets/godot/agent.cordis.yml` 的 `config.text`、`~/.dsh/.agent-presets/godot-codely/agent.cordis.yml`（源在主仓 `agent-presets/godot-codely/`）。生效的是 preset 里的 `config.text`。长方法论在 `docs/`。
