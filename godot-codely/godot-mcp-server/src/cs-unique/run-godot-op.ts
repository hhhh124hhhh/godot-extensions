// [sovereign] coding-solo 独有工具的 Godot 进程运行器。
//
// coding-solo 的 export_mesh_library / get_uid / update_project_uids（后者在 .gd 中名为
// resave_resources）依赖 bundled godot_operations.gd 走 Godot 子进程完成。这里移植其
// executeOperation 机制：以 `--headless --path <project> --script <gd> <op> <json>` 拉起
// Godot，捕获 stdout（.gd 用 print 输出结果）/ stderr（printerr 报错）。
//
// 其余 coding-solo 工具（create_scene/add_node/load_sprite/save_scene/launch/run/stop…）
// 已被 better 的纯文件解析工具覆盖，不在此处移植。

import { execFile } from 'child_process'
import { promisify } from 'util'

const execFileAsync = promisify(execFile)

export interface RunGodotOpResult {
  stdout: string
  stderr: string
}

/**
 * 运行 bundled godot_operations.gd 的某一 operation。
 * @param godotPath 检测到的 Godot 可执行文件路径（无则报错）
 * @param scriptPath godot_operations.gd 的绝对路径
 * @param projectPath 工程目录（--path，res:// 基准）
 * @param operation .gd 中 match 的分支名
 * @param params 已转 snake_case 的参数对象（会被 JSON.stringify 成命令行参数）
 */
export async function runGodotOp(
  godotPath: string | null,
  scriptPath: string,
  projectPath: string,
  operation: string,
  params: Record<string, unknown>,
): Promise<RunGodotOpResult> {
  if (!godotPath) {
    throw new Error('未检测到 Godot 可执行文件，请设置 GODOT_PATH 环境变量后重试。')
  }

  const paramsJson = JSON.stringify(params)
  const args = [
    '--headless',
    '--path',
    projectPath,
    '--script',
    scriptPath,
    operation,
    paramsJson,
  ]

  try {
    const { stdout, stderr } = await execFileAsync(godotPath, args, {
      maxBuffer: 32 * 1024 * 1024,
    })
    return { stdout: stdout ?? '', stderr: stderr ?? '' }
  } catch (error: unknown) {
    // execFile 在非零退出码时仍会在 error 上挂 stdout/stderr
    if (error && typeof error === 'object' && 'stdout' in error && 'stderr' in error) {
      const e = error as { stdout: string; stderr: string }
      return { stdout: e.stdout ?? '', stderr: e.stderr ?? '' }
    }
    throw error
  }
}
