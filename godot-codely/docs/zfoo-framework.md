# godot-framework / zfoo（按需加载）

本项目整合了 [godot-fun/godot-framework](https://github.com/godot-fun/godot-framework) 的运行时框架。框架以 Autoload 方式加载（`GodotFramework.tscn` → 全局类名 `gdf`）。**仅当目标工程已经接了这套框架时**，写 GDScript 优先用框架 API，不要手写等价逻辑。工程里没有 `zfoo/` 或 `GodotFramework` 时，按工程现有写法，不要为了用表而加依赖。

| 场景 | 框架 API | 禁止手写 |
|------|----------|----------|
| 播放音乐 | `Audio.play_music("res://audio/bgm.mp3")` | 不要手写 AudioStreamPlayer 节点 |
| 播放音效 | `Audios.play("res://audio/click.mp3", 0.8)` | 不要手写 AudioStreamPlayer2D |
| 场景切换 | `await SceneHelper.async_change_scene_to_file("res://scene/Main.tscn")` | 不要手写 `get_tree().change_scene_to_file()` |
| 异步加载资源 | `await ResourceHelper.async_load("res://assets/icon.svg")` | 不要用 `load()` 阻塞主线程 |
| 日志 | `Log.info("msg:[{}]", val)` / `Log.error(...)` | 不要用 `print()` / `push_error()` |
| 持久化配置 | `Setting.get_bool("key", false)` / `Setting.set_string("key", "val")` + `Setting.save()` | 不要手写 ConfigFile |
| 定时任务 | `SchedulerBus.schedule(func(): do_something(), 1000)` | 不要用 Timer 节点 |
| HTTP 请求 | `await HttpHelper.async_get("https://...")` | 不要手写 HTTPRequest 节点 |
| 主线程回调 | `gdf.callable_deferred(func(): refresh_ui())` | 不要用 `call_deferred` 字符串形式 |
| 安全退出 | `await gdf.quit()` | 不要用 `get_tree().quit()` |
| 精灵表动画 | `EffectAnimation2D.spawn(pos, parent, "res://effects/attack.png", Vector2i(4,4), 0.5, 13)` | 不要手写 AnimatedSprite2D |
| Toast 提示 | `Alert.alert("Saved", Colors.success)` | 不要手写 Label + Tween |

框架 Autoload 注册方式（项目集成时）：

Project → Project Settings → Autoload → GodotFramework (`res://zfoo/GodotFramework.tscn`)

改完仍按 [methodology-2.0.md](methodology-2.0.md) 的分层验证：结构编辑用 `scenes.info` / `scripts.read`；只有运行时行为才 `project.run` 一次。
