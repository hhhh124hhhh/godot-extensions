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

## 🎬 效果演示

```
你：「做一个平台跳跃游戏，角色能二段跳，有敌人和金币」

AI（五人团协作）：
  架构师：设计场景树结构、信号解耦方案
  玩法师：实现物理移动、跳跃手感、碰撞检测
  世界师：生成 TileMap 关卡、放置金币和敌人
  界面师：创建 HUD、分数显示、暂停菜单
  质量师：编译闸 → 冒烟闸 → 功能自测闸
```

## 🏗️ 架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   DSH Web UI    │────▶│  Godot Codely   │────▶│ godot-mcp-server│
│   (AI 对话)      │     │  (五人专家团)    │     │   (23 工具)      │
│   :3080         │     │                 │     │   stdio 挂载     │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Godot 工程     │
                                                 │  .tscn / .gd    │
                                                 └─────────────────┘
```

## 🚀 快速开始

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
| `presets/godot/agent.cordis.yml` | 五人专家团预设 |
| `dsh-godot-mount.patch.yml` | MCP 挂载配置 |
| `SYSTEM_PROMPT.md` | 方法论 2.0 源文档 |
| `godot-codely-addon/` | 编辑器内嵌面板（可选） |
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

预设注入的专家团方法论：

### 不灰盒
第一个交付就是**能玩的核心循环游戏**，从 t=0 按「能不能上架」倒推。

### 阶段门控
- Phase 0：脚手架（落 PROJECT.md）
- Phase 1：核心循环
- Phase 2：内容质感
- Phase 3：三道闸发布

### 三道闸红线
1. **编译闸** — `godot-verify` 全量 load
2. **冒烟闸** — `godot-runtime-smoke`
3. **功能闸** — `godot-functional-playtest`

## 👁️ 视觉验证

配合 [dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit) 实现截图验证闭环：

```
改代码 → 运行 → 截图 → 像素对比 → 差异 > 5% → 定位修复 → 再验证
```

## 🎯 五人团路由

复杂任务自动路由给对应专家：

| 专家 | 负责领域 |
|------|----------|
| 架构(梁栋) | 场景树 / 信号 / Resource / 类型安全 |
| 玩法(动枢) | 物理 / 手感 / 动画 / 音频 / 多人 |
| 世界(境拓) | TileMap / 程序化 / 地形 / 着色器 |
| 界面(屏绘) | Control 布局 / 商业化 UI |
| 质量(验舟) | 三道闸 + 导出 |

## 🔗 相关项目

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) — AI Agent 运行时
- [godot-mcp-server](../godot-mcp-server) — Godot MCP Server
- [dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit) — 视觉验证插件

## 📄 License

MIT © 2026 hhhh124hhhh