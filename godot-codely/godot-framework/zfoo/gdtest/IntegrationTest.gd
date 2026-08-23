## Runs test scenes one by one. Each scene must emit gdf.events.test_passed when finished.
extends Node
class_name IntegrationTest

static var is_integration_test: bool = false

# Include files in subfolders
@export var include_subfolders: bool = false

@export var enable_test_logging: bool = true

var error_occurred: bool = false
var test_scenes: Array[String] = []


func _ready() -> void:
	if is_integration_test:
		return
	is_integration_test = true
	gdf.events.log_error.connect(func() -> void: error_occurred = true)
	gdf.events.test_passed.connect(on_integration_test_passed)
	scan_test_scenes()
	gdf.callable_deferred(next_integration_test)
	pass


func _process(_delta: float) -> void:
	if !error_occurred:
		return
	var scene_path := test_scenes[0] if !test_scenes.is_empty() else ""
	Log.error("❌ FAIL | IntegrationTest | scene:[{}]", scene_path)
	gdf.quit(1)
	pass


func scan_test_scenes() -> void:
	var current_scene_path := NodeUtils.scene_file_path_from_node(self)
	var scan_path := current_scene_path.get_base_dir()
	var files: Array[String] = FileUtils.get_all_files_in_folder(scan_path, include_subfolders)
	for file in files:
		if !file.ends_with(".tscn"):
			continue
		var scene_name := file.get_file().get_basename().to_lower()
		if !(scene_name.begins_with("test") || scene_name.ends_with("test")):
			continue
		if file == current_scene_path:
			continue
		test_scenes.push_back(file)
	if enable_test_logging:
		Log.info("🔎 SCAN | IntegrationTest | scenes:[{}] | scan_path:[{}]", test_scenes.size(), scan_path)
	pass


func on_integration_test_passed() -> void:
	test_scenes.pop_front()
	next_integration_test()
	pass


func next_integration_test() -> void:
	for child in get_children():
		remove_child(child)
		child.free()
	if test_scenes.is_empty():
		Log.info("🎉 DONE | IntegrationTest")
		gdf.quit()
		return
	var scene_path := test_scenes[0]
	Log.info("🧪 TEST | IntegrationTest | remaining:[{}] | scene:[{}]", test_scenes.size() - 1, scene_path)
	var packed := load(scene_path) as PackedScene
	if packed == null:
		Log.error("❌ FAIL | IntegrationTest | scene:[{}]", scene_path)
		await gdf.quit(1)
		return
	add_child(packed.instantiate())
	pass
