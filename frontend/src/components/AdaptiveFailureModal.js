import React, { useState } from 'react';

const AdaptiveFailureModal = ({ userEmail, onNotify, onClose }) => {
  const [notificationSent, setNotificationSent] = useState(false);
  const [sending, setSending] = useState(false);

  const handleNotifyTeam = async () => {
    setSending(true);
    try {
      await onNotify();
      setNotificationSent(true);
    } catch (error) {
      console.error('Failed to send notification:', error);
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" style={{ backdropFilter: 'blur(4px)' }}>
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full mx-4 animate-fadeIn">
        {!notificationSent ? (
          <>
            {/* Warning Icon */}
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center">
                <span className="text-4xl">⚠️</span>
              </div>
            </div>

            {/* Title */}
            <h2 className="text-2xl font-bold text-center text-gray-800 mb-3">
              Session Preparation Issue
            </h2>

            {/* Description */}
            <p className="text-center text-gray-600 mb-6">
              Our adaptive engine encountered an issue preparing your personalized session. This is unusual and we're sorry for the inconvenience.
            </p>

            {/* What's happening */}
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-gray-700">
                <strong>What's happening:</strong> The background analysis that personalizes your sessions may have taken longer than expected or encountered a temporary issue.
              </p>
            </div>

            {/* Notify Button */}
            <button
              onClick={handleNotifyTeam}
              disabled={sending}
              className="w-full bg-[#9ac026] hover:bg-[#8ab01f] text-white font-medium py-3 px-4 rounded-lg transition-colors mb-4 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending ? 'Notifying Team...' : '🚀 Notify Support Team'}
            </button>

            {/* Help text */}
            <p className="text-xs text-center text-gray-500">
              Our technical team will investigate and resolve this immediately.
            </p>
          </>
        ) : (
          <>
            {/* Success Icon */}
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                <span className="text-4xl">✅</span>
              </div>
            </div>

            {/* Title */}
            <h2 className="text-2xl font-bold text-center text-gray-800 mb-3">
              Support Team Notified!
            </h2>

            {/* Success Message */}
            <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
              <p className="text-sm text-green-800">
                Our technical team has been alerted and will investigate immediately. We'll email you at <strong>{userEmail}</strong> once your session is ready.
              </p>
            </div>

            {/* What to do next */}
            <div className="bg-blue-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-gray-700">
                <strong>What to do next:</strong>
              </p>
              <ul className="text-sm text-gray-600 mt-2 ml-4 list-disc space-y-1">
                <li>Take a 5-10 minute break</li>
                <li>Try starting a session again</li>
                <li>Check your email for updates</li>
              </ul>
            </div>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors"
            >
              Close
            </button>
          </>
        )}
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: scale(0.9);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default AdaptiveFailureModal;
