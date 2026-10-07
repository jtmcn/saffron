import { expect, test } from 'claude-code/testing'

import { parse, summarize } from '../hooks/progress'

const line = (o: object) => JSON.stringify(o)
const base = { spec_id: 'SA-0222' }

const OLD_TASK = [
  line({ kind: 'Ceilings', timestamp: 1, ...base, budget_usd: 10, max_attempts: 1, max_turns: 5 }),
  line({ kind: 'TaskOutcome', timestamp: 2, ...base, outcome: 'EXHAUSTED', spent_usd_est: 9 }),
]

const LIVE = [
  line({ kind: 'Ceilings', timestamp: 10, ...base, budget_usd: 26, max_attempts: 3, max_turns: 180 }),
  line({ kind: 'Preflight', timestamp: 11, ...base, step: 'cell_up', detail: 'up' }),
  line({
    kind: 'Baseline', timestamp: 12, ...base, aborted: [],
    gates: ['lint', 'prose', 'terms'], statuses: ['pass', 'fail', 'fail'],
  }),
  line({ kind: 'GateResult', timestamp: 12.1, ...base, gate: 'prose', status: 'fail', against: 'baseline' }),
  line({ kind: 'PhaseStart', timestamp: 13, ...base, phase: 'IMPLEMENT', label: 'PLAN', detail: 'accepted' }),
  line({ kind: 'Attempt', timestamp: 14, ...base, phase: 'IMPLEMENT', attempt: 1, commits: 2, spent_usd_est: 3.1 }),
]

test('the newest task alone is summarized, and prose failing at base wakes nobody', async () => {
  const proseOnly = line({
    kind: 'Baseline', timestamp: 12, ...base, aborted: [], gates: ['lint', 'prose'], statuses: ['pass', 'fail'],
  })
  const p = summarize(parse([...OLD_TASK, ...LIVE.map((l, i) => (i === 2 ? proseOnly : l))].join('\n')))
  expect(p.lines).toContain('baseline: fail=prose')
  expect(p.status).toBe('SA-0222 · IMPLEMENT #1 · $3.10/$26.00')
  expect(p.milestones).toEqual([])
  expect(p.lines.some(l => l.includes('EXHAUSTED'))).toBe(false)
})

test('a baseline fail other than prose is a milestone', async () => {
  const p = summarize(parse(LIVE.join('\n')))
  expect(p.milestones.map(m => m.line)).toEqual(['baseline: fail=prose,terms'])
  const next = summarize(parse(LIVE.map(l => l.replaceAll('SA-0222', 'SA-0223')).join('\n')))
  expect(next.milestones[0]?.key).toBe(p.milestones[0]?.key)
  expect(p.lines.filter(l => l.startsWith('gate '))).toEqual([])
})

test('an outcome is a milestone with spend against budget, and a rate limit names its reopening', async () => {
  const done = [
    ...LIVE,
    line({ kind: 'TaskOutcome', timestamp: 20, ...base, outcome: 'RATE_LIMITED', spent_usd_est: 7.92, resets_at: 1791400000 }),
  ]
  const p = summarize(parse(done.join('\n')))
  const last = p.milestones.at(-1)
  expect(last?.key).toBe('SA-0222:TaskOutcome:20')
  expect(last?.line.startsWith('RATE_LIMITED at $7.92 of $26.00, window reopens')).toBe(true)
  expect(p.status.startsWith('SA-0222 · RATE_LIMITED')).toBe(true)
})

test('a truncated final line is skipped, not fatal', async () => {
  const p = summarize(parse(`${LIVE.join('\n')}\n{"kind": "Attem`))
  expect(p.lines.length).toBeGreaterThan(0)
})

test('only a budget_usd ceiling with no rebut spend stops the task', async () => {
  const stop = line({ kind: 'Budget', timestamp: 30, ...base, ceiling: 'budget_usd', value: 26, limit: 26 })
  const rebut = line({
    kind: 'Budget', timestamp: 31, ...base, ceiling: 'budget_usd', value: 20, limit: 26, rebut_spent_usd_est: 2,
  })
  const turns = line({ kind: 'Budget', timestamp: 32, ...base, ceiling: 'max_turns', value: 180, limit: 180 })
  const keys = summarize(parse([LIVE[0], stop, rebut, turns].join('\n'))).milestones.map(m => m.key)
  expect(keys).toEqual(['SA-0222:Budget:30'])
})
