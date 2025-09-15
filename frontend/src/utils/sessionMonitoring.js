import { useEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

export function useRouteTrace(rid) {
  const loc = useLocation(); 
  const nav = useNavigationType();
  
  useEffect(() => {
    console.log(`[ROUTE] ${rid}`, { 
      path: loc.pathname + loc.search, 
      nav, 
      timestamp: new Date().toISOString() 
    });
  }, [loc, nav, rid]);
}

// Global error monitoring hooks
export const setupGlobalErrorMonitoring = (requestId) => {
  // Global error handler
  window.onerror = (message, source, lineno, colno, error) => {
    console.error('[GLOBAL_ERROR]', {
      requestId,
      message,
      source,
      lineno,
      colno,
      error: error?.stack || error,
      timestamp: new Date().toISOString()
    });
  };

  // Unhandled promise rejection handler
  window.onunhandledrejection = (event) => {
    console.error('[UNHANDLED_REJECTION]', {
      requestId,
      reason: event.reason,
      promise: event.promise,
      timestamp: new Date().toISOString()
    });
  };

  console.log(`[MONITORING] Global error hooks activated for request ${requestId}`);
};