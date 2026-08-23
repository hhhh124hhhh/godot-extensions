class_name NodeUtils
extends Object




static func scene_file_path_from_node(node: Node) -> String:
	var current_scene_path := node.scene_file_path
	if StringUtils.is_blank(current_scene_path):
		current_scene_path = node.get_tree().current_scene.scene_file_path
	return current_scene_path


static func load_and_instantiate(path: String) -> Node:
	var packed := load(path) as PackedScene
	if packed == null:
		Log.error("load and instantiate failed path:[{}]", path)
		return null
	return packed.instantiate()
