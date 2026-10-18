# Godot Codely

**AI 驱动的 Godot 游戏开发专家团** — DeepSeek Harness 插件

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![DSH](https://img.shields.io/badge/DSH-rc.8-orange.svg)](https://github.com/deepseek-ai/deepseek-harness)
[![Godot](https://img.shields.io/badge/Godot-4.7-blue.svg)](https://godotengine.org)

---

## ✨ 这是什么

Godot Codely 把 **五人专家团** 装进 AI，让 AI 像专业游戏开发团队一样工作：

- 🏗️ **架构师** — 场景树、信号解耦、类型安全
- 🎮 **玩法师** — 物理、手感、动画状态机
- 🌍 **世界师** — TileMap、程序化关卡、着色器
- 🎨 **界面师** — Control 布局、商业化 UI
- ✅ **质量师** — 三道闸验证、导出发布

##  效果演示

```
你：「做一个平台跳跃游戏，角色能二段跳，有敌人和金币」

AI（五人团协作）：
  架构师：设计场景树结构、信号解耦方案
  玩法师：实现物理移动、跳跃手感、碰撞检测
  世界师：生成 TileMap 关卡、放置金币和敌人
  界面师：创建 HUD、分数显示、暂停菜单
  质量师：编译闸 → 冒烟闸 → 功能自测闸
```

## ️ 架构

```
┌─────────────────     ┌─────────────────┐     ─────────────────┐
│   DSH Web UI    │────▶│  Godot Codely   │────▶│ godot-mcp-server│
│   (AI 对话)      │     │  (五人专家团)    │     │   (23 工具)      │
│   :3080         │     │                 │     │   stdio 挂载     │
└─────────────────┘     └─────────────────┘     ────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Godot 工程     │
                                                 │  .tscn / .gd    │
                                                 ─────────────────┘
```

##  快速开始

### 前置条件

- Node.js ≥ 22
- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 已安装
- Godot 4.7+ 已安装

### 安装

```bash
# 1. 构建 MCP Server
cd godot-mcp-server && npm install && npm run build && npm link

# 2. 挂载到 DSH
dsh plugin --profile web add ./godot-codely
```

### 使用

1. 启动 DSH：`dsh web`
2. 打开 http://127.0.0.1:3080
3. 选择 **「Godot Codely」** 预设
4. 告诉 AI 你的 Godot 工程路径
5. 开始开发！

## 📦 包含内容

| 文件 | 作用 |
|------|------|
| `presets/godot/agent.cordis.yml` | 「Godot Codely」短 persona（`dsh-persona` / `config.text`） |
| `dsh-godot-mount.patch.yml` | MCP 挂载配置 |
| `SYSTEM_PROMPT.md` | 短 persona 源正文（须与两处 preset 的 `config.text` 逐字相同） |
| `docs/` | 按需长材料：方法论 2.0、分层验证、Loop 示例、zfoo、五人团路由 |
| `godot-codely-addon/` | 编辑器内嵌面板（可选） |
| `godot-framework/` | Godot 轻量级框架 + Agent 技能集（来自 [godot-fun/godot-framework](https://github.com/godot-fun/godot-framework)） |
| `QUICKSTART.md` | 端到端教程 |

## 🔧 MCP 工具列表

23 个工具，覆盖 Godot 开发全流程：

| 类别 | 工具 |
|------|------|
| **场景** | `scenes.list` `scenes.info` `nodes.list` `nodes.add` `nodes.set_property` |
| **脚本** | `scripts.create` `scripts.write` `scripts.attach` `scripts.read` |
| **运行** | `project.run` `project.stop` `project.export` |
| **系统** | `resources` `input_map` `signals` `animation` `tilemap` `shader` `physics` `audio` |
| **AI 出图** | `generate_sprite` `generate_image` |

## 🔥 方法论 2.0

长文在 `docs/methodology-2.0.md`，**不**注入每轮系统提示。单智能体 Codely 直接做最小一层。分层验证：结构编辑用 `scenes.info`；行为要引擎才 `project.run` 一次；宣称可上架 / Phase 3 完成才跑满三道闸。小改动不自动冒烟或功能自测。

预设不再每轮注入下面全文，需要时再读 `docs/`：

### 不灰盒
第一个交付就是**能玩的核心循环游戏**，从 t=0 按「能不能上架」倒推。

### 阶段门控
- Phase 0：脚手架（落 PROJECT.md）
- Phase 1：核心循环
- Phase 2：内容质感
- Phase 3：三道闸发布

### 三道闸（仅宣称可上架 / Phase 3 完成）
1. **编译闸** — `godot-verify` 全量 load
2. **冒烟闸** — `godot-runtime-smoke`
3. **功能闸** — `godot-functional-playtest`

## 👁️ 视觉验证

用户要求对画面时，再配合 [dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit)。这不是默认检查；结构编辑不要为了截图去跑游戏：

```
改代码 → 运行 → 截图 → 像素对比 → 差异 > 5% → 定位修复 → 再验证
```

## 🎯 五人团路由

单智能体 Codely **不要先五人团再动手**。路由给 **Godot Game Studio** / AgentTeams，说明在 `docs/team-routing.md`：

| 专家 | 负责领域 |
|------|----------|
| 架构(梁栋) | 场景树 / 信号 / Resource / 类型安全 |
| 玩法(动枢) | 物理 / 手感 / 动画 / 音频 / 多人 |
| 世界(境拓) | TileMap / 程序化 / 地形 / 着色器 |
| 界面(屏绘) | Control 布局 / 商业化 UI |
| 质量(验舟) | 三道闸 + 导出 |

## 🧩 Godot Framework

整合了 [godot-fun/godot-framework](https://github.com/godot-fun/godot-framework) 的运行时框架 + 40+ Agent 技能：

### 运行时框架（`zfoo/`）

| 模块 | 功能 |
|------|------|
| **Audio** | 音乐播放列表、音效、语音、交叉淡入淡出 |
| **Network** | TCP/WebSocket 客户端 + 路由消息系统 |
| **SceneHelper** | 场景切换（带淡入淡出/滑动过渡） |
| **ResourceHelper** | 异步资源加载（不阻塞主线程） |
| **SchedulerBus** | 定时/周期任务调度 |
| **HotUpdate** | PCK 热更新（检查版本→下载→校验 MD5→加载） |
| **Setting** | 持久化用户配置 |
| **Log** | 文件日志 |
| **Http** | 异步 GET/POST 请求 |
| **AI** | OpenAI 兼容聊天（多轮对话） |

### Agent 技能集（`.cursor/skills/`）

40+ 个批量资产处理技能：

| 类别 | 技能数 | 功能 |
|------|--------|------|
| **Audio** | 9 | 转 wav → 裁剪 → 响度 → 导出 |
| **Image** | 8 | 转 png → 水印 → 分割 → 去背景 → 裁剪/缩放 |
| **Video** | 9 | 水印 → 静音 → 4K → 合并 → 压缩 |
| **Storyboard** | 4 | 分镜 → HTML 预览 → 配音 → 视频 → 混音 → 发布 |
| **AI** | 1 | 文字转语音 |
| **其他** | 2 | 命名规范、提交规范 |

### 使用方式

在 Godot 项目中：
1. 复制 `godot-framework/zfoo/` 到项目根目录
2. 注册 Autoload：`Project → Project Settings → Autoload → GodotFramework (res://zfoo/GodotFramework.tscn)`
3. 完成！

在 AI Agent 中：
- Cursor / OpenCode：原生支持 `.cursor/skills/`
- Claude：复制 `.cursor/skills/` → `.claude/skills/`
- Codex：复制 `.cursor/skills/` → `.agents/skills/`

##  相关项目

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) — AI Agent 运行时
- [godot-mcp-server](../godot-mcp-server) — Godot MCP Server
- [godot-framework](https://github.com/godot-fun/godot-framework) — Godot 轻量级框架 + Agent 技能集
- [dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit) — 视觉验证插件

##  License

MIT © 2026 hhhh124hhhh