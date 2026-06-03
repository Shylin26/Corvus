import useStore from '../store'

const STATUS_COLOR = {
  DETECTING:         'text-amber  border-amber',
  DIAGNOSING:        'text-amber  border-amber',
  PLANNING:          'text-amber  border-amber',
  AWAITING_APPROVAL: 'text-purple border-purple',
  EXECUTING:         'text-red    border-red',
  RESOLVED:          'text-green  border-green',
  ROLLED_BACK:       'text-muted  border-muted',
  FAILED:            'text-red    border-red',
}

export default function IncidentTimeline({ compact = false }) {
  const { incidents, selectedId, setSelectedId } = useStore()

  if (incidents.length === 0) {
    return (
      <div className="text-muted text-xs text-center py-8 border border-border rounded p-4">
        <div className="text-2xl mb-2 opacity-30">◈</div>
        <div>No incidents detected</div>
        <div className="mt-1 opacity-50">Run chaos injector to trigger pipeline</div>
      </div>
    )
  }

  const list = compact ? incidents.slice(0, 5) : incidents

  return (
    <div className="space-y-1">
      {list.map((inc) => {
        const colors = STATUS_COLOR[inc.status] || 'text-muted border-muted'
        return (
          <div
            key={inc.incident_id}
            onClick={() => setSelectedId(inc.incident_id)}
            className={`border-l-2 pl-3 py-2 cursor-pointer transition-all hover:bg-dim rounded-r ${
              selectedId === inc.incident_id ? 'bg-dim' : ''
            } ${colors}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-text">{inc.incident_id}</span>
              <span className={`text-xs ${colors.split(' ')[0]}`}>{inc.status}</span>
            </div>
            {inc.service && (
              <div className="text-xs text-muted mt-0.5">{inc.service}</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
