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
    <div className="border border-purple rounded p-3">
      <div className="text-xs text-purple tracking-widest uppercase mb-3 flex items-center gap-2">
        <span className="animate-blink">▮</span>
        APPROVAL REQUIRED ({pendingApprovals.length})
      </div>
      {pendingApprovals.map((a) => (
        <div key={a.plan_id} className="bg-bg rounded p-3 mb-2 border border-border">
          <div className="text-xs text-text font-mono mb-1">{a.plan_label}</div>
          <div className="text-xs text-muted mb-1">{a.incident_id}</div>
          <div className="text-xs text-red mb-3">
            RISK {(a.risk_score * 100).toFixed(0)}% — {a.reason}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => respond(a.plan_id, 'approve')}
              className="flex-1 py-1 border border-green text-green text-xs hover:bg-green hover:text-bg transition-all"
            >
              APPROVE
            </button>
            <button
              onClick={() => respond(a.plan_id, 'reject')}
              className="flex-1 py-1 border border-red text-red text-xs hover:bg-red hover:text-bg transition-all"
            >
              REJECT
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
