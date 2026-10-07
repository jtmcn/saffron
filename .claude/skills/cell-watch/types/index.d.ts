// `spec` empty with `follow` false means nothing is watched.
export type Watch = { spec: string; follow: boolean; wake: boolean }

export type View = { spec: string; status: string; lines: string[] }

declare module 'claude-code' {
  interface PluginState {
    'cell-watch': { watch: Watch; view: View; announced: string[] }
  }
}
