import React from 'react';

/**
 * Session Status Component - Clean loading states and error handling
 */
export function SessionStatus({ state, onRetry }) {
  if (state.phase === 'preparing') {
    return (
      <div className="flex items-center space-x-3 text-blue-600">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
        <div className="font-medium">{state.message || 'Preparing your session…'}</div>
      </div>
    );
  }
  
  if (state.phase === 'failed') {
    return (
      <div className="space-y-2">
        <div className="text-red-600 font-medium">{state.message}</div>
        {state.error && (
          <div className="text-red-500 text-sm">{state.error}</div>
        )}
        {state.canRetry && onRetry && (
          <button 
            onClick={onRetry} 
            className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 transition-colors"
          >
            Try again
          </button>
        )}
      </div>
    );
  }
  
  if (state.phase === 'ready') {
    return (
      <div className="flex items-center space-x-2 text-green-600">
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
        <div className="font-medium">{state.message || 'Session ready!'}</div>
      </div>
    );
  }
  
  return null;
}

export default SessionStatus;