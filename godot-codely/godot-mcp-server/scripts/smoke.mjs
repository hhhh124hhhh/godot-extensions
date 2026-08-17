// MCP stdio 冒烟：spawn 服务器，走 initialize + notifications/initialized + tools/list，
// 打印工具总数与名称，验证「单一 Server / 无前缀 / 17+4+2」。
// 用法：npm run build && npm run smoke（GODOT_MCP_ENTRY 可指定其他入口）
import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = __dirname
const ENTRY = process.env.GODOT_MCP_ENTRY || path.join(ROOT, '..', 'build', 'index.js')
const child = spawn('node', [ENTRY], { cwd: ROOT, stdio: ['pipe', 'pipe', 'pipe'] })

let buf = ''
child.stdout.on('data', (d) => { buf += d.toString() })
child.stderr.on('data', (d) => process.stderr.write('[server] ' + d.toString()))

let id = 0
const send = (method, params) =>
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: ++id, method, params }) + '\n')

send('initialize', {
  protocolVersion: '2025-06-18',
  capabilities: {},
  clientInfo: { name: 'smoke', version: '1.0' },
})
setTimeout(() => send('notifications/initialized', {}), 300)
setTimeout(() => send('tools/list', {}), 600)

setTimeout(() => {
  const msgs = buf
    .split('\n')
    .filter(Boolean)
    .map((l) => { try { return JSON.parse(l) } catch { return null } })
    .filter(Boolean)
  const list = msgs.find((m) => m.result && m.result.tools)
  if (!list || !list.result || !list.result.tools) {
    console.error('NO tools/list response. raw buf:\n' + buf.slice(0, 2000))
    child.kill()
    process.exit(1)
  }
  const tools = list.result.tools
  console.log('TOTAL_TOOLS=' + tools.length)
  const names = tools.map((t) => t.name).sort()
  console.log(names.join('\n'))
  const prefixed = names.filter((n) => n.startsWith('cs__') || n.startsWith('better__'))
  console.log('PREFIXED=' + prefixed.length)
  child.kill()
  process.exit(0)
}, 2000)
