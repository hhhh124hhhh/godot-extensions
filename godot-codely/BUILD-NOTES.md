# godot-cef 在 Godot 4.7.1 编辑器内嵌 —— 可复现构建笔记

> 目标：Godot 4.7.1 编辑器右侧 Dock 内嵌 dsh web(`http://127.0.0.1:3080`)。
> 结论：**官方 release 的 gdcef.dll 无法在编辑器内嵌**，必须自行重编并打一行补丁。
> 验证日期：2026-08-16。实测通过（headless 已见 `texture_set=true` + `load_finished status=200`）。

## 两个真因（都不是安全软件、不是 Godot 版本）

### 真因 1：CefTexture 不是 tool 类 → 编辑器只给占位壳

Godot 对**非 tool 的 GDExtension 类**在编辑器里只创建 *placeholder instance*（runtime class 机制），
`init()` 根本不会被调用，任何方法调用都报：

```
ERROR: Cannot call GDExtension method bind 'on_ready' on placeholder instance.
```

godot-cef 作者只给辅助类加了 `tool`（`CefTexture2D`、`CefIpcInspector`），
主类 `CefTexture` **故意没加**——因为它设计给**游戏运行时**用，不是编辑器。
我们把它塞进编辑器 Dock，正踩这个未支持场景。

**修复**：`patches/0001-cef-texture-tool-class.patch`（一行）

```rust
-#[class(base=TextureRect)]
+#[class(base=TextureRect, tool)]
```

### 真因 2：源码分支与随包 libcef 的 CEF API 版本错配

- release 包 `bin/x86_64-pc-windows-msvc/libcef.dll` = **CEF 148.0.10**（chromium-148.0.7778.218）
- 仓库 `main` HEAD（`chore: update deps`）已升到 `cef = 151.2.0` → 请求 API `15101`

用 main HEAD 编出的 dll 配 148 的 libcef 会硬崩：

```
ERROR: Request for unsupported CEF API version 15101
FATAL: CefApp_0_CToCpp called with invalid version -1
```

**修复**：必须从 **tag `v1.15.3`**（commit `8e7b958`）编，其依赖为
`cef = 148.2.0` / `cef-dll-sys = 148.2.0` / `godot = 0.5.3 (api-4-5)`，与随包 libcef 精确配套。

> 注意：`git clone` 默认可能是 depth=1，需 `git fetch --unshallow --tags` 才能看到 tag。
> tag 用 `git tag --sort=-v:refname` 排（字母序会把 `v1.15.3` 排到 `v1.5.0` 前面，容易误判"没有该 tag"）。

## 可复现步骤

```bash
# 1. 取源码并切到与随包 libcef 配套的 tag
git clone https://github.com/dsh0416/godot-cef <你的源码目录>
cd <你的源码目录>
git fetch --unshallow --tags
git checkout -B v1153-tool v1.15.3          # commit 8e7b958

# 2. 打 tool 补丁（一行）
git apply <仓库路径>/godot-codely/patches/0001-cef-texture-tool-class.patch

# 3. 工具链（本机已装）：Rust nightly + cmake + ninja
export PATH="$PATH:/c/Program Files/CMake/bin:/c/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/Common7/IDE/CommonExtensions/Microsoft/CMake/Ninja"
cargo +nightly build --release -p gdcef      # 首次约 10min（含 CEF 148 分发下载）

# 4. 替换进 addon（勿动 libcef.dll 等其它依赖文件）
cp -f <源码目录>/target/release/gdcef.dll \
      <你的addon目录>/godot_cef/bin/x86_64-pc-windows-msvc/gdcef.dll

# 5. headless 自检（路径用 Windows 绝对路径 D:/ 形式，不能用 /d/）
"<你的Godot 4.7.1控制台版路径>" \
  --headless --editor --quit --path "<你的Godot工程>" > <你的日志路径>/cef.log 2>&1
```

### 通过标准（headless 日志里必须同时出现）

| 行 | 含义 |
|---|---|
| `Initialize godot-rust (API v4.5..., runtime v4.7.1...)` | godot-rust 加载成功（runtime ≥ API 即可） |
| `[CefInit] Startup summary: ...` | CEF 初始化真正执行（说明不是占位壳） |
| `DevTools listening on ws://127.0.0.1:9229` | CEF 子进程成功 spawn（EDR 未拦） |
| `probe@4.0s ... texture_set=true` | 纹理已上屏（内嵌渲染生效） |
| `load_finished url=... status=200` | 目标页面加载成功 |
| **不得出现** `placeholder instance` / `unsupported CEF API version` | — |

## 环境事实（本机，避免重复踩）

- `nightly` 必需（`retour-rs` 依赖）；`cmake` + `ninja`（ninja 在 VS2022 BuildTools 里）。
- rustup 官方源被 EDR 拦 → 需 `RUSTUP_DIST_SERVER=https://mirrors.ustc.edu.cn/rust-static`；
  cargo 走 `.cargo/config.toml` 里的 ustc 镜像可正常拉 crate。
- addon 目录**不要放在被 EDR 高频扫描的路径**：Godot 加载 GDExtension 会把 `gdcef.dll` 复制成 `~gdcef.dll`
  再加载，Defender 锁源文件会导致三行错误
  （`Failed to open ~gdcef.dll` / `Error copying library` / `Can't open GDExtension`）。
  本机绕法 = 真身放 `D:\godot-addons\godot_cef`，工程 `addons/` 用 junction 挂载。
- `~gdcef.dll*.TMP` 残留会被 EDR 锁住删不掉，**无害**，可忽略。
- headless `--editor` 下 GPU 不可用，`create_rd_texture` 返回 `Err(Failed to get RenderingDevice)`
  是**正常**的（代码有 fallback），会走 software rendering，依然能加载页面。

## 已排除的错误假设（省时间）

| 假设 | 结论 |
|---|---|
| godot-rust 0.5.x ↔ Godot 4.7 ABI 不兼容 | ❌ 极简对照扩展（Node 与 TextureRect 空类）在 4.7.1 上均正常实例化 |
| 用 `api-4-7` 精确匹配引擎版本 | ❌ 反而更糟；官方就是 `api-4-5`，靠 Godot 向后兼容（runtime ≥ API） |
| 升 godot-rust 到 0.5.5 / 0.6+ | ❌ 与本问题无关，0.5.5 同样占位壳 |
| 降级 Godot 到 4.6.3 | ❌ 无必要；且用 `api-4-7` 编的 dll 在 4.6.3 上会 panic（runtime < API） |
| `CefTexture::init` 在 4.7 panic | ❌ 加诊断打印后确认 init 全链跑通，问题是 init 从未被调用 |
| EDR 拦 CEF 子进程 | ❌ `DevTools listening on 9229` 证明子进程正常起 |
