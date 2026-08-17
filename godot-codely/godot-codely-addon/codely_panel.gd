## Godot Codely — 内嵌 dsh web 的编辑器面板
## 形态同 cocos-codely：cocos 面板 <iframe> dsh web(3080)，这里用 webview GDExtension 渲染 dsh web(3080)。
## dsh 已通过 dsh-godot-mount.patch.yml 挂好 better-godot-mcp(专家团知识 + godot 工具)，
## 所以面板里聊的就是"带 godot 专家团能力的大脑"。
@tool
extends PanelContainer

const DSH_WEB_URL := "http://127.0.0.1:3080"

# 按你安装的 webview 扩展填类名：
#   Godot WRY      -> "WebView"
#   appsinacup     -> "WebViewNode"
#   godot-cef      -> "CefTexture"
# 留空则自动探测常见类名。
const WEBVIEW_CLASS := "CefTexture"

# 诊断开关：true = 完全不加载 webview（不创建 CefTexture / 不跑 CEF 进程 / 不每帧渲染），
# 仅显示占位 Label。用于隔离「dock 拖不动」根因：能拖=CEF 内容或主线程循环是元凶；仍不能拖=控件存在即干扰。
const DISABLE_WEBVIEW := false

var editor_interface = null
var _webview = null
var _load_finished_fired := false


func _ready() -> void:
	# godot-cef 是 rust GDExtension，其类(CefTexture)注册晚于编辑器插件 _ready()，
	# 故延迟并多次重试探测，避免一次性检查误判为"未安装 webview"。
	_try_setup_webview(0)


func set_editor_interface(ei) -> void:
	editor_interface = ei


func _try_setup_webview(attempt: int) -> void:
	if DISABLE_WEBVIEW:
		_show_diagnostic_placeholder()
		return
	var known := ["WebView", "WebViewNode", "CefTexture"]
	var candidates: Array = []
	if WEBVIEW_CLASS != "" and not (WEBVIEW_CLASS in known):
		candidates.append(WEBVIEW_CLASS)
	for c in known:
		candidates.append(c)

	for cls in candidates:
		if ClassDB.class_exists(cls):
			_webview = ClassDB.instantiate(cls)
			break

	if _webview != null:
		_init_webview()
		return

	# godot-cef (rust GDExtension) 的类(CefTexture)注册晚于编辑器插件 _ready()，
	# 故 0.1s 重试，最多 50 次（≈5s）后仍无则退化成"打开 dsh web"按钮。
	if attempt < 50:
		await get_tree().create_timer(0.1).timeout
		_try_setup_webview(attempt + 1)
		return

	_fallback_open_button()
	push_warning("[GodotCodely] 未检测到 webview GDExtension (试过 %s)。已退化为“打开 dsh web”按钮。\n请按 addon README 安装 godot-cef / Godot WRY，并把 WEBVIEW_CLASS 设为对应类名。" % str(candidates))


func _init_webview() -> void:
	print("[GodotCodely] 检测到 webview 节点: ", _webview.get_class())
	_webview.name = "DsWeb"

	# —— 尺寸与纹理缩放 ——
	# 1) 给非零初始尺寸，避免 dock 尚未布局时 CEF 拿到 0x0 离屏表面 → 永久空白。
	# 2) TextureRect 默认按纹理原像素画、不随节点缩放；改 EXPAND_IGNORE_SIZE+STRETCH_SCALE 铺满。
	if _webview is Control:
		_webview.custom_minimum_size = Vector2(480, 320)
		_webview.size_flags_vertical = Control.SIZE_EXPAND_FILL
		_webview.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if _webview is TextureRect:
		_webview.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		_webview.stretch_mode = TextureRect.STRETCH_SCALE

	# 【关键】Windows 编辑器里 GPU 加速 OSR 依赖 Godot 把 CEF 渲染结果绑到 DX12/Vulkan 纹理，
	# README 明说此路径在 Windows 易失败（4.5.1 的 DX12 get_driver_resource 返回 0 等）。
	# 强制软件渲染（CPU 帧缓冲）彻底绕开 Godot 纹理绑定，最稳、且官方确认 Windows 支持。
	if "enable_accelerated_osr" in _webview:
		_webview.enable_accelerated_osr = false

	# —— 官方示例顺序：先设 url + osr 标志，再 add_child ——
	if "url" in _webview:
		_webview.url = DSH_WEB_URL
	elif _webview.has_method("url") or _webview.has_method("load_url"):
		_webview.load_url(DSH_WEB_URL)
	else:
		push_warning("[GodotCodely] webview 节点 %s 既无 url 也无 load_url，无法加载 dsh web。" % _webview.get_class())
		_fallback_open_button()
		return

	add_child(_webview)

	# —— 关键修复：godot-cef 的 CefTexture.on_ready 仅由 READY 通知触发 cef_retain()
	# （→ 打印 [CefInit] 并 mark_cef_retained，使 on_process 的 can_create_browser() 成立）。
	# 在编辑器 dock 中「_ready 期间 add_child」可能使子节点 READY 通知未送达 → on_ready 不跑
	# → CEF 永不初始化（日志里缺 [CefInit] 即铁证）→ 浏览器永不创建 → texture_set=false。
	# 延迟一帧确保节点已在树内、通知正常流动，再显式补触发 on_ready（cef_retain 有
	# needs_initialize 守卫，重复调用安全；即便 Godot 后续也触发 READY，仅重复无害设置）。
	await get_tree().process_frame
	if _webview.has_method("on_ready"):
		_webview.call("on_ready")
		print("[GodotCodely] 已显式触发 CefTexture.on_ready（补 READY 通知缺口）")

	# —— 诊断：导航完成信号 + 多阶段探针 ——
	# CEF 首次 spawn 渲染子进程 + 加载 3080 可能要数秒（尤本机 EDR 扫描时更慢），
	# 单次 0.5s 太早。1.5s/4s/8s 各探一次，看 texture 最终是否出现、load_finished 是否触发。
	if _webview.has_signal("load_finished"):
		_webview.connect("load_finished", _on_load_finished)
	_probe_webview(1.5)
	await get_tree().create_timer(2.5).timeout
	_probe_webview(4.0)
	await get_tree().create_timer(4.0).timeout
	_probe_webview(8.0)

	# —— 渲染结果兜底：若 8s 后纹理仍未挂上（典型为 godot-cef 在 4.7.1 下只注册了占位类，
	# instantiate 出 placeholder instance，on_ready 调不动、纹理永 null），不静默黑屏，
	# 改为明确诊断 + 浏览器兜底按钮。
	await get_tree().create_timer(1.0).timeout
	_evaluate_render()


