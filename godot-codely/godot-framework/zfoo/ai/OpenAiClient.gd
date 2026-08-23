class_name OpenAiClient
extends Object

## Local-dev only. Replace with a backend proxy before shipping.
## Reads from env OPENAI_API_KEY by default; can still override at runtime.
const API_KEY_ENV := "OPENAI_API_KEY"
static var api_key: String = OS.get_environment(API_KEY_ENV)
static var base_url: String = "https://api.deepseek.com/chat/completions"
static var model: String = "deepseek-v4-flash"


static func async_chat(prompt: String, system_prompt: String = "") -> String:
	var messages: Array[ChatMessage] = []
	if not StringUtils.is_blank(system_prompt):
		messages.append(ChatMessage.new(ChatMessage.ROLE_SYSTEM, system_prompt))
	messages.append(ChatMessage.new(ChatMessage.ROLE_USER, prompt))
	return await async_chat_messages(messages)


static func async_chat_messages(messages: Array[ChatMessage]) -> String:
	if StringUtils.is_blank(api_key):
		Log.error("OpenAI api_key is empty, set env {}", API_KEY_ENV)
		return StringUtils.EMPTY
	if messages.is_empty():
		Log.error("OpenAI messages is empty")
		return StringUtils.EMPTY
	var request := OpenAiRequest.new(model, messages, false)

	var headers := PackedStringArray([
		StringUtils.format("Authorization: Bearer {}", api_key),
	])
	var response := await HttpHelper.async_post(base_url, JsonUtils.object_to_json(request), headers)
	var body := response.get_body_string()
	Log.info("OpenAI response body:[{}]", StringUtils.truncate(body, 512))
	if not response.success or response.code != 200:
		Log.error("OpenAI request failed code:[{}] body:[{}]", response.code, StringUtils.truncate(body, 512))
		return StringUtils.EMPTY

	var chat_response: OpenAiResponse = JsonUtils.json_to_object(body, OpenAiResponse)
	if chat_response == null or chat_response.choices.is_empty():
		Log.error("OpenAI response parse failed body:[{}]", StringUtils.truncate(body, 512))
		return StringUtils.EMPTY

	var message := chat_response.choices[0].message
	if message == null or StringUtils.is_blank(message.content):
		Log.error("OpenAI response missing content body:[{}]", StringUtils.truncate(body, 512))
		return StringUtils.EMPTY
	return message.content
