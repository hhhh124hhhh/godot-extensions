/**
 * Coverage tests for input-map edge cases
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { GodotConfig } from '../../src/godot/types.js'
import { handleInputMap } from '../../src/tools/composite/input-map.js'
import { createTmpProject, makeConfig } from '../fixtures.js'

describe('input-map coverage', () => {
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

  it('list: missing project_path', async () => {
    await expect(handleInputMap('list', {}, makeConfig())).rejects.toThrow('No project path specified')
  })
  it('add_event: missing args', async () => {
    await expect(
      handleInputMap('add_event', { project_path: projectPath, action_name: 'jump' }, config),
    ).rejects.toThrow('action_name, event_type, and event_value required')
  })
  it('remove_action: missing action_name', async () => {
    await expect(handleInputMap('remove_action', { project_path: projectPath }, config)).rejects.toThrow(
      'No action_name specified',
    )
  })
  it('multi-line input action', async () => {
    const ml = `[application]\nconfig/name="T"\n\n[input]\ncomplex={
"deadzone": 0.2,
"events": [Object(InputEventKey,"keycode":65)]
}\nsimple={"deadzone": 0.5, "events": []}\n\n[rendering]\n`
    const t = createTmpProject(ml)
    const r = await handleInputMap('list', { project_path: t.projectPath }, makeConfig({ projectPath: t.projectPath }))
    const d = JSON.parse(r.content[0].text)
    expect(d.actions.find((a: { name: string }) => a.name === 'complex')).toBeDefined()
    t.cleanup()
  })
  it('key: numeric code', async () => {
    const r = await handleInputMap(
      'add_event',
      { project_path: projectPath, action_name: 'jump', event_type: 'key', event_value: '32' },
      config,
    )
    expect(r.content[0].text).toContain('Added key event')
  })
  it('mouse: numeric code', async () => {
    const r = await handleInputMap(
      'add_event',
      { project_path: projectPath, action_name: 'jump', event_type: 'mouse', event_value: '1' },
      config,
    )
    expect(r.content[0].text).toContain('Added mouse event')
  })
})
