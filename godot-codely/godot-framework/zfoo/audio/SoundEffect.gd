class_name SoundEffect
extends Object

var path: String
var volume_linear: float = 1.0

func _init(_path: String, _volume_linear: float = 1.0) -> void:
	path = _path
	volume_linear = _volume_linear
	pass
