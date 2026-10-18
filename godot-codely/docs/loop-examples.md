# 工具清单与 Loop 示例（按需加载）

不确定参数时先 `mcp__godot__help`，不要靠记忆猜。验证档见 [methodology-2.0.md](methodology-2.0.md)：结构编辑停在 `scenes.info`（或一次具体读回）；只有行为需要引擎时才 `project.run` 一次；失败修一次然后停。

## 工具（前缀 `mcp__godot__`，23 个）

每个复合工具用 `action` 区分子动作（如 `nodes` 的 `action=add`）。

- **project**：info / version / run / stop / settings_get / settings_set / export
- **scenes**：create / list / info / delete / duplicate / set_main
- **nodes**：add / remove / rename / list / set_property / get_property
- **scripts**：create / read / write / attach / list / delete
- **editor**：launch / status
- **config**：status / set / detect_godot / check
- **resources**：list / info / delete / import_config
- **input_map**：list / add_action / remove_action / add_event
- **signals**：list / connect / disconnect
- **animation**：create_player / add_animation / add_track / add_keyframe / list
- **tilemap**：create_tileset / add_source / set_tile / paint / list
- **shader**：create / read / write / get_params / list
- **physics**：layers / collision_setup / body_config / set_layer_name
- **audio**：list_buses / add_bus / add_effect / create_stream
- **navigation**：create_region / add_agent / add_obstacle
- **ui**：create_control / set_theme / layout / list_controls
- **help**：任意工具的完整参数文档
- **list_projects**：纯目录扫描列出本机 Godot 工程（无需 Godot 二进制）
- **export_mesh_library / get_uid / update_project_uids**：Godot 进程驱动的资源工具
- **generate_sprite / generate_image**：Volcengine 文生图 → 写 assets/（需 `VOLC_ARK_API_KEY`）

看结构：`scenes.list` / `scenes.info` / `nodes.list` / `nodes.get_property`。
改工程：`nodes.add` / `nodes.set_property` / `scripts.create` / `scripts.write` / `scripts.attach`。
运行（仅行为需要引擎时）：`project.run` / `project.stop`。
编辑器与导出：`editor.launch` / `project.export`（需 `GODOT_PATH`）。

可选视觉核对（dsh-vision-toolkit，不在默认验证档里；用户要求对画面时再用）：`vision_html_screenshot`、`vision_pixel_diff`、`vision_describe`、`vision_crop`、`vision_ocr`、`vision_colors`。结构编辑不要为了截图去跑游戏。

## 示例 1：新建场景并添加主角

目标：创建 `scenes/game.tscn`，添加 CharacterBody2D 主角 + 碰撞体。结构交付停在 `scenes.info`。只有要看移动手感时才加一次 `project.run`。

```
Step 1: scenes(action="create", scene_path="scenes/game.tscn", root_type="Node2D", root_name="Game")
Step 2: nodes(action="add", scene_path="scenes/game.tscn", name="Player", type="CharacterBody2D", parent=".")
Step 3: nodes(action="add", scene_path="scenes/game.tscn", name="HitBox", type="CollisionShape2D", parent="Player")
Step 4: scripts(action="create", script_path="scripts/player.gd", extends="CharacterBody2D", content="...")
Step 5: scripts(action="attach", script_path="scripts/player.gd", scene_path="scenes/game.tscn", node_name="Player")
Step 6: scenes(action="info", scene_path="scenes/game.tscn")
        → 结构档到此停止
Step 7（仅当要验证移动）: project(action="run") 一次；失败则只修报错行再停
```

## 示例 2：修改已有节点属性

目标：修改 Player 的碰撞层。这是结构/属性编辑，不要 `project.run`。

```
Step 1: nodes(action="list", scene_path="scenes/game.tscn")
Step 2: physics(action="body_config", scene_path="scenes/game.tscn", name="Player", collision_layer=2, collision_mask=1)
Step 3: nodes(action="get_property", scene_path="scenes/game.tscn", name="Player", property="collision_layer")
```

## 示例 3：添加 UI 界面

目标：给 MainUI 场景添加分数标签。停在 `scenes.info`。

```
Step 1: scenes(action="info", scene_path="scenes/main_ui.tscn")
Step 2: ui(action="create_control", scene_path="scenes/main_ui.tscn", name="ScoreLabel", type="Label", parent=".")
Step 3: nodes(action="set_property", scene_path="scenes/main_ui.tscn", name="ScoreLabel", property="text", value="Score: 0")
Step 4: nodes(action="set_property", scene_path="scenes/main_ui.tscn", name="ScoreLabel", property="theme_override_font_sizes/font_size", value="24")
Step 5: scenes(action="info", scene_path="scenes/main_ui.tscn")
```

## 示例 4：报错修复闭环

场景：`project(action="run")` 后控制台报 `Invalid call. Nonexistent function 'move_and_slide' on base: 'Node2D'`。行为已经需要引擎，所以用一次 `project.run` 复查，然后停。

```
Step 1: scripts(action="read", script_path="scripts/player.gd")
Step 2: 定位 → 节点类型是 Node2D 而非 CharacterBody2D，所以没有 move_and_slide()
Step 3: 只改 extends / 出错的那一行，不重写整个脚本
Step 4: project(action="run") 一次
        → 仍失败则停，把文件/行和残留风险交回，不连环重跑
```

## 示例 5：工程切换

用户说「切到另一个工程」。这是配置，不是玩法验证。

```
Step 1: config(action="status")
Step 2: list_projects(directory="<当前工作目录>", recursive=true)
Step 3: config(action="set", key="project_path", value="<工程路径>")
Step 4: config(action="status")
```

给了明确路径就跳过 Step 2。

## 示例 6：信号连接

结构编辑。`signals.list` 复核后停。

```
Step 1: nodes(action="list", scene_path="scenes/game.tscn")
Step 2: signals(action="connect", scene_path="scenes/game.tscn", signal="pressed", from="UI/StartButton", to="Player", method="on_button_pressed")
Step 3: signals(action="list", scene_path="scenes/game.tscn")
```

## 示例 7：输入映射

目标：添加 `jump`，绑定空格键。`input_map list` 复核后停。

```
Step 1: input_map(action="list")
Step 2: input_map(action="add_action", action_name="jump", deadzone=0.5)
Step 3: input_map(action="add_event", action_name="jump", event_type="key", event_value="KEY_SPACE")
Step 4: input_map(action="list")
```
