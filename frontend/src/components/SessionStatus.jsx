import React from 'react';

/**
 * Session Status Component - Clean loading states and error handling
 */
export function SessionStatus({ state, onRetry }) {
  if (state.phase === 'preparing') {
    return (
      <div className="session-status preparing">
        <div className="loading-spinner"></div>
        <div className="message">{state.message || 'Preparing your session…'}</div>
      </div>
    );
  }
  
  if (state.phase === 'failed') {
    return (
      <div className="session-status failed">
        <div className="error-message">{state.message}</div>
        {state.error && (
          <div className="error-details">{state.error}</div>
        )}
        {state.canRetry && onRetry && (
          <button onClick={onRetry} className="retry-button">
            Try again
          </button>
        )}
      </div>
    );
  }
  
  if (state.phase === 'ready') {
    return (
      <div className="session-status ready">
        <div className="success-message">{state.message || 'Session ready!'}</div>
      </div>
    );
  }
  
  return null;
}

export default SessionStatus;