/**
 * Framework tools - godot-framework (zfoo/) integration
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { GodotMCPError } from '../helpers/errors.js';
import { resolveProjectRoot } from '../helpers/paths.js';
import type { GodotConfig } from '../../godot/types.js';
const ZFOO_DIR = 'zfoo';
const AUTOLOAD_NAME = 'GodotFramework';
const AUTOLOAD_PATH = 'res://zfoo/GodotFramework.tscn';
async function handleCheck(projectPath: string): Promise<string> {
  const zfooPath = path.join(projectPath, ZFOO_DIR);
  const projectGodotPath = path.join(projectPath, 'project.godot');
  const results: string[] = [];
  if (!fs.existsSync(zfooPath)) {
    results.push('zfoo/ directory not found at: ' + zfooPath);
    results.push('');
    results.push('To integrate godot-framework:');
    results.push('1. Copy zfoo/ from godot-codely/godot-framework/zfoo/ to your project root');
    results.push('2. Run framework(action=\"bootstrap\")');
    return results.join('\n');
  }
  results.push('zfoo/ directory found at: ' + zfooPath);
  const modules: string[] = [];
  try {
    const entries = fs.readdirSync(zfooPath, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.isDirectory() && !entry.name.startsWith('.')) modules.push(entry.name);
    }
  } catch { /* ignore */ }
  if (modules.length > 0) results.push('   Modules: ' + modules.join(', '));
  if (fs.existsSync(projectGodotPath)) {
    const content = fs.readFileSync(projectGodotPath, 'utf-8');
    const hasAutoload = content.includes(AUTOLOAD_NAME) && content.includes(AUTOLOAD_PATH);
    if (hasAutoload) results.push('Autoload registered: ' + AUTOLOAD_NAME + ' = ' + AUTOLOAD_PATH);
    else { results.push('Autoload NOT registered. Add to project.godot [autoload]:'); results.push('   ' + AUTOLOAD_NAME + '=\"*' + AUTOLOAD_PATH + '\"'); }
  } else results.push('project.godot not found at: ' + projectGodotPath);
  return results.join('\n');
}
async function handleBootstrap(projectPath: string, frameworkSourcePath: string): Promise<string> {
  const zfooSrc = path.join(frameworkSourcePath, ZFOO_DIR);
  const zfooDst = path.join(projectPath, ZFOO_DIR);
  const projectGodotPath = path.join(projectPath, 'project.godot');
  const results: string[] = [];
  if (!fs.existsSync(zfooSrc)) {
    throw new GodotMCPError('Framework source not found: ' + zfooSrc, 'INVALID_ACTION', 'Make sure godot-framework is included in the godot-codely plugin directory.');
  }
  if (fs.existsSync(zfooDst)) {
    results.push('zfoo/ already exists at: ' + zfooDst + ' (skipping copy)');
  } else {
    copyDirRecursive(zfooSrc, zfooDst);
    results.push('Copied zfoo/ to: ' + zfooDst);
  }
  if (fs.existsSync(projectGodotPath)) {
    let content = fs.readFileSync(projectGodotPath, 'utf-8');
    if (content.includes(AUTOLOAD_NAME)) {
      results.push('Autoload ' + AUTOLOAD_NAME + ' already registered (skipping)');
    } else {
      const autoloadSection = '[autoload]';
      if (!content.includes(autoloadSection)) content += '\n' + autoloadSection + '\n';
      const autoloadEntry = AUTOLOAD_NAME + '=\"*' + AUTOLOAD_PATH + '\"';
      content = content.replace(new RegExp('(\\[autoload\\]\\n?)'), '' + autoloadEntry + '\n');
      fs.writeFileSync(projectGodotPath, content, 'utf-8');
      results.push('Registered Autoload: ' + autoloadEntry);
    }
  } else {
    results.push('project.godot not found, Autoload not registered');
    results.push('   Manually add: ' + AUTOLOAD_NAME + '=\"*' + AUTOLOAD_PATH + '\"');
  }
  results.push('');
  results.push('Done! In Godot Editor: Project > Project Settings > Autoload to verify.');
  return results.join('\n');
}
function copyDirRecursive(src: string, dst: string): void {
  fs.mkdirSync(dst, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const dstPath = path.join(dst, entry.name);
    if (entry.isDirectory()) copyDirRecursive(srcPath, dstPath);
    else fs.copyFileSync(srcPath, dstPath);
  }
}
export async function handleFramework(
  action: string,
  args: Record<string, unknown>,
  config: GodotConfig,
): Promise<{ content: Array<{ type: string; text: string }> }> {
  const projectPath = resolveProjectRoot(args.project_path as string | undefined, config.projectPath);
  switch (action) {
    case 'check':
      return { content: [{ type: 'text', text: await handleCheck(projectPath) }] };
    case 'bootstrap': {
      const fsp = args.framework_source_path as string | undefined;
      if (!fsp) throw new GodotMCPError('framework_source_path is required for bootstrap', 'INVALID_ACTION', 'Provide the path to the godot-framework directory.');
      return { content: [{ type: 'text', text: await handleBootstrap(projectPath, fsp) }] };
    }
    default:
      throw new GodotMCPError('Unknown framework action: ' + action, 'INVALID_ACTION', 'Valid actions: check, bootstrap');
  }
}
