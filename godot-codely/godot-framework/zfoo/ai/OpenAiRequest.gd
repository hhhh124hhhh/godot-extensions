class_name OpenAiRequest
extends RefCounted

var model: String = ""
var messages: Array[ChatMessage] = []
var stream: bool = false


func _init(_model: String = "", _messages: Array[ChatMessage] = [], _stream: bool = false) -> void:
	model = _model
	messages = _messages
	stream = _stream
	pass
