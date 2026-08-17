/**
 * Coverage tests for scripts and scenes edge cases
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { GodotConfig } from '../../src/godot/types.js'
import { handleScenes } from '../../src/tools/composite/scenes.js'
import { handleScripts } from '../../src/tools/composite/scripts.js'
import { createTmpProject, createTmpScene, createTmpScript, MINIMAL_TSCN, makeConfig } from '../fixtures.js'

describe('scripts/scenes coverage', () => {
  let projectPath: string
  let cleanup: () => void
  let config: GodotConfig

  beforeEach(() => {
    const tmp = createTmpProject()
    projectPath = tmp.projectPath
    cleanup = tmp.cleanup
    config = makeConfig({ projectPath })
  })

  afterEach(() => cleanup())

  describe('scripts', () => {
    it('create: missing script_path', async () => {
      await expect(handleScripts('create', { project_path: projectPath }, config)).rejects.toThrow(
        'No script_path specified',
      )
    })
    it('create: script exists', async () => {
      createTmpScript(projectPath, 'e.gd')
      await expect(handleScripts('create', { project_path: projectPath, script_path: 'e.gd' }, config)).rejects.toThrow(
        'already exists',
      )
    })
    it('read: missing script_path', async () => {
      await expect(handleScripts('read', { project_path: projectPath }, config)).rejects.toThrow(
        'No script_path specified',
      )
    })
    it('read: not found', async () => {
      await expect(handleScripts('read', { project_path: projectPath, script_path: 'x.gd' }, config)).rejects.toThrow(
        'not found',
      )
    })
    it('write: missing script_path', async () => {
      await expect(handleScripts('write', { project_path: projectPath }, config)).rejects.toThrow(
        'No script_path specified',
      )
    })
    it('write: missing content', async () => {
      await expect(handleScripts('write', { project_path: projectPath, script_path: 'x.gd' }, config)).rejects.toThrow(
        'No content specified',
      )
    })
    it('attach: missing paths', async () => {
      await expect(handleScripts('attach', { project_path: projectPath }, config)).rejects.toThrow(
        'Both scene_path and script_path required',
      )
    })
    it('attach: scene not found', async () => {
      await expect(
        handleScripts('attach', { project_path: projectPath, scene_path: 'x.tscn', script_path: 'x.gd' }, config),
      ).rejects.toThrow('Scene not found')
    })
    it('attach: node not found', async () => {
      createTmpScene(projectPath, 't.tscn', MINIMAL_TSCN)
      await expect(
        handleScripts(
          'attach',
          { project_path: projectPath, scene_path: 't.tscn', script_path: 'x.gd', node_name: 'Ghost' },
          config,
        ),
      ).rejects.toThrow('Node "Ghost" not found')
    })
    it('list: missing project_path', async () => {
      await expect(handleScripts('list', {}, makeConfig())).rejects.toThrow('No project path specified')
    })
    it('delete: missing script_path', async () => {
      await expect(handleScripts('delete', { project_path: projectPath }, config)).rejects.toThrow(
        'No script_path specified',
      )
    })
    it('delete: not found', async () => {
      await expect(handleScripts('delete', { project_path: projectPath, script_path: 'x.gd' }, config)).rejects.toThrow(
        'not found',
      )
    })
    it('create: CharacterBody2D template', async () => {
      await handleScripts(
        'create',
        { project_path: projectPath, script_path: 'p.gd', extends: 'CharacterBody2D' },
        config,
      )
      expect(readFileSync(join(projectPath, 'p.gd'), 'utf-8')).toContain('_physics_process')
    })
    it('create: unknown extends', async () => {
      await handleScripts('create', { project_path: projectPath, script_path: 'c.gd', extends: 'CustomClass' }, config)
      expect(readFileSync(join(projectPath, 'c.gd'), 'utf-8')).toContain('extends CustomClass')
    })
  })

  describe('scenes', () => {
    it('duplicate: missing new_path', async () => {
      await expect(
        handleScenes('duplicate', { project_path: projectPath, scene_path: 'a.tscn' }, config),
      ).rejects.toThrow('Both scene_path and new_path required')
    })
    it('duplicate: source not found', async () => {
      await expect(
        handleScenes('duplicate', { project_path: projectPath, scene_path: 'x.tscn', new_path: 'y.tscn' }, config),
      ).rejects.toThrow('Source scene not found')
    })
    it('duplicate: dest exists', async () => {
      createTmpScene(projectPath, 's.tscn')
      createTmpScene(projectPath, 'd.tscn')
      await expect(
        handleScenes('duplicate', { project_path: projectPath, scene_path: 's.tscn', new_path: 'd.tscn' }, config),
      ).rejects.toThrow('Destination already exists')
    })
    it('set_main: no project.godot', async () => {
      await expect(
        handleScenes(
          'set_main',
          { project_path: '/tmp/nonexistent', scene_path: 'm.tscn' },
          makeConfig({ projectPath: '/tmp/nonexistent' }),
        ),
      ).rejects.toThrow('No project.godot found')
    })
    it('info: missing scene_path', async () => {
      await expect(handleScenes('info', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('info: not found', async () => {
      await expect(handleScenes('info', { project_path: projectPath, scene_path: 'x.tscn' }, config)).rejects.toThrow(
        'Scene not found',
      )
    })
    it('delete: missing scene_path', async () => {
      await expect(handleScenes('delete', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('delete: not found', async () => {
      await expect(handleScenes('delete', { project_path: projectPath, scene_path: 'x.tscn' }, config)).rejects.toThrow(
        'Scene not found',
      )
    })
    it('set_main: missing scene_path', async () => {
      await expect(handleScenes('set_main', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('create: missing project_path', async () => {
      await expect(handleScenes('create', { scene_path: 'x.tscn' }, makeConfig())).rejects.toThrow(
        'No project path specified',
      )
    })
    it('list: missing project_path', async () => {
      await expect(handleScenes('list', {}, makeConfig())).rejects.toThrow('No project path specified')
    })
    it('create: already exists', async () => {
      createTmpScene(projectPath, 'e.tscn')
      await expect(handleScenes('create', { project_path: projectPath, scene_path: 'e.tscn' }, config)).rejects.toThrow(
        'already exists',
      )
    })
  })
})
