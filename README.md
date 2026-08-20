# Godot MCP Stack

**AI 驱动的 Godot 游戏开发专家团** — 五人团 + 23 工具 + 方法论 2.0

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![DSH](https://img.shields.io/badge/DSH-rc.8-orange.svg)](https://github.com/deepseek-ai/deepseek-harness)
[![Godot](https://img.shields.io/badge/Godot-4.7-blue.svg)](https://godotengine.org)

---

## ✨ 这是什么

一句话：**AI 像专业游戏开发团队一样工作**。

- 👥 **五人专家团** — 架构/玩法/世界/界面/质量各司其职
- 🔧 **23 个 MCP 工具** — 直接读写 .tscn/.gd，无需编辑器常驻
- 🎮 **方法论 2.0** — 不灰盒，第一版就是能玩的核心循环
- 🔥 **三道闸红线** — 编译/冒烟/功能自测，闸绿才算完成
- 👁️ **视觉验证** — 截图对比，像素级 UI 还原度检查
- 🤖 **AgentTeams** — 7 角色游戏开发工作室（可选）

## 🎬 效果演示

```
你：「做一个平台跳跃游戏，角色能二段跳，有敌人和金币」

AI（五人团协作）：
  架构师(梁栋)：设计场景树结构、信号解耦方案
  玩法师(动枢)：实现物理移动、跳跃手感、碰撞检测
  世界师(境拓)：生成 TileMap 关卡、放置金币和敌人
  界面师(屏绘)：创建 HUD、分数显示、暂停菜单
  质量师(验舟)：编译闸 → 冒烟闸 → 功能自测闸
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

## 📦 组件

| 组件 | 说明 |
|---|---|
| **godot-codely/** | dsh 客户端插件：MCP 挂载 + 专家预设 + 可选编辑器内嵌面板 |
| **godot-mcp-server/** | 自研 MCP Server：23 工具，直接文本化读写 .tscn/.gd |
| **agent-presets/** | 7 个专家角色预设 + AgentTeams 团队配置 |
| **install-godot-stack.mjs** | 一键幂等安装器 |

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/hhhh124hhhh/godot-extensions.git
cd godot-extensions

# 2. 一键安装（幂等，可重复跑）
node install-godot-stack.mjs

# 3. 启动 DSH
dsh web

# 4. 打开 http://127.0.0.1:3080，选择预设：
#    - 「Godot Game Studio」— 拉五人团队
#    - 「Godot Codely」— 单 agent 改工程
```

完整教程见 [QUICKSTART.md](./QUICKSTART.md) 和 [AGENTS.md](./AGENTS.md)。

## 👥 五人专家团

| 角色 | 代号 | 职责 |
|------|------|------|
| 🏗️ **架构师** | 梁栋 | 场景树 / 信号解耦 / Resource / 类型安全 |
| 🎮 **玩法师** | 动枢 | 物理 / 手感 / 动画状态机 / 音频 / 多人 |
| 🌍 **世界师** | 境拓 | TileMap / 程序化关卡 / 地形 / 着色器 |
| 🎨 **界面师** | 屏绘 | Control 布局 / 商业化 UI |
| ✅ **质量师** | 验舟 | 三道闸 + 导出发布 |

复杂任务自动路由给对应专家，简单任务单 agent 搞定。

## 🔧 23 个 MCP 工具

| 类别 | 工具 |
|------|------|
| **场景** | `scenes.list` `scenes.info` `nodes.list` `nodes.add` `nodes.set_property` |
| **脚本** | `scripts.create` `scripts.write` `scripts.attach` `scripts.read` |
| **运行** | `project.run` `project.stop` `project.export` |
| **系统** | `resources` `input_map` `signals` `animation` `tilemap` `shader` `physics` `audio` `navigation` `ui` |
| **AI 出图** | `generate_sprite` `generate_image` |

无需 Godot 编辑器常驻，MCP Server 直接文本化操作工程文件。

## 🔥 方法论 2.0

### 不灰盒
第一个交付就是**能玩的核心循环游戏**（占位美术 + 合成音效 + 手感三件套），从 t=0 按「能不能上架」倒推。

### 阶段门控
- Phase 0：脚手架（落 PROJECT.md）
- Phase 1：核心循环
- Phase 2：内容质感
- Phase 3：三道闸发布

### 三道闸红线
1. **编译闸** — `godot-verify` 全量 load，绝不用 --script/--check-only
2. **冒烟闸** — `godot-runtime-smoke` headless 运行
3. **功能闸** — `godot-functional-playtest` 自测

闸绿才算完成，AI 不会糊弄你。

## 👁️ 视觉验证

配合 [dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit) 实现截图验证闭环：

```
改代码 → 运行 → 截图 → 像素对比 → 差异 > 5% → 定位修复 → 再验证
```

## 📖 文档

- [QUICKSTART.md](./QUICKSTART.md) — 端到端教程
- [AGENTS.md](./AGENTS.md) — 安装指南 + 排错
- [godot-codely/README.md](./godot-codely/README.md) — 插件详情
- [godot-mcp-server/README.md](./godot-mcp-server/README.md) — MCP Server 文档

## 🔗 相关项目

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) — AI Agent 运行时
- [dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit) — 视觉验证插件

## 📄 License

MIT © 2026 hhhh124hhhh

（godot-mcp-server 内含 Apache-2.0 成分，见其 LICENSE/NOTICE）