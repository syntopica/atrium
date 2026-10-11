declare module 'claude-code' {
  interface PluginState {
    'atrium-context': {
      summary: string | null
      usage: { injected: number; lookups: number; read: string[]; cited: string[]; isComplete: boolean } | null
      instance: string | null
    }
  }
}
