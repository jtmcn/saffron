import { expect, test } from 'claude-code/testing'

const TOOL = 'mcp__cell-watch__watch'

test('the delegate can stop a watch through the tool', async ($, on) => {
  const shown: unknown[] = []
  on('ui.status', async (_$, e) => {
    shown.push(e)
    return { value: undefined }
  })
  const out = await $.tool.call({ tool: TOOL, input: { stop: true } })
  expect(out.result).toBe('cell-watch stopped.')
  expect(shown.length).toBe(1)
})

test('a spec that is no SA-NNNN id is refused before any watch starts', async $ => {
  const out = await $.tool.call({ tool: TOOL, input: { spec: '../../etc' } })
  expect(out.deny).toContain('not an SA-NNNN id')
})
