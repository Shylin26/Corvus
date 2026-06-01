import useStore from '../store'

const STATUS_BADGE = {
  DETECTING:         'bg-yellow-500',
  DIAGNOSING:        'bg-orange-500',
  PLANNING:          'bg-orange-500',
  AWAITING_APPROVAL: 'bg-purple-500',
  EXECUTING:         'bg-red-500',
  RESOLVED:          'bg-green-500',
  ROLLED_BACK:       'bg-gray-500',
  FAILED:            'bg-red-700',
}

export default function IncidentTimeline() {
  const { incidents, selectedId, setSelectedId } = useStore()

  if (incidents.length === 0) {
    return (
      <div className="text-gray-500 text-sm text-center py-8">
        No incidents yet. Inject chaos to trigger one.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {incidents.map((inc) => (
        <div
          key={inc.incident_id}
          onClick={() => setSelectedId(inc.incident_id)}
          className={`p-3 rounded-lg border cursor-pointer transition-all ${
            selectedId === inc.incident_id
              ? 'border-blue-500 bg-gray-800'
              : 'border-gray-700 bg-gray-900 hover:border-gray-500'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-white text-sm font-mono">{inc.incident_id}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full text-white ${STATUS_BADGE[inc.status] || 'bg-gray-600'}`}>
              {inc.status}
            </span>
          </div>
          <div className="text-gray-400 text-xs mt-1">{inc.service}</div>
        </div>
      ))}
    </div>
  )
}
