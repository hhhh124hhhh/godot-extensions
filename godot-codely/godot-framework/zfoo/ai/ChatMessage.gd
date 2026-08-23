class_name ChatMessage
extends RefCounted

const ROLE_SYSTEM := "system"
const ROLE_USER := "user"
const ROLE_ASSISTANT := "assistant"

var role: String = ""
var content: String = ""


func _init(_role: String = "", _content: String = "") -> void:
	role = _role
	content = _content
	pass
