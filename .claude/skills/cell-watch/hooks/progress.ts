// Reads saffron/events.py's wire format: one JSON object per line, `kind` naming the dataclass.
export type CellEvent = { kind: string; timestamp: number; spec_id: string } & Record<string, unknown>

export type Milestone = { key: string; line: string }

export type Progress = {
  spec: string
  status: string
  lines: string[]
  milestones: Milestone[]
}

// prose fails at base by design (.saffron/policy.yaml). Any other baseline fail is red on the cell's base.
const FAILS_AT_BASE = new Set(['prose'])

export function parse(text: string): CellEvent[] {
  const events: CellEvent[] = []
  for (const line of text.split('\n')) {
    if (line.trim() === '') continue
    try {
      const obj: unknown = JSON.parse(line)
      if (typeof obj === 'object' && obj !== null && typeof (obj as CellEvent).kind === 'string') {
        events.push(obj as CellEvent)
      }
    } catch {
      // A truncated final line is a write in progress, as read_log treats it.
    }
  }
  return events
}

// A spec driven twice shares one log, and Ceilings opens every task (saffron/watch.py).
export function newestTask(events: CellEvent[]): CellEvent[] {
  let start = 0
  events.forEach((event, i) => {
    if (event.kind === 'Ceilings') start = i
  })
  return events.slice(start)
}

const str = (v: unknown): string => (typeof v === 'string' ? v : '')
const num = (v: unknown): number | null => (typeof v === 'number' ? v : null)
const strs = (v: unknown): string[] => (Array.isArray(v) ? v.filter(x => typeof x === 'string') : [])
const usd = (v: number | null): string => (v === null ? '?' : `$${v.toFixed(2)}`)

// A stacked batch hands one stale base to every cell, so one fail set wakes once per session.
function baselineKey(event: CellEvent, fails: string[], aborted: string[]): string {
  return aborted.length ? `${event.spec_id}:Baseline:${event.timestamp}` : `baseline:${fails.join(',')}`
}

export function summarize(all: CellEvent[]): Progress {
  const events = newestTask(all)
  const spec = events.length > 0 ? str(events[events.length - 1]?.spec_id) : ''
  let budget: number | null = null
  let spent: number | null = null
  let label = ''
  let outcome = ''
  const lines: string[] = []
  const milestones: Milestone[] = []
  const mark = (event: CellEvent, line: string, key = `${event.spec_id}:${event.kind}:${event.timestamp}`) => {
    milestones.push({ key, line })
  }

  for (const e of events) {
    switch (e.kind) {
      case 'Ceilings':
        budget = num(e.budget_usd)
        lines.push(`ceilings: ${usd(budget)}, ${e.max_attempts} attempts, ${e.max_turns} turns`)
        break
      case 'Preflight':
        label = 'PREFLIGHT'
        lines.push(`preflight: ${str(e.step)} ${str(e.detail)}`.trimEnd())
        break
      case 'Baseline': {
        const gates = strs(e.gates)
        const statuses = strs(e.statuses)
        const fails = gates.filter((_, i) => statuses[i] === 'fail')
        const aborted = strs(e.aborted)
        const line = `baseline: ${fails.length ? `fail=${fails.join(',')}` : 'green'}${
          aborted.length ? `; aborted=${aborted.join(',')}` : ''
        }`
        lines.push(line)
        if (aborted.length || fails.some(g => !FAILS_AT_BASE.has(g))) mark(e, line, baselineKey(e, fails, aborted))
        break
      }
      case 'GateResult':
        // Baseline already says each gate at base, so show only an attempt's non-pass.
        if (e.against !== 'baseline' && e.status !== 'pass' && e.status !== 'skip') {
          const n = num(e.new_failures)
          lines.push(`gate ${str(e.gate)} ${str(e.status)}${n === null ? '' : ` (${n} new)`}`)
        }
        break
      case 'PhaseStart':
        label = str(e.label) || str(e.phase)
        lines.push(`${label}: ${str(e.detail)}`.trimEnd())
        break
      case 'Attempt':
        spent = num(e.spent_usd_est) ?? spent
        label = `${str(e.phase)} #${e.attempt}`
        lines.push(
          `attempt ${e.attempt} ${str(e.phase)}${e.decision ? `: ${str(e.decision)}` : ''}${
            e.commits == null ? '' : `, ${e.commits} commits`
          }`,
        )
        break
      case 'Budget': {
        const line = `budget: ${str(e.ceiling)} ${e.value}/${e.limit}`
        lines.push(line)
        // events.py: only a budget_usd event with no rebut spend stops the task.
        if (e.ceiling === 'budget_usd' && e.rebut_spent_usd_est == null) mark(e, line)
        break
      }
      case 'Terminal': {
        spent = num(e.spent_usd_est) ?? spent
        const line = `terminal: ${str(e.reason)} at ${usd(spent)}${e.detail ? `: ${str(e.detail)}` : ''}`
        lines.push(line)
        mark(e, line)
        break
      }
      case 'TaskOutcome': {
        spent = num(e.spent_usd_est) ?? spent
        outcome = str(e.outcome)
        const resets = num(e.resets_at)
        const line = `${outcome} at ${usd(spent)} of ${usd(budget)}${
          resets === null ? '' : `, window reopens ${new Date(resets * 1000).toLocaleTimeString()}`
        }`
        lines.push(line)
        mark(e, line)
        break
      }
      case 'Teardown':
        if (e.ok === false) lines.push(`teardown: ${str(e.step)} failed ${str(e.detail)}`.trimEnd())
        break
    }
  }

  const where = outcome || label || 'waiting'
  const money = spent === null ? '' : ` · ${usd(spent)}/${usd(budget)}`
  return { spec, status: spec ? `${spec} · ${where}${money}` : '', lines, milestones }
}
