import Topology from './components/Topology'
import IncidentTimeline from './components/IncidentTimeline'
import ApprovalPanel from './components/ApprovalPanel'
import { useIncidents } from './hooks/useIncidents'

export default function App() {
  useIncidents()

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4 flex items-center gap-3">
        <span className="text-2xl">🦅</span>
        <h1 className="text-xl font-bold tracking-tight">Corvus</h1>
        <span className="text-gray-500 text-sm">Self-healing infrastructure monitor</span>
      </header>

      <main className="p-6 grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div>
            <h2 className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">
              Service Topology
            </h2>
            <Topology />
          </div>
        </div>

        <div className="space-y-4">
          <ApprovalPanel />
          <div>
            <h2 className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">
              Incidents
            </h2>
            <IncidentTimeline />
          </div>
        </div>
      </main>
    </div>
  )
}
