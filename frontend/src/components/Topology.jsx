import ReactFlow, { Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'
import useStore from '../store'

const STATUS_COLORS = {
  healthy:          '#22c55e',
  DETECTING:        '#eab308',
  DIAGNOSING:       '#f97316',
  PLANNING:         '#f97316',
  AWAITING_APPROVAL:'#a855f7',
  EXECUTING:        '#ef4444',
  RESOLVED:         '#22c55e',
  ROLLED_BACK:      '#6b7280',
  FAILED:           '#ef4444',
}

const BASE_NODES = [
  { id: 'api-gateway',          position: { x: 300, y: 50  }, data: { label: 'api-gateway' } },
  { id: 'auth-service',         position: { x: 100, y: 200 }, data: { label: 'auth-service' } },
  { id: 'order-service',        position: { x: 300, y: 200 }, data: { label: 'order-service' } },
  { id: 'inventory-service',    position: { x: 500, y: 200 }, data: { label: 'inventory-service' } },
  { id: 'notification-service', position: { x: 300, y: 350 }, data: { label: 'notification-service' } },
]

const EDGES = [
  { id: 'gw-auth',  source: 'api-gateway', target: 'auth-service' },
  { id: 'gw-order', source: 'api-gateway', target: 'order-service' },
  { id: 'gw-inv',   source: 'api-gateway', target: 'inventory-service' },
  { id: 'ord-notif',source: 'order-service', target: 'notification-service' },
]

export default function Topology() {
  const incidents = useStore((s) => s.incidents)

  const serviceStatus = {}
  incidents.forEach((inc) => {
    if (inc.service) serviceStatus[inc.service] = inc.status
  })

  const nodes = BASE_NODES.map((n) => ({
    ...n,
    style: {
      background: STATUS_COLORS[serviceStatus[n.id]] || STATUS_COLORS.healthy,
      color:  '#fff',
      border: '1px solid #374151',
      borderRadius: '8px',
      padding: '8px 16px',
      fontWeight: 600,
      fontSize: '12px',
    },
  }))

  return (
    <div className="h-96 bg-gray-900 rounded-lg border border-gray-700">
      <ReactFlow nodes={nodes} edges={EDGES} fitView>
        <Background color="#374151" />
        <Controls />
      </ReactFlow>
    </div>
  )
}
