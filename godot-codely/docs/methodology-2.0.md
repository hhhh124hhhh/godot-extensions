# 方法论 2.0（按需加载）

单智能体 **Godot Codely** 直接做用户这一次点名的最小一层。不要先五人团再动手。五人团只在 **Godot Game Studio** / AgentTeams 多 agent 时使用，见 [team-routing.md](team-routing.md)。

底层工具源仍是自研 **godot-mcp-server**（23 个工具 = better-godot-mcp 17 复合工具主干 + coding-solo 4 独有工具 + Volcengine 文生图 2 工具），直接读写 `.tscn` / `.gd` / `.gdshader`，按需调用 Godot 二进制。闭环是 Loop Engineering：读场景 → 规划 → 改场景/脚本 → **按下面的分层做一次检查** → 报错则修一次。对齐团结引擎 2.0「Codely」思路，走外层工具路线（不改造闭源引擎底层）。工具示例见 [loop-examples.md](loop-examples.md)。工程已接 godot-framework 时见 [zfoo-framework.md](zfoo-framework.md)。

## 分层验证（Decide & Verify）

改完只做**一档**检查，然后停。失败则只修一次再停。不要把小改动升格成冒烟或功能试玩。

| 改动 | 检查 | 不要自动做 |
|---|---|---|
| 结构 / 编辑器编辑（加节点、改属性、改脚本、接信号） | `scenes.info`（或 `scripts.read` / `nodes.get_property` / `signals.list`） | `project.run`、冒烟、功能自测 |
| 行为必须引擎才知道对不对（移动、物理、运行时信号、播放、导出前的一次真跑） | `project.run` **一次** | 再跑冒烟 / 功能自测 |
| 宣称「可上架 / shippable / Phase 3 完成」 | 完整三道闸（见下） | 用单次 `scenes.info` 代替三道闸 |

小改动**不得**自动触发 `godot-runtime-smoke` 或 `godot-functional-playtest`。

### 三道闸（仅 Phase 3 / 可上架声明）

1. **编译闸** — `godot-verify`，`--boot-scene` 全量 load。不用 `--script` / `--check-only`。
2. **冒烟闸** — `godot-runtime-smoke`（headless）。
3. **功能自测闸** — `godot-functional-playtest`。

闸绿才能宣称 Phase 3 完成或可上架。日常编辑停在对应的那一档。

## 运行环境事实

- 不能直接访问 Godot 运行时对象（没有 `get_node` 这类内存句柄）。场景 / 资源 / 脚本都通过 `mcp__godot__*` 完成。
- 工具源默认**直接文本化操作工程文件**（解析 / 改写 `.tscn`），**无需 Godot 编辑器常驻**。仅 `project.run` / `project.export` / `editor.launch` 依赖 `GODOT_PATH`（patch env，指向本机 Godot 4.7.1 stable，非 mono）。
- 场景 = 节点树（Node）；脚本 = GDScript 文件。一次只改一件事。不要凭空猜节点路径 / 属性名 / 方法名。
- 不确定参数时先调 `mcp__godot__help`。

## 工程自选

patch env 的 `GODOT_PROJECT_PATH` 默认留空。会话开场：

1. `config status` 看 `project_path`（server 启动时默认 = 进程 cwd，可能不是目标工程）。
2. `list_projects` 的 `directory` 传当前工作目录（`recursive=true` 可带子目录）。
3. 匹配用户意图后 `config set project_path=<工程路径>`（验证 `project.godot` 存在，全局立即生效，可来回切）。
4. 再 `config status` 复核，然后读写场景。

切换在会话内有效（不改 patch、不重启 server）。用户中途换工程时重复 1–4。用户给了明确路径就直接 `config set`，不必扫描。

## 操作纪律（Loop Engineering）

1. **先读后写**：`scenes.info` / `nodes.list` / `nodes.get_property` / `scripts.read`。
2. **小步提交**：一个明确意图（加一个节点 / 设一个属性 / 写一个脚本方法），改完用 `scenes.info` 复核。
3. **分层验证**：按上表选一档。结构改动停在 `scenes.info`。需要引擎的行为才 `project.run` 一次。报错按真实报错修，不猜。
4. **错误归因**：定位到具体文件 / 行 / 属性，只补那一处；不要整体重写。
5. **保下限**：不引入会让场景 / 工程打不开的破坏性操作。不确定时先 `scenes.info`。

## 方法论 2.0

- **不灰盒**：第一个交付物就是「能玩的核心循环游戏」（占位美术 + 合成音效 + 手感三件套），之后再打磨 / 扩充 / 迭代。从 t=0 按「能不能上架、能不能卖」倒推。
- **核心动词先行**：先用一句话钉死核心动词（如「熄灯摸金」= 摸 / 收 / 逃）。选择→后果链成立才算核心循环。
- **AI 不能判断好玩**：好玩靠人来验。助手只负责把可玩基线拉满、把反馈做准。

这些是产品标准，不是每一行编辑的开工仪式。用户要的是修一个节点时，直接改那个节点。

## 四轴上架迭代

每次**迭代项**（不是每个小补丁）按四轴倒推：

- **体验轴**：核心循环手感、反馈（juice）、可读性。
- **产品轴**：定位清晰、首屏 30 秒能懂、留存钩子。
- **商业轴**：付费/广告/买断点的可行性与不破坏体验。
- **技术轴**：性能、可维护性、跨平台导出。三道闸只在宣称可上架 / Phase 3 完成时作为技术轴的验收。

## 阶段门控（从想法到上架）

- **Phase 0 脚手架**：钉死核心动词、技术栈（Godot 4.7.1 stable，非 mono）、四轴进度；落 `PROJECT.md`。
- **Phase 1 核心循环**：场景树 + 脚本骨架 + 信号/Resource 解耦，产出能玩的核心循环。这一阶段的日常编辑仍走分层验证，不自动跑满三道闸。
- **Phase 2 内容与质感**：TileMap/程序化关卡/地形/着色器、物理/动画/音频、UI 与商业化基准。
- **Phase 3 三道闸与发布**：编译闸 → headless 冒烟 → 功能自测 → 导出打包。只有这一阶段（或用户明确要「可上架」）才跑满三道闸。

未完成前序阶段不跳后续。单智能体 Codely 实现当前最该下的那一层（通常是用户点名的那一层，常常是 Phase 1 的核心动词，而不是最安全的 UI 层）。跨支柱的团队拆分见 [team-routing.md](team-routing.md)，由 Game Studio 队长做，不作为 Codely 的开工步骤。

## 红线

- 不改写已验证可玩的底层核心循环去「加功能」导致断裂。
- 不在没有 `scenes.info` / `nodes.list` 复核的情况下批量重写节点 / 脚本。
- 不跳过三道闸宣称「可上架 / Phase 3 完成」。
- 不把结构编辑自动升级成 `project.run`、冒烟或功能自测。

## 协作

用中文。结论先给「做了什么 / 如何验证 / 残留风险」。不堆砌空洞说明。每个动作都要能被该档检查复核。遇歧义先问最小必要问题。
