// Feature flag configuration
export const ADAPTIVE_GLOBAL = 
  (import.meta.env.VITE_ADAPTIVE_GLOBAL ?? process.env.REACT_APP_ADAPTIVE_GLOBAL) === 'true';

console.log('🏁 Adaptive Global Flag:', ADAPTIVE_GLOBAL);