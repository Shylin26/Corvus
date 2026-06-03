import { useState } from 'react'
import Topology from './components/Topology'
import IncidentTimeline from './components/IncidentTimeline'
import ApprovalPanel from './components/ApprovalPanel'
import ChatInterface from './components/ChatInterface'
import StatusBar from './components/StatusBar'
import ChatInterface from './components/ChatInterface'
import { useIncidents } from './hooks/useIncidents'
import useStore from './store'

export default function App() {
  useIncidents()
  const incidents = useStore((s) => s.incidents)
  const [tab, setTab] = useState('topology')

  const active = incidents.filter(i =>
    !['RESOLVED', 'ROLLED_BACK', 'FAILED'].includes(i.status)
  ).length

  return (
    <div className="min-h-screen bg-bg flex flex-col">

      {/* Header */}
      <header className="border-b border-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-green font-display text-lg">◈</span>
            <span className="font-display text-text text-lg tracking-widest">CORVUS</span>
          </div>
          <span className="text-muted text-xs tracking-widest uppercase">
            / self-healing infrastructure
          </span>
        </div>
        <div className="flex items-center gap-6 text-xs text-muted">
          {active > 0 && (
            <span className="text-amber animate-pulse-slow">
              ⚠ {active} ACTIVE INCIDENT{active > 1 ? 'S' : ''}
            </span>
          )}
          <span className="text-green">● SYSTEM ONLINE</span>
        </div>
      </header>

      {/* Tab bar */}
      <div className="border-b border-border px-6 flex gap-0">
        {['topology', 'incidents'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs tracking-widest uppercase border-b-2 transition-all ${
              tab === t
                ? 'border-green text-green'
                : 'border-transparent text-muted hover:text-text'
            }`}
          >
            {t}
            {t === 'incidents' && incidents.length > 0 && (
              <span className="ml-2 bg-dim text-text px-1.5 py-0.5 rounded text-xs">
                {incidents.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Main content */}
      <main className="flex-1 flex gap-0">

        {/* Left panel */}
        <div className="flex-1 p-6">
          {tab === 'topology' && (
            <div>
              <div className="text-xs text-muted tracking-widest uppercase mb-4">
                ▸ Service topology — live
              </div>
              <Topology />
            </div>
          )}
          {tab === 'incidents' && (
            <div>
              <div className="text-xs text-muted tracking-widest uppercase mb-4">
                ▸ Incident log
              </div>
              <IncidentTimeline />
            </div>
          )}
        </div>

        {/* Right panel */}
        <div className="w-80 border-l border-border p-4 flex flex-col gap-4">
          <ApprovalPanel />
          <StatusBar />
          <div>
            <div className="text-xs text-muted tracking-widest uppercase mb-3">
              ▸ Recent incidents
            </div>
            <IncidentTimeline compact />
          </div>
          <ChatInterface />
        </div>

      </main>
    </div>
  )
}
