// Pack History Recorder - Tracks all pack state changes
const packHistory = [];

function recordPackWrite(next, reason) {
  const len = Array.isArray(next) ? next.length : -1;
  const stack = new Error().stack;
  packHistory.push({ 
    ts: Date.now(), 
    len, 
    reason, 
    stack: stack?.split('\n').slice(1, 5).join('\n') // First 4 stack frames
  });
  
  // Keep last 50 entries
  if (packHistory.length > 50) packHistory.shift();
  
  // Make available globally for debugging
  window.__packHistory = packHistory;
  
  console.log(`[PACK_WRITE] ${reason}: length=${len}, timestamp=${new Date().toISOString()}`);
}

export { recordPackWrite };