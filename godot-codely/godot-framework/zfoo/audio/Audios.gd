class_name Audios
extends Object

# Multi-channel audio: a pool of AudioStreamPlayers that can play multiple sounds concurrently.

const COUNT: int = 8
const SFX_BUS_NAME: String = "SoundEffect"

static var audios: Array[AudioStreamPlayer] = []

static func init() -> void:
	AudioServer.add_bus()
	var bus_index := AudioServer.get_bus_count() - 1
	AudioServer.set_bus_name(bus_index, SFX_BUS_NAME)

	var sfx_node := Node.new()
	sfx_node.name = SFX_BUS_NAME
	gdf.gdf_node.add_child(sfx_node)
	for i in range(COUNT):
		var player := AudioStreamPlayer.new()
		player.name = StringUtils.format("sfx_{}", i)
		player.bus = SFX_BUS_NAME
		player.finished.connect(func() -> void: player.stream = null)
		sfx_node.add_child(player)
		audios.append(player)
	pass

static func set_bus_volume_linear(volume_linear: float) -> void:
	AudioServer.set_bus_volume_linear(AudioServer.get_bus_index(SFX_BUS_NAME), clampf(volume_linear, 0.0, 1.0))
	pass

static func play(path: String, volume_linear: float = 1.0) -> void:
	var resource := await ResourceHelper.async_load(path) as AudioStream
	if resource == null:
		return
	var player_index := audios.find_custom(func(audio: AudioStreamPlayer) -> bool: return !audio.playing)
	var player: AudioStreamPlayer
	if player_index >= 0:
		player = audios[player_index]
	else:
		# All channels busy: preempt a random one so the new SFX still plays.
		player = RandomUtils.random_ele(audios)
		player.stop()
		player.stream = null
	player.volume_linear = clampf(volume_linear, 0.0, 1.0)
	player.stream = resource
	player.play()
	pass

static func play_sfx(sfx: SoundEffect) -> void:
	play(sfx.path, sfx.volume_linear)
	pass

static func stop_all() -> void:
	for player in audios:
		player.stop()
		player.stream = null
	pass
