import useStore from '../store'

const GATEWAY = 'http://localhost:8000'

export default function ApprovalPanel() {
  const { pendingApprovals, setPendingApprovals } = useStore()

  const respond = async (planId, action) => {
    await fetch(`${GATEWAY}/approvals/${planId}/${action}`, { method: 'POST' })
    setPendingApprovals(pendingApprovals.filter((a) => a.plan_id !== planId))
  }

  if (pendingApprovals.length === 0) return null

  return (
    <div className="border border-purple-700 bg-purple-950 rounded-lg p-4 mb-4">
      <h3 className="text-purple-300 font-semibold text-sm mb-3">
        ⚠ Pending Approvals ({pendingApprovals.length})
      </h3>
      {pendingApprovals.map((a) => (
        <div key={a.plan_id} className="bg-gray-900 rounded p-3 mb-2">
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="text-white text-sm font-semibold">{a.plan_label}</div>
              <div className="text-gray-400 text-xs">{a.incident_id} — {a.reason}</div>
              <div className="text-red-400 text-xs">Risk: {(a.risk_score * 100).toFixed(0)}%</div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => respond(a.plan_id, 'approve')}
                className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white text-xs rounded"
              >
                Approve
              </button>
              <button
                onClick={() => respond(a.plan_id, 'reject')}
                className="px-3 py-1 bg-red-700 hover:bg-red-600 text-white text-xs rounded"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
