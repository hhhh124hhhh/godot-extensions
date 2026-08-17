/**
 * Coverage tests for ui, signals, animation, resources edge cases
 */

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { GodotConfig } from '../../src/godot/types.js'
import { handleAnimation } from '../../src/tools/composite/animation.js'
import { handleResources } from '../../src/tools/composite/resources.js'
import { handleSignals } from '../../src/tools/composite/signals.js'
import { handleUI } from '../../src/tools/composite/ui.js'
import { createTmpProject, createTmpScene, MINIMAL_TSCN, makeConfig } from '../fixtures.js'

describe('ui/signals/animation/resources coverage', () => {
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

  // ui
  describe('ui', () => {
    it('layout: bottom_wide', async () => {
      createTmpScene(projectPath, 'u.tscn', MINIMAL_TSCN)
      await handleUI(
        'layout',
        { project_path: projectPath, scene_path: 'u.tscn', name: 'Root', preset: 'bottom_wide' },
        config,
      )
      expect(readFileSync(join(projectPath, 'u.tscn'), 'utf-8')).toContain('anchors_preset = 12')
    })
    it('layout: left_wide', async () => {
      createTmpScene(projectPath, 'u.tscn', MINIMAL_TSCN)
      await handleUI(
        'layout',
        { project_path: projectPath, scene_path: 'u.tscn', name: 'Root', preset: 'left_wide' },
        config,
      )
      expect(readFileSync(join(projectPath, 'u.tscn'), 'utf-8')).toContain('anchors_preset = 9')
    })
    it('layout: right_wide', async () => {
      createTmpScene(projectPath, 'u.tscn', MINIMAL_TSCN)
      await handleUI(
        'layout',
        { project_path: projectPath, scene_path: 'u.tscn', name: 'Root', preset: 'right_wide' },
        config,
      )
      expect(readFileSync(join(projectPath, 'u.tscn'), 'utf-8')).toContain('anchors_preset = 11')
    })
    it('layout: invalid preset', async () => {
      createTmpScene(projectPath, 'u.tscn', MINIMAL_TSCN)
      await expect(
        handleUI('layout', { project_path: projectPath, scene_path: 'u.tscn', name: 'Root', preset: 'xxx' }, config),
      ).rejects.toThrow('Unknown layout preset')
    })
    it('create_control: missing scene_path', async () => {
      await expect(handleUI('create_control', { project_path: projectPath, name: 'B' }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('create_control: missing name', async () => {
      createTmpScene(projectPath, 'u.tscn', MINIMAL_TSCN)
      await expect(
        handleUI('create_control', { project_path: projectPath, scene_path: 'u.tscn' }, config),
      ).rejects.toThrow('No name specified')
    })
    it('layout: missing scene_path', async () => {
      await expect(handleUI('layout', { project_path: projectPath, name: 'R' }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('layout: missing name', async () => {
      createTmpScene(projectPath, 'u.tscn', MINIMAL_TSCN)
      await expect(handleUI('layout', { project_path: projectPath, scene_path: 'u.tscn' }, config)).rejects.toThrow(
        'No name specified',
      )
    })
    it('layout: node not found', async () => {
      createTmpScene(projectPath, 'u.tscn', MINIMAL_TSCN)
      await expect(
        handleUI('layout', { project_path: projectPath, scene_path: 'u.tscn', name: 'Ghost' }, config),
      ).rejects.toThrow('Node "Ghost" not found')
    })
    it('list_controls: missing scene_path', async () => {
      await expect(handleUI('list_controls', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('set_theme: missing theme_path', async () => {
      await expect(handleUI('set_theme', { project_path: projectPath }, config)).rejects.toThrow(
        'No theme_path specified',
      )
    })
    it('create_control: custom properties', async () => {
      createTmpScene(projectPath, 'u.tscn', MINIMAL_TSCN)
      await handleUI(
        'create_control',
        { project_path: projectPath, scene_path: 'u.tscn', name: 'B', type: 'Button', properties: { cp: '"v"' } },
        config,
      )
      expect(readFileSync(join(projectPath, 'u.tscn'), 'utf-8')).toContain('cp = "v"')
    })
  })

  // signals
  describe('signals', () => {
    it('list: scene not found', async () => {
      await expect(handleSignals('list', { project_path: projectPath, scene_path: 'x.tscn' }, config)).rejects.toThrow(
        'Scene not found',
      )
    })
    it('connect: scene not found', async () => {
      await expect(
        handleSignals(
          'connect',
          { project_path: projectPath, scene_path: 'x.tscn', signal: 's', from: 'a', to: 'b', method: 'm' },
          config,
        ),
      ).rejects.toThrow('Scene not found')
    })
    it('disconnect: scene not found', async () => {
      await expect(
        handleSignals(
          'disconnect',
          { project_path: projectPath, scene_path: 'x.tscn', signal: 's', from: 'a', to: 'b', method: 'm' },
          config,
        ),
      ).rejects.toThrow('Scene not found')
    })
    it('disconnect: connection not found', async () => {
      createTmpScene(projectPath, 't.tscn', MINIMAL_TSCN)
      await expect(
        handleSignals(
          'disconnect',
          { project_path: projectPath, scene_path: 't.tscn', signal: 's', from: 'a', to: 'b', method: 'm' },
          config,
        ),
      ).rejects.toThrow('Connection not found')
    })
    it('missing scene_path', async () => {
      await expect(handleSignals('list', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
  })

  // animation
  describe('animation', () => {
    it('create_player: scene not found', async () => {
      await expect(
        handleAnimation('create_player', { project_path: projectPath, scene_path: 'x.tscn' }, config),
      ).rejects.toThrow('Scene not found')
    })
    it('add_animation: no [node] section', async () => {
      createTmpScene(projectPath, 'e.tscn', '[gd_scene format=3]\n')
      await handleAnimation(
        'add_animation',
        { project_path: projectPath, scene_path: 'e.tscn', anim_name: 'idle', duration: 2.0 },
        config,
      )
      expect(readFileSync(join(projectPath, 'e.tscn'), 'utf-8')).toContain('Animation_idle')
    })
    it('add_track: missing args', async () => {
      createTmpScene(projectPath, 't.tscn')
      await expect(
        handleAnimation('add_track', { project_path: projectPath, scene_path: 't.tscn', anim_name: 'w' }, config),
      ).rejects.toThrow('anim_name, node_path, and property required')
    })
    it('add_track: scene not found', async () => {
      await expect(
        handleAnimation(
          'add_track',
          { project_path: projectPath, scene_path: 'x.tscn', anim_name: 'w', node_path: '.', property: 'p' },
          config,
        ),
      ).rejects.toThrow('Scene not found')
    })
    it('list: scene not found', async () => {
      await expect(
        handleAnimation('list', { project_path: projectPath, scene_path: 'x.tscn' }, config),
      ).rejects.toThrow('Scene not found')
    })
    it('add_animation: scene not found', async () => {
      await expect(
        handleAnimation('add_animation', { project_path: projectPath, scene_path: 'x.tscn', anim_name: 'w' }, config),
      ).rejects.toThrow('Scene not found')
    })
    it('add_animation: missing anim_name', async () => {
      createTmpScene(projectPath, 't.tscn')
      await expect(
        handleAnimation('add_animation', { project_path: projectPath, scene_path: 't.tscn' }, config),
      ).rejects.toThrow('No anim_name specified')
    })
    it('create_player: missing scene_path', async () => {
      await expect(handleAnimation('create_player', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('add_animation: missing scene_path', async () => {
      await expect(handleAnimation('add_animation', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('add_track: missing scene_path', async () => {
      await expect(handleAnimation('add_track', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
    it('list: missing scene_path', async () => {
      await expect(handleAnimation('list', { project_path: projectPath }, config)).rejects.toThrow(
        'No scene_path specified',
      )
    })
  })

  // resources
  describe('resources', () => {
    it('info: missing resource_path', async () => {
      await expect(handleResources('info', { project_path: projectPath }, config)).rejects.toThrow(
        'No resource_path specified',
      )
    })
    it('delete: missing resource_path', async () => {
      await expect(handleResources('delete', { project_path: projectPath }, config)).rejects.toThrow(
        'No resource_path specified',
      )
    })
    it('import_config: missing resource_path', async () => {
      await expect(handleResources('import_config', { project_path: projectPath }, config)).rejects.toThrow(
        'No resource_path specified',
      )
    })
    it('import_config: no .import file', async () => {
      const r = await handleResources('import_config', { project_path: projectPath, resource_path: 'x.png' }, config)
      expect(JSON.parse(r.content[0].text).imported).toBe(false)
    })
    it('import_config: read .import file', async () => {
      writeFileSync(join(projectPath, 'i.png.import'), '[remap]\npath="res://i"\n', 'utf-8')
      const r = await handleResources('import_config', { project_path: projectPath, resource_path: 'i.png' }, config)
      expect(r.content[0].text).toContain('remap')
    })
    it('info: .tres metadata', async () => {
      writeFileSync(join(projectPath, 't.tres'), '[gd_resource type="Theme" format=3]\n\n[resource]\n', 'utf-8')
      const r = await handleResources('info', { project_path: projectPath, resource_path: 't.tres' }, config)
      expect(JSON.parse(r.content[0].text).type).toBe('Theme')
    })
    it('list: type filter', async () => {
      mkdirSync(join(projectPath, 'img'), { recursive: true })
      writeFileSync(join(projectPath, 'img/a.png'), '', 'utf-8')
      const r = await handleResources('list', { project_path: projectPath, type: 'image' }, config)
      const d = JSON.parse(r.content[0].text)
      expect(
        d.resources.every((r: { ext: string }) => ['.png', '.jpg', '.jpeg', '.svg', '.webp'].includes(r.ext)),
      ).toBe(true)
    })
    it('delete: also removes .import', async () => {
      writeFileSync(join(projectPath, 'i.png'), '', 'utf-8')
      writeFileSync(join(projectPath, 'i.png.import'), 'data', 'utf-8')
      await handleResources('delete', { project_path: projectPath, resource_path: 'i.png' }, config)
      const { existsSync } = await import('node:fs')
      expect(existsSync(join(projectPath, 'i.png'))).toBe(false)
      expect(existsSync(join(projectPath, 'i.png.import'))).toBe(false)
    })
  })
})
