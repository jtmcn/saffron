import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, Timer } from 'claude-code'

import type { View, Watch } from '../types'
import { parse, summarize } from './progress'

const PANE = 'cell-watch'
const POLL_MS = 3000
const SPEC = /^SA-\d+$/

const watch = atom({ plugin: 'cell-watch', key: 'watch' } as const, { spec: '', follow: false, wake: true })
const view = atom({ plugin: 'cell-watch', key: 'view' } as const, { spec: '', status: '', lines: [] })
const announced = atom({ plugin: 'cell-watch', key: 'announced' } as const, [])

let timer: Timer | undefined
let busy = false

async function batches($: EngineInterface): Promise<string> {
  return `${(await $.env.get('HOME')) ?? ''}/.saffron/batches/v0`
}

// `saffron batch` moves from spec to spec, so follow mode takes the newest-written log.
async function newestSpec($: EngineInterface): Promise<string> {
  const root = await batches($)
  const found = await $.process.run(['find', root, '-maxdepth', '2', '-name', 'events.jsonl', '-mmin', '-720'])
  let best = { spec: '', mtime: -1 }
  for (const path of found.stdout.split('\n').filter(Boolean)) {
    const spec = path.split('/').at(-2) ?? ''
    if (!SPEC.test(spec)) continue
    const stat = await $.fs.stat(path).catch(() => undefined)
    if (stat && stat.mtimeMs > best.mtime) best = { spec, mtime: stat.mtimeMs }
  }
  return best.spec
}

// grep drops the agent's own lines. Measured on SA-0222, 300 KB of log became 5 KB, far under fs.read's 4 MiB cap.
async function events($: EngineInterface, spec: string) {
  const path = `${await batches($)}/${spec}/events.jsonl`
  const out = await $.process.run(['grep', '-v', '-F', '"kind": "Agent"', path])
  return parse(out.stdout)
}

// announce false marks what the log already holds as seen, so starting a watch wakes nobody.
async function poll($: EngineInterface, announce: boolean): Promise<string[]> {
  if (busy) return []
  busy = true
  try {
    const w: Watch = await read($, watch)
    const spec = w.follow ? await newestSpec($) : w.spec
    if (!spec) return []
    const progress = summarize(await events($, spec))
    const next: View = { spec, status: progress.status || `${spec} · no log yet`, lines: progress.lines.slice(-200) }
    await update($, view, () => next)
    $.ui.status(next.status)

    const seen = new Set<string>(await read($, announced))
    const fresh = progress.milestones.filter(m => !seen.has(m.key))
    if (fresh.length === 0) return []
    await update($, announced, list => [...list, ...fresh.map(m => m.key)].slice(-500))
    if (announce) {
      for (const m of fresh) {
        $.ui.toast(`${spec}: ${m.line}`)
        if (w.wake) {
          void $.prompt.submit({
            text:
              `cell-watch: ${spec} ${m.line}. Read from events.jsonl, not the process: ` +
              `wait for the cell's exit notice before \`driver.py record\`.`,
          })
        }
      }
    }
    return fresh.map(m => m.line)
  } finally {
    busy = false
  }
}

function arm($: EngineInterface) {
  timer?.cancel()
  timer = $.clock.every(POLL_MS, () => {
    void poll($, true).catch(err => $.ui.log(`cell-watch: ${String(err)}`, { to: 'debug' }))
  })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'cell-watch',
      description: 'Follow a Saffron task: /cell-watch [SA-NNNN] [--quiet] [--pane] | stop',
      argumentHint: '[SA-NNNN] [--quiet] [--pane] | stop',
    })
    // A hot reload drops the timer but keeps $.state, so a watch in progress resumes.
    const w = await read($, watch)
    if (w.spec || w.follow) arm($)
    return next(e)
  })

  on('command.run', { command: 'cell-watch' }, async ($, e) => {
    const words = e.args.trim().split(/\s+/).filter(Boolean)
    if (words.includes('stop')) {
      timer?.cancel()
      timer = undefined
      await update($, watch, () => ({ spec: '', follow: false, wake: true }))
      $.ui.status(undefined)
      return { text: 'cell-watch stopped.' }
    }
    const spec = words.find(w => SPEC.test(w)) ?? ''
    await update($, watch, () => ({ spec, follow: spec === '', wake: !words.includes('--quiet') }))
    const already = await poll($, false)
    arm($)
    if (words.includes('--pane')) void $.ui.open({ id: PANE, title: 'Cell watch' })
    const v = await read($, view)
    const target = spec || `the newest task (${v.spec || 'none in the last 12 h'})`
    const held = already.length ? ` Already in the log: ${already.join('; ')}.` : ''
    return { text: `Watching ${target}: ${v.status || 'no log yet'}.${held}` }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const v = await read($, view)
    const room = Math.max(1, (e.viewport?.rows ?? 24) - 4)
    return (
      <Box flexDirection="column">
        <Text bold>{v.status || 'Nothing watched.'}</Text>
        {v.lines.slice(-room).map(line => (
          <Text dimColor>{line}</Text>
        ))}
      </Box>
    )
  })
}
