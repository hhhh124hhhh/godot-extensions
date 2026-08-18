#!/usr/bin/env node
/**
 * godot-mcp-server —— Godot MCP 主权聚合器（真·去重合并版）
 *
 * 设计（单一 McpServer / 单一注册 / 无前缀 / 统一 SDK ^1.30.0）：
 *  - 主干：better-godot-mcp 的 17 复合工具（纯文件解析路线，不需 Godot 二进制在场）
 *  - 补 coding-solo 独有工具：list_projects + export_mesh_library / get_uid / update_project_uids
 *  - 原生 image-gen：generate_sprite / generate_image（火山方舟文生图，移植自 cocos-mcp-bridge）
 *  - 已删除：coding-solo 冗余 10 工具 + Plan B 子进程代理（spawnUpstream / cs__ / better__ 前缀）
 *
 * 传输：stdio（默认）或 http 单端点（MCP_TRANSPORT=http）。
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import http from 'http'
import path from 'path'
import fs from 'fs'
import { randomUUID } from 'crypto'
import { fileURLToPath } from 'url'
import { detectGodot } from './better/src/godot/detector.js'
import type { GodotConfig } from './better/src/godot/types.js'
import { registerTools } from './better/src/tools/registry.js'
import type { SovereignCtx } from './cs-unique/tools.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

export interface GodotMcpConfig {
  host: string
  port: number
  godotPath: string
  godotProjectPath: string
  volcArkApiKey: string
}

function loadConfig(): GodotMcpConfig {
  const configPath = path.join(ROOT, 'godot-mcp-server.config.json')
  let fileConfig: any = {}
  if (fs.existsSync(configPath)) {
    try {
      fileConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'))
    } catch (_) {
      fileConfig = {}
    }
  }
  const num = (v: any, d: number) => (Number.isInteger(v) ? v : d)
  return {
    host: process.env.GODOT_MCP_HOST || fileConfig.host || '127.0.0.1',
    port: num(process.env.GODOT_MCP_PORT || fileConfig.port, 8785),
    godotPath: process.env.GODOT_PATH || fileConfig.godotPath || '',
    godotProjectPath: process.env.GODOT_PROJECT_PATH || fileConfig.godotProjectPath || process.cwd(),
    volcArkApiKey: process.env.VOLC_ARK_API_KEY || fileConfig.volcArkApiKey || '',
  }
}

const CONFIG = loadConfig()

function buildSovereignCtx(): SovereignCtx {
  return {
    godotPath: CONFIG.godotPath || null,
    scriptPath: path.join(ROOT, 'src', 'godot-scripts', 'godot_operations.gd'),
    volcArkApiKey: CONFIG.volcArkApiKey,
    godotProjectPath: CONFIG.godotProjectPath,
  }
}

async function main(): Promise<void> {
  // 检测 Godot 二进制（better 路线；无则仅文件解析类工具可用，godot 进程类工具需二进制）
  const detection = detectGodot()
  const godotPath = detection?.path ?? (CONFIG.godotPath || null)
  if (godotPath) {
    console.error(`[godot-mcp-server] Godot detected: ${godotPath}`)
  } else {
    console.error(
      '[godot-mcp-server] Godot 未检测到（GODOT_PATH 未设）。文件解析类工具可用；' +
        'godot 进程类工具（export_mesh_library/get_uid/update_project_uids）需 Godot 二进制。',
    )
  }

  const config: GodotConfig = {
    godotPath,
    godotVersion: detection?.version ?? null,
    projectPath: CONFIG.godotProjectPath,
    activePids: [],
  }

  const server = new Server(
    { name: 'godot-mcp-server', version: '2.0.0' },
    { capabilities: { tools: {} } },
  )

  // 单一注册：better 17 复合工具 + coding-solo 4 独有工具 + image-gen 2 原生工具（无前缀）
  registerTools(server, config, buildSovereignCtx())

  console.error('[godot-mcp-server] 工具注册完成（better 主干 + cs-unique + image-gen，单 Server 无前缀）')

  const transportType = process.env.MCP_TRANSPORT || 'stdio'

  if (transportType === 'http') {
    const httpServer = http.createServer()
    const transports = new Map<string, StreamableHTTPServerTransport>()

    httpServer.on('request', async (req, res) => {
      const sessionId = req.headers['mcp-session-id'] as string | undefined
      let transport: StreamableHTTPServerTransport | undefined
      if (sessionId && transports.has(sessionId)) {
        transport = transports.get(sessionId)
      } else if (!sessionId && req.headers['accept']?.includes('text/event-stream')) {
        // 新会话：为每次 initialize 创建独立 transport 并接入同一 Server
        transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: () => randomUUID(),
          onsessioninitialized: (sid) => {
            transports.set(sid, transport!)
          },
        })
        await server.connect(transport)
      } else {
        res.writeHead(400).end('Bad Request')
        return
      }
      if (transport) {
        await transport.handleRequest(req, res)
      } else {
        res.writeHead(404).end('Not Found')
      }
    })

    httpServer.listen(CONFIG.port, CONFIG.host, () => {
      console.error(`[godot-mcp-server] HTTP 端点已起: http://${CONFIG.host}:${CONFIG.port}/mcp`)
    })
  } else {
    const stdioTransport = new StdioServerTransport()
    await server.connect(stdioTransport)
    console.error('[godot-mcp-server] stdio 传输已连接')
  }
}

main().catch((e) => {
  console.error('[godot-mcp-server] 启动失败:', e)
  process.exit(1)
})
