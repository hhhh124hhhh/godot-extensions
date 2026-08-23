class_name Error
const PROTOCOL_ID: int = 101

var code: int
var message: String

static func write(buffer: ByteBuffer, packet: Error):
	if (packet == null):
		buffer.writeInt(0)
		return
	buffer.writeInt(-1)
	buffer.writeInt(packet.code)
	buffer.writeString(packet.message)
	pass

static func read(buffer: ByteBuffer) -> Error:
	var length = buffer.readInt()
	if (length == 0):
		return null
	var beforeReadIndex = buffer.getReadOffset()
	var packet: Error = Error.new()
	var result0 = buffer.readInt()
	packet.code = result0
	var result1 = buffer.readString()
	packet.message = result1
	if (length > 0):
		buffer.setReadOffset(beforeReadIndex + length)
	return packet