import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

import type { ParkingDecision } from '@/api/types';

type ScanResultState = {
  decision: ParkingDecision | null;
  setDecision: (decision: ParkingDecision | null) => void;
};

const ScanResultContext = createContext<ScanResultState | null>(null);

export function ScanResultProvider({ children }: { children: ReactNode }) {
  const [decision, setDecision] = useState<ParkingDecision | null>(null);
  const value = useMemo(() => ({ decision, setDecision }), [decision]);
  return <ScanResultContext.Provider value={value}>{children}</ScanResultContext.Provider>;
}

export function useScanResult(): ScanResultState {
  const state = useContext(ScanResultContext);
  if (!state) throw new Error('useScanResult must be used inside ScanResultProvider');
  return state;
}
