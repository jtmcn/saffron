// `spec` empty with `follow` false means nothing is watched.
// `since` is when a follow began: a log last written before it is the last batch's.
export type Watch = { spec: string; follow: boolean; wake: boolean; since?: number }

export type View = { spec: string; status: string; lines: string[] }

declare module 'claude-code' {
  interface PluginState {
    'cell-watch': { watch: Watch; view: View; announced: string[] }
  }
}
