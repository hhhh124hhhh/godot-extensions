# Godot Codely — Godot 编辑器内嵌 dsh web 面板

把 **DeepSeek Harness (dsh)** 的 web 聊天界面（已挂 `godot-mcp-server` + 专家团知识）**嵌进 Godot 编辑器右侧 Dock**，
形态与 `cocos-codely`（`iframe` dsh web）同构——只是 Godot 面板是原生 `Control`，不能 iframe，改用 **webview GDExtension** 渲染 dsh web。

```
Godot 编辑器右侧 Dock (Codely 面板)
   └─ webview 节点 (填满面板)
        └─ http://127.0.0.1:3080   ← dsh web
                                      └─ godot-mcp-server (stdio) ──► 你的 Godot 工程 .tscn/.gd
```

聊天在编辑器里，AI 改工程文件直接生效（开着的 Godot 编辑器会热重载）。

---

## 1. 前置

- `deepseek-harness` 已 `dsh --profile web --patch …/dsh-godot-mount.patch.yml` 起好，dsh web 在 **3080** 可访问。
- 一个 Godot 工程（用于存放 addon 并验证 AI 改文件）。实机版本用 **4.7.1 stable**（非 mono）。

## 2. 安装 webview GDExtension（关键依赖）

Godot 没有内置浏览器控件，必须装一个 webview 扩展。**GDExtension 跟 Godot 版本强绑定**，4.7.1 这么新，请确认下载到匹配 4.7 的构建。

推荐（按 4.7.1 兼容把握从高到低）：

| 扩展 | 节点类名 | 备注 |
|------|----------|------|
| **godot-cef** (dsh0416/godot-cef) | `CefTexture` | 基于 Chromium（Rust 写），**声明支持 Godot 4.5+**，2026 仍活跃，有预编译二进制。最新 v1.15.3（2026-06）。最稳，但 4.7.1 未明文确认。 |
| **Godot WRY** (doceazedo) | `WebView` | GDExtension，支持 4.1+，`load_url(url)`。 |
| godot-webview (i3urn) | — | 商业 indie 免费，Chromium，版本兼容未明。 |

安装步骤（以 godot-cef 为例）：

1. 去 `github.com/dsh0416/godot-cef` Releases 下载最新预编译 zip（`godot_cef-v1.15.3.zip`，约 936MB，含 CEF 运行时）。
2. 解压到你的 Godot 工程 `addons/godot-cef/`。
3. 编辑器里 **Project → Project Settings → Plugins** 启用 `Godot CEF`。
4. 本 addon 的 `codely_panel.gd` 里把 `WEBVIEW_CLASS` 设为 `"CefTexture"`（或留空让它自动探测）。

## 3. 安装本 addon

> 回答"必须每项目拷一份吗"：**不用**。推荐"单源 + 每项目符号链接"，装一次、所有工程共享同一真身。

### 方式 A（推荐）：单源 junction，所有工程可见（不依赖 Godot 飘忽的全局路径）

`addon` 只有一份真身在 `godot-codely-addon/`，用 `install.ps1` 把它以 **junction** 挂进各工程的 `addons/`。改 `godot-codely-addon/` 一处，所有挂了 junction 的工程同步生效。

```powershell
# 装进某个工程（junction 优先，EDR 拦链接则自动降级复制）
powershell -File install.ps1 -Project "<你的Godot工程根>"
# 想覆盖已装的：加 -Force
# 顺带把 webview 扩展也挂上：加 -WebView "D:/path/to/godot-cef"
```

- 安装后每个目标工程下出现 `addons/godot-codely` -> 指回本仓库的 `godot-codely-addon/`（junction / 符号链接，不是副本）。
- 多个工程都跑一遍 `-Project` 即可"一次维护、处处可用"。

### 方式 B（真·全局）：编辑器配置目录（尽力、版本依赖）

Godot 4 对 **AssetLib 里的插件**有"Install to Editor"可全局装；但**本地插件（我们这种）没有这个按钮**，只能手动把文件放到编辑器配置目录，Godot 会把它挂载为 `res://addons/` 对所有工程生效。问题在于**具体子路径随版本飘**：

```powershell
powershell -File install.ps1 -Global
# 本机落到 %APPDATA%\Godot\addons\  (= 符号链接 -> D:/GodotData/addons/)
```

⚠️ 放好后请打开任意工程 **Project → Project Settings → Plugins** 看是否列出本插件；若没列出，试候选子路径 `<editor_data>/editor_data/<ver>/addons/`（`<ver>` 如 `4.7`）。这是 Godot 4 全局本地插件的最大不确定点，**方式 A 更稳**。

### 启用（两种方式都要）

1. 打开 Godot 4.7.1 工程（方式 B 全局装则任意工程）。
2. 编辑器 **Project → Project Settings → Plugins** → 勾选启用 `Godot Codely`。
3. 右侧 Dock 出现 `Codely` 面板 → 已装 webview 扩展则内嵌 dsh web(3080)，否则退化为"打开 dsh web"按钮。
4. 确保 dsh web 已起：`dsh --profile web --patch …/dsh-godot-mount.patch.yml`

## 4. 已知风险（务必实测）

1. **编辑器内 webview 渲染**：这些 webview 扩展大多为"游戏运行时"设计，在**编辑器 Dock 面板**里能否正常渲染 + 键盘/鼠标交互，是待你在 4.7.1 实测的坑（可能重绘/焦点问题）。
2. **GDExtension 版本匹配**：4.7.1 很新，务必下到匹配构建，否则编辑器启动报扩展不兼容。
3. **dsh web 必须已起**：面板加载 `http://127.0.0.1:3080`，若 dsh 没起，webview 显示空白/报错。

## 5. Fallback（webview 不可用时的退化路径）

若 `_try_setup_webview()` 重试 50 次（≈5s）仍没探测到任何 webview 节点类，面板会**自动退化成一个按钮"打开 dsh web (3080)"**——点一下在默认浏览器打开 dsh web。注意 godot-cef 是 rust GDExtension，类(CefTexture)注册晚于编辑器插件 `_ready()`，故探测做了延迟重试，不要误以为是"没装"。
这不是"内嵌"，但保证"在 Godot 里点一下就能用 dsh 大脑"。

## 6. 与 cocos-codely 的对照

| | cocos-codely | godot-codely (路A) |
|---|---|---|
| 聊天 UI 位置 | Cocos 面板 `<iframe>` dsh web | Godot 面板 webview 渲染 dsh web |
| AI 工具源 | cocos-mcp-bridge (8765) | godot-mcp-server (stdio) |
| 专家团知识 | SYSTEM_PROMPT.md | SYSTEM_PROMPT.md（同一套） |
| 改文件方式 | MCP 工具改工程 | MCP 工具改工程（同） |
| Godot 编辑器常驻 | 不需要（Cocos 侧） | 不需要（AI 改文件），仅 run/export 调二进制 |

一句话：**知识/工具都在 dsh 侧**，Godot 这边只负责"把 dsh web 显示出来"，所以 godot-ai-assistant 那套直连 provider + `<scene>` 执行器不再需要。
