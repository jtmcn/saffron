import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const TOOL = 'mcp__cell-watch__watch'
const ROOT = '/home/op/.saffron/batches/v0'
const line = (o: object) => JSON.stringify(o)

// A batch tree in memory: each spec's log text and when it was last written.
type Log = { text: string; mtimeMs: number }

function world(on: On, logs: Map<string, Log>) {
  const woken: string[] = []
  const clock = mock.clock(on)
  mock.env(on, { HOME: '/home/op' })
  on('process.run', async (_$, e) => {
    const [cmd, ...rest] = e.argv
    const stdout =
      cmd === 'find'
        ? [...logs.keys()].map(spec => `${ROOT}/${spec}/events.jsonl`).join('\n')
        : (logs.get(rest.at(-1)?.split('/').at(-2) ?? '')?.text ?? '')
    return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('fs.stat', async (_$, e) => {
    const mtimeMs = logs.get(e.path.split('/').at(-2) ?? '')?.mtimeMs ?? 0
    return { value: { kind: 'file', size: 1, mtimeMs, isLink: false } }
  })
  on('prompt.submit', async (_$, e) => {
    woken.push(e.text)
    return { text: e.text }
  })
  on('ui.status', async () => ({ value: undefined }))
  on('ui.toast', async () => ({ value: undefined }))
  return { woken, clock }
}

const opened = (spec: string, t: number) =>
  line({ kind: 'Ceilings', timestamp: t, spec_id: spec, budget_usd: 20, max_attempts: 3, max_turns: 100 })
const outcome = (spec: string, t: number) =>
  line({ kind: 'TaskOutcome', timestamp: t, spec_id: spec, outcome: 'READY_FOR_REVIEW', spent_usd_est: 4 })

test('the delegate can stop a watch through the tool', async ($, on) => {
  world(on, new Map())
  const out = await $.tool.call({ tool: TOOL, input: { stop: true, spec: 'SA-0001' } })
  expect(out.result).toBe('cell-watch stopped.')
})

test('a spec that is no SA-NNNN id is refused before any watch starts', async $ => {
  const out = await $.tool.call({ tool: TOOL, input: { spec: '../../etc' } })
  expect(out.deny).toContain('not an SA-NNNN id')
})

test('a pinned watch wakes the delegate on an outcome, and not for what the log held at start', async ($, on) => {
  const ended = line({ kind: 'Terminal', timestamp: 1.5, spec_id: 'SA-0001', reason: 'READY_FOR_REVIEW' })
  const start = `${opened('SA-0001', 1)}\n${ended}`
  const logs = new Map([['SA-0001', { text: start, mtimeMs: 1 }]])
  const { woken, clock } = world(on, logs)
  const out = await $.tool.call({ tool: TOOL, input: { spec: 'SA-0001' } })
  expect(out.result).toContain('Already in the log: terminal')
  await clock.advance(3000)
  expect(woken).toEqual([])
  logs.set('SA-0001', { text: `${start}\n${outcome('SA-0001', 2)}`, mtimeMs: 2 })
  await clock.advance(3000)
  expect(woken.length).toBe(1)
  expect(woken[0]).toContain('READY_FOR_REVIEW')
})

test('following a batch wakes the delegate when the next task starts, since the last one packaged', async ($, on) => {
  const logs = new Map([['SA-0001', { text: opened('SA-0001', 1), mtimeMs: 1 }]])
  const { woken, clock } = world(on, logs)
  await $.tool.call({ tool: TOOL, input: {} })
  logs.set('SA-0002', { text: opened('SA-0002', 5), mtimeMs: 5 })
  await clock.advance(3000)
  expect(woken.length).toBe(1)
  expect(woken[0]).toContain('SA-0001 has packaged, and SA-0002 started')
})

test('a stray word to /cell-watch is refused rather than read as follow mode', async ($, on) => {
  world(on, new Map())
  on('command.run', async () => ({ value: { text: 'unreached' } }))
  const out = await $.command.run({ command: 'cell-watch', args: 'SA-12x' })
  expect(JSON.stringify(out)).toContain('neither an SA-NNNN id nor a flag')
})
