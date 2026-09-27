export const colors = {
  background: '#F5F7FA',
  surface: '#FFFFFF',
  primary: '#1E4FD8',
  primaryPressed: '#173DA8',
  text: '#0F172A',
  textMuted: '#64748B',
  border: '#E2E8F0',

  warningBackground: '#FEF3C7',
  warningText: '#92400E',
  errorText: '#B91C1C',

  // Result statuses, mirroring ParkingStatus on the backend. Dark enough for white text.
  status: {
    green: '#15803D',
    orange: '#B45309',
    red: '#B91C1C',
    unknown: '#475569',
  },
} as const;
