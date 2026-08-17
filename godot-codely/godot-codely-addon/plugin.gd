## Godot Codely — EditorPlugin 入口
## 把 codely_panel(内嵌 dsh web 的面板) 挂到编辑器右侧 Dock。
## 形态同 cocos-codely：cocos 用 <iframe> 嵌 dsh web，godot 用 webview GDExtension 嵌 dsh web。
@tool
extends EditorPlugin

const CodelyPanel = preload("res://addons/godot-codely/codely_panel.gd")

var _panel = null


func _enter_tree() -> void:
	print("[GodotCodely] 开始加载插件...")

	_panel = CodelyPanel.new()
	_panel.name = "Codely"
	if _panel.has_method("set_editor_interface"):
		_panel.set_editor_interface(get_editor_interface())
	print("[GodotCodely] 面板已实例化")

	# 挂到右侧 Dock（和 Inspector 同侧下方）
	add_control_to_dock(DOCK_SLOT_RIGHT_BL, _panel)
	print("[GodotCodely] ✅ 已添加到右侧 Dock (dsh web 面板)")


func _exit_tree() -> void:
	print("[GodotCodely] 开始卸载插件...")
	if _panel:
		remove_control_from_docks(_panel)
		_panel.queue_free()
		_panel = null
		print("[GodotCodely] ✅ 插件已卸载")
	else:
		print("[GodotCodely] 没有面板需要卸载")
