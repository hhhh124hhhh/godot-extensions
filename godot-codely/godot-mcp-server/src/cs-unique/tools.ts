// [sovereign] coding-solo 独有工具的 MCP 定义 + 分发。
//
// 这 4 个工具是 coding-solo 相对 better 真正独有的能力：
//  - list_projects      纯目录扫描，无 Godot 依赖
//  - export_mesh_library / get_uid / update_project_uids  依赖 godot_operations.gd 进程
//
// 其余 coding-solo 工具被 better 的 17 复合工具（文件解析路线）覆盖，已从主权仓删除。

import { existsSync, readdirSync, statSync } from 'fs'
import { join, basename } from 'path'
import { runGodotOp } from './run-godot-op.js'

/**
 * 主权上下文：由 sovereign index.ts 在 registerTools 时注入，
 * 提供 Godot 路径、脚本路径、image-gen key、工程路径。
 */
export interface SovereignCtx {
  godotPath: string | null
  scriptPath: string
  volcArkApiKey: string
  godotProjectPath: string
}

export interface McpTextResult {
  content: Array<{ type: 'text'; text: string }>
  isError?: boolean
}

function textResult(text: string, isError = false): McpTextResult {
  return { content: [{ type: 'text', text }], isError }
}

// coding-solo 的 executeOperation 会把 camelCase 参数转 snake_case 再传给 .gd，
// .gd 中的 func 读取 params["scene_path"] / params["file_path"] / params["project_path"]。
function toSnakeCase(obj: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(obj)) {
    const snake = k.replace(/[A-Z]/g, (m) => '_' + m.toLowerCase())
    out[snake] = v
  }
  return out
}

function findGodotProjects(
  directory: string,
  recursive: boolean,
): Array<{ path: string; name: string }> {
  const projects: Array<{ path: string; name: string }> = []

  if (existsSync(join(directory, 'project.godot'))) {
    projects.push({ path: directory, name: basename(directory) })
  }

  // 字符串扫描（readdirSync 无 withFileTypes），规避 Dirent<T> 在不同 @types/node 下的泛型差异
  let names: string[]
  try {
    names = readdirSync(directory)
  } catch {
    return projects
  }

  const dirs: string[] = []
  for (const name of names) {
    if (name.startsWith('.')) continue
    try {
      if (statSync(join(directory, name)).isDirectory()) dirs.push(name)
    } catch {
      // ignore unreadable entry
    }
  }

  if (!recursive) {
    for (const name of dirs) {
      const sub = join(directory, name)
      if (existsSync(join(sub, 'project.godot'))) {
        projects.push({ path: sub, name })
      }
    }
  } else {
    for (const name of dirs) {
      const sub = join(directory, name)
      if (existsSync(join(sub, 'project.godot'))) {
        projects.push({ path: sub, name })
      } else {
        projects.push(...findGodotProjects(sub, true))
      }
    }
  }

  return projects
}

export const CS_UNIQUE_TOOLS = [
  {
    name: 'list_projects',
    description: [
      'Scan a directory for Godot projects (those containing a project.godot file).',
      '',
      'Actions (required -> optional):',
      '- list (directory -> recursive=false): list Godot projects under the directory',
    ].join('\n'),
    inputSchema: {
      type: 'object',
      properties: {
        action: { type: 'string', enum: ['list'], description: 'Action to perform' },
        directory: { type: 'string', description: 'Directory to scan for Godot projects' },
        recursive: { type: 'boolean', description: 'Recurse into subdirectories (default: false)' },
      },
      required: ['action', 'directory'],
    },
  },
  {
    name: 'export_mesh_library',
    description:
      '[godot-process] Export a MeshLibrary .tres from a scene via Godot. Requires Godot binary (GODOT_PATH).',
    inputSchema: {
      type: 'object',
      properties: {
        project_path: { type: 'string', description: 'Godot project directory' },
        scene_path: { type: 'string', description: 'Scene path relative to project (e.g. "scenes/main.tscn")' },
        output_path: { type: 'string', description: 'Output .tres path relative to project (e.g. "models/lib.tres")' },
      },
      required: ['project_path', 'scene_path', 'output_path'],
    },
  },
  {
    name: 'get_uid',
    description:
      '[godot-process] Read the UID of a resource file (.uid). Requires Godot binary (GODOT_PATH).',
    inputSchema: {
      type: 'object',
      properties: {
        project_path: { type: 'string', description: 'Godot project directory' },
        file_path: { type: 'string', description: 'Resource path relative to project (e.g. "scenes/main.tscn")' },
      },
      required: ['project_path', 'file_path'],
    },
  },
  {
    name: 'update_project_uids',
    description:
      '[godot-process] Regenerate/repair resource UIDs across the project (resave_resources). Requires Godot binary (GODOT_PATH).',
    inputSchema: {
      type: 'object',
      properties: {
        project_path: { type: 'string', description: 'Godot project directory' },
      },
      required: ['project_path'],
    },
  },
]

export async function dispatchCsUnique(
  name: string,
  args: Record<string, unknown>,
  ctx: SovereignCtx,
): Promise<McpTextResult> {
  switch (name) {
    case 'list_projects': {
      const directory = args.directory as string
      if (!directory) return textResult('directory is required', true)
      if (!existsSync(directory)) return textResult(`Directory does not exist: ${directory}`, true)
      const recursive = args.recursive === true
      const projects = findGodotProjects(directory, recursive)
      return textResult(JSON.stringify(projects, null, 2))
    }

    case 'export_mesh_library': {
      const projectPath = args.project_path as string
      const params = toSnakeCase({
        scenePath: args.scene_path,
        outputPath: args.output_path,
      })
      const { stdout } = await runGodotOp(ctx.godotPath, ctx.scriptPath, projectPath, 'export_mesh_library', params)
      return textResult(stdout)
    }

    case 'get_uid': {
      const projectPath = args.project_path as string
      const params = toSnakeCase({ filePath: args.file_path })
      const { stdout } = await runGodotOp(ctx.godotPath, ctx.scriptPath, projectPath, 'get_uid', params)
      return textResult(stdout)
    }

    case 'update_project_uids': {
      const projectPath = args.project_path as string
      const params = toSnakeCase({ projectPath })
      const { stdout } = await runGodotOp(ctx.godotPath, ctx.scriptPath, projectPath, 'resave_resources', params)
      return textResult(stdout)
    }

    default:
      return textResult(`Unknown cs-unique tool: ${name}`, true)
  }
}
