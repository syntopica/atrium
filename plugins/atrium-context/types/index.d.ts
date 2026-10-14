declare module 'claude-code' {
  interface PluginState {
    'atrium-context': {
      summary: string | null
      warning: string | null
      usage: { injected: number; lookups: number; read: string[]; cited: string[]; isComplete: boolean } | null
      instance: string | null
      activity: { kind: 'searching' | 'retrying'; frame: number } | null
      pulse: boolean | null
      details: {
        query: string
        status: 'healthy' | 'nothing' | 'degraded' | 'failed'
        reason: string
        attempts: number
        ms: number
        chars: number
        lane: string | null
        servedBy: string | null
        atriumMs: number | null
        passes: { name: string; ms: number; candidates: number }[]
        freshness: string | null
        items: { kind: string; date: string; source: string; score: number | null; title: string }[]
      } | null
      isShown: boolean | null
      stats: { retrievals: number; failures: number; retries: number; totalMs: number; chars: number } | null
    }
  }
}
