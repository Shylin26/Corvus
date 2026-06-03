import { useEffect, useState } from 'react'
import ReactFlow, { Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'
import useStore from '../store'

const STATUS_COLOR = {
  healthy:           '#3FB950',
  DETECTING:         '#D29922',
  DIAGNOSING:        '#E3B341',
  PLANNING:          '#E3B341',
  AWAITING_APPROVAL: '#BC8CFF',
  EXECUTING:         '#F85149',
  RESOLVED:          '#3FB950',
  ROLLED_BACK:       '#484F58',
  FAILED:            '#F85149',
}

const BASE_NODES = [
  { id: 'api-gateway',          position: { x: 280, y: 40  }, data: { label: 'api-gateway' } },
  { id: 'auth-service',         position: { x: 80,  y: 180 }, data: { label: 'auth-service' } },
  { id: 'order-service',        position: { x: 280, y: 180 }, data: { label: 'order-service' } },
  { id: 'inventory-service',    position: { x: 480, y: 180 }, data: { label: 'inventory-service' } },
  { id: 'notification-service', position: { x: 280, y: 320 }, data: { label: 'notification-service' } },
]

const EDGES = [
  { id: 'gw-auth',   source: 'api-gateway',   target: 'auth-service' },
  { id: 'gw-order',  source: 'api-gateway',   target: 'order-service' },
  { id: 'gw-inv',    source: 'api-gateway',   target: 'inventory-service' },
  { id: 'ord-notif', source: 'order-service', target: 'notification-service' },
]

const ACTIVE = ['DETECTING','DIAGNOSING','PLANNING','AWAITING_APPROVAL','EXECUTING']

export default function Topology() {
  const incidents = useStore((s) => s.incidents)

  // Build service → worst active status map
  const serviceStatus = {}
  incidents.forEach((inc) => {
    if (!inc.service || inc.service === 'unknown') return
    const existing = serviceStatus[inc.service]
    // Active incidents take priority over resolved
    if (!existing || ACTIVE.includes(inc.status)) {
      serviceStatus[inc.service] = inc.status
    }
  })

  const nodes = BASE_NODES.map((n) => {
    const status  = serviceStatus[n.id]
    const color   = STATUS_COLOR[status] || STATUS_COLOR.healthy
    const active  = ACTIVE.includes(status)

    return {
      ...n,
      style: {
        background:   '#0D1117',
        color:        color,
        border:       `1px solid ${color}`,
        borderRadius: '2px',
        padding:      '8px 14px',
        fontFamily:   '"IBM Plex Mono", monospace',
        fontSize:     '11px',
        fontWeight:   500,
        letterSpacing:'0.05em',
        boxShadow:    active ? `0 0 16px ${color}60` : 'none',
        minWidth:     '130px',
        textAlign:    'center',
        transition:   'all 0.5s ease',
      },
    }
  })

  const edges = EDGES.map(e => {
    const srcStatus = serviceStatus[e.source]
    const active = ACTIVE.includes(srcStatus)
    return {
      ...e,
      style: { stroke: active ? '#D29922' : '#1C2128', strokeWidth: 1 },
      animated: active,
    }
  })

  return (
    <div className="h-[500px] bg-surface rounded border border-border">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#1C2128" gap={24} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  )
}
