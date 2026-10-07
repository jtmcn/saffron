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

// events.py's `_clean` and `_DETAIL_BOUND`: a detail mixes host and cell text (item 63).
const DETAIL_BOUND = 500
const CONTROL = /[\u0000-\u001f\u007f]/g

export function cellText(value: unknown): string {
  return (typeof value === 'string' ? value : '').replace(CONTROL, ' ').slice(0, DETAIL_BOUND)
}

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

// Each coerces a field of the wrong type to empty rather than failing the poll.
const asStr = (v: unknown): string => (typeof v === 'string' ? v : '')
const asNum = (v: unknown): number | null => (typeof v === 'number' ? v : null)
const asStrs = (v: unknown): string[] => (Array.isArray(v) ? v.filter(x => typeof x === 'string') : [])
const usd = (v: number | null): string => (v === null ? '?' : `$${v.toFixed(2)}`)

// A stacked batch hands one stale base to every cell, so one fail set wakes once per session.
function baselineKey(event: CellEvent, fails: string[], aborted: string[]): string {
  return aborted.length ? `${event.spec_id}:Baseline:${event.timestamp}` : `baseline:${fails.join(',')}`
}

function reopens(e: CellEvent): string {
  const resets = asNum(e.resets_at)
  if (resets !== null) return `, window reopens ${new Date(resets * 1000).toLocaleTimeString()}`
  return e.resets_at_unreadable === true ? ', reopening time unreadable' : ''
}

export function summarize(all: CellEvent[]): Progress {
  const events = newestTask(all)
  const spec = events.length > 0 ? asStr(events[events.length - 1]?.spec_id) : ''
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
    // Attempt, Terminal and TaskOutcome carry spend. A null is a phase that measured none.
    spent = asNum(e.spent_usd_est) ?? spent
    switch (e.kind) {
      case 'Ceilings':
        budget = asNum(e.budget_usd)
        lines.push(`ceilings: ${usd(budget)}, ${e.max_attempts} attempts, ${e.max_turns} turns`)
        break
      case 'Preflight':
        label = 'PREFLIGHT'
        lines.push(`preflight: ${asStr(e.step)} ${cellText(e.detail)}`.trimEnd())
        break
      case 'Baseline': {
        const gates = asStrs(e.gates)
        const statuses = asStrs(e.statuses)
        const fails = gates.filter((_, i) => statuses[i] === 'fail')
        const aborted = asStrs(e.aborted)
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
          const n = asNum(e.new_failures)
          lines.push(`gate ${asStr(e.gate)} ${asStr(e.status)}${n === null ? '' : ` (${n} new)`}`)
        }
        break
      case 'PhaseStart':
        label = asStr(e.label) || asStr(e.phase)
        lines.push(`${label}: ${cellText(e.detail)}`.trimEnd())
        break
      case 'Attempt':
        label = `${asStr(e.phase)} #${e.attempt}`
        lines.push(
          `attempt ${e.attempt} ${asStr(e.phase)}${e.decision ? `: ${asStr(e.decision)}` : ''}${
            e.commits == null ? '' : `, ${e.commits} commits`
          }`,
        )
        break
      case 'Budget': {
        const isUsd = e.ceiling === 'budget_usd'
        const reached = isUsd ? `${usd(asNum(e.value))}/${usd(asNum(e.limit))}` : `${e.value}/${e.limit}`
        const line = `budget: ${asStr(e.ceiling)} ${reached}`
        lines.push(line)
        // events.py: only a budget_usd event with no rebut spend stops the task.
        if (isUsd && e.rebut_spent_usd_est == null) mark(e, line)
        break
      }
      case 'Terminal': {
        const detail = cellText(e.detail)
        const line = `terminal: ${asStr(e.reason)} at ${usd(spent)}${detail ? `: ${detail}` : ''}`
        lines.push(line)
        mark(e, line)
        break
      }
      case 'TaskOutcome': {
        outcome = asStr(e.outcome)
        const line = `${outcome} at ${usd(spent)} of ${usd(budget)}${reopens(e)}`
        lines.push(line)
        mark(e, line)
        break
      }
      case 'Teardown':
        if (e.ok === false) lines.push(`teardown: ${asStr(e.step)} failed ${cellText(e.detail)}`.trimEnd())
        break
    }
  }

  const where = outcome || label || 'waiting'
  const money = spent === null ? '' : ` · ${usd(spent)}/${usd(budget)}`
  return { spec, status: spec ? `${spec} · ${where}${money}` : '', lines, milestones }
}
