import React, { useState } from 'react';

const PauseSubscriptionModal = ({ isOpen, onClose, onConfirmPause }) => {
  const [isPausing, setIsPausing] = useState(false);

  const handlePause = async () => {
    setIsPausing(true);
    try {
      await onConfirmPause();
    } catch (error) {
      console.error('Error pausing subscription:', error);
    } finally {
      setIsPausing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-md w-full">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
              Pause Your Subscription
            </h2>
            <button
              onClick={onClose}
              disabled={isPausing}
              className="text-gray-400 hover:text-gray-600 text-2xl font-light disabled:opacity-50"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Icon */}
          <div className="text-center mb-6">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center" style={{ backgroundColor: '#f0f9ff' }}>
              <svg className="w-8 h-8 text-[#9ac026]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>

          {/* Message */}
          <div className="text-center mb-6">
            <p className="text-gray-700 mb-4" style={{ fontFamily: 'Lato, sans-serif', lineHeight: '1.6' }}>
              We understand your hectic schedules and maybe pausing your subscription now makes better sense. 
              But we have got you covered and you can resume your subscription anytime, balance days get carry forwarded.
            </p>
            
            <div className="bg-orange-50 border-l-4 border-orange-400 p-4 rounded-r-lg mb-4">
              <p className="text-sm text-orange-800 font-medium" style={{ fontFamily: 'Lato, sans-serif' }}>
                <strong>PS:</strong> Please note, you would be required to re-subscribe at the time of resuming.
              </p>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h3 className="text-sm font-semibold text-green-800 mb-1" style={{ fontFamily: 'Lato, sans-serif' }}>
                    What happens when you pause?
                  </h3>
                  <ul className="text-sm text-green-700 space-y-1" style={{ fontFamily: 'Lato, sans-serif' }}>
                    <li>• Your remaining days are safely stored</li>
                    <li>• Access is temporarily suspended</li>
                    <li>• Resume anytime with bonus balance days</li>
                    <li>• No penalties, just flexible learning</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={isPausing}
              className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors disabled:opacity-50"
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              Continue Subscription
            </button>
            <button
              onClick={handlePause}
              disabled={isPausing}
              className="flex-1 px-4 py-3 bg-orange-500 text-white rounded-lg font-semibold hover:bg-orange-600 transition-colors disabled:opacity-50"
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              {isPausing ? (
                <div className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Pausing...
                </div>
              ) : (
                'Pause Subscription'
              )}
            </button>
          </div>

          {/* Footer Note */}
          <p className="text-xs text-gray-500 text-center mt-4" style={{ fontFamily: 'Lato, sans-serif' }}>
            Designed to fit your CAT prep journey • Twelvr
          </p>
        </div>
      </div>
    </div>
  );
};

export default PauseSubscriptionModal;