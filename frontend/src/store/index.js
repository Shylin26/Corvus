import { create } from 'zustand'

const useStore = create((set) => ({
  incidents:       [],
  selectedId:      null,
  pendingApprovals: [],

  setIncidents:        (incidents)        => set({ incidents }),
  setSelectedId:       (id)               => set({ selectedId: id }),
  setPendingApprovals: (pendingApprovals) => set({ pendingApprovals }),
}))

export default useStore
