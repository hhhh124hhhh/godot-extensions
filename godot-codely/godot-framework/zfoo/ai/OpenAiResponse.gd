class_name OpenAiResponse
extends RefCounted


class Choice:
	var index: int = 0
	var message: ChatMessage = ChatMessage.new()
	var finish_reason: String = ""
	pass


var id: String = ""
var model: String = ""
var choices: Array[Choice] = []