func _evaluate_render() -> void:
	var tex = null
	if _webview != null:
		tex = _webview.get("texture")
	if tex == null:
		_show_placeholder_diagnostic()
		return
	print("[GodotCodely] ✅ CefTexture 渲染成功，dsh web 已内嵌")


func _show_placeholder_diagnostic() -> void:
	if _webview != null and _webview.get_parent() == self:
		remove_child(_webview)
		_webview.queue_free()
		_webview = null
	var vbox := VBoxContainer.new()
	vbox.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var lbl := Label.new()
	lbl.text = "警告：dsh web 内嵌失败。\n\n根因：godot-cef 的 CefTexture 在本机 Godot 4.7.1 下只注册了占位类（instantiate 出的是 placeholder instance，on_ready 无法调用、纹理永不生成）。\n这是 godot-cef v1.15.3 原生二进制与 Godot 4.7.1 的 GDExtension 兼容问题，并非本面板代码问题。\n\n可行方向：①用 Rust 从源码重新编译 godot-cef 对齐 4.7.1；②把工程降到 godot-cef 明确支持的 Godot 版本（4.5/4.6）；③换一个确认支持 4.7 的 webview 扩展。"
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(lbl)
	var btn := Button.new()
	btn.text = "在默认浏览器打开 dsh web (3080)"
	btn.pressed.connect(func(): OS.shell_open(DSH_WEB_URL))
	vbox.add_child(btn)
	add_child(vbox)
	print("[GodotCodely] 已切换为诊断+兜底模式：godot-cef 与 4.7.1 不兼容，请用浏览器打开 dsh web")


func _on_load_finished(url: String, status: int) -> void:
	_load_finished_fired = true
	print("[GodotCodely] load_finished url=%s status=%s" % [url, str(status)])


func _probe_webview(t: float) -> void:
	var u = _webview.get("url")
	var tex = _webview.get("texture")
	var sz = _webview.size if _webview is Control else Vector2.ZERO
	print("[GodotCodely] probe@%ss class=%s url=%s texture_set=%s load_finished=%s size=%s" % [
		str(t), _webview.get_class(), str(u), str(tex != null), str(_load_finished_fired), str(sz)])


var _hb := 0.0
func _process(delta: float) -> void:
	_hb += delta
	if _hb >= 3.0:
		_hb = 0.0
		var tex = null
		if _webview != null:
			tex = _webview.get("texture")
		print("[GodotCodely] heartbeat: process_ticking=true webview=%s texture_set=%s" % [
			str(_webview != null), str(tex != null)])


func _fallback_open_button() -> void:
	var btn := Button.new()
	btn.text = "打开 dsh web (3080)"
	btn.pressed.connect(func(): OS.shell_open(DSH_WEB_URL))
	add_child(btn)
	print("[GodotCodely] 已挂载 fallback：点击在默认浏览器打开 dsh web")


func _show_diagnostic_placeholder() -> void:
	var lbl := Label.new()
	lbl.text = "WEBVIEW 已禁用（诊断模式 · DISABLE_WEBVIEW=true）。\n\n此时 Dock 内没有任何 CefTexture / CEF 进程 / 每帧渲染循环。\n请拖一下本 Dock 顶部的「Codely」标题栏：\n  · 能拖 → CEF 内容或主线程循环是元凶，走降负载方向；\n  · 仍不能拖 → 控件存在即干扰（与 CEF 无关），走 mouse_filter 方向。"
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(lbl)
	print("[GodotCodely] DISABLE_WEBVIEW=true：已跳过 webview 装配，仅显示诊断占位（用于隔离 dock 拖拽问题）")
