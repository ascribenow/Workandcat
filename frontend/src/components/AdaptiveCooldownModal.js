import React, { useState, useEffect } from 'react';

const AdaptiveCooldownModal = ({ remainingSeconds, onClose, onCheckEarly }) => {
  const [timeLeft, setTimeLeft] = useState(remainingSeconds);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    setTimeLeft(remainingSeconds);
  }, [remainingSeconds]);

  useEffect(() => {
    if (timeLeft <= 0) {
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

  const handleCheckNow = async () => {
    setChecking(true);
    await onCheckEarly();
    setChecking(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" style={{ backdropFilter: 'blur(4px)' }}>
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full mx-4 animate-fadeIn">
        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-gradient-to-br from-[#9ac026] to-[#7a9920] rounded-full flex items-center justify-center animate-pulse">
            <span className="text-3xl">🧠</span>
          </div>
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold text-center text-gray-800 mb-3">
          Analyzing Your Performance
        </h2>

        {/* Description */}
        <p className="text-center text-gray-600 mb-6">
          Our adaptive engine is personalizing your next session based on your recent performance.
        </p>

        {/* Timer */}
        <div className="bg-gradient-to-r from-[#f0f5e6] to-[#e8f0d8] rounded-lg p-6 mb-6 text-center">
          <div className="text-4xl font-bold text-[#9ac026] mb-2">
            {formatTime(timeLeft)}
          </div>
          <div className="text-sm text-gray-600">
            remaining
          </div>
        </div>

        {/* Tip */}
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
          <div className="flex items-start">
            <span className="text-xl mr-2">💡</span>
            <p className="text-sm text-blue-800">
              <strong>Tip:</strong> Take a short break to stay fresh! Grab some water or stretch for a moment.
            </p>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleCheckNow}
            disabled={checking}
            className="flex-1 bg-[#9ac026] hover:bg-[#8ab01f] text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {checking ? 'Checking...' : 'Check If Ready'}
          </button>
        </div>

        {/* Progress indicator */}
        <div className="mt-4 flex justify-center gap-2">
          <div className={`w-2 h-2 rounded-full ${timeLeft > 90 ? 'bg-[#9ac026]' : 'bg-gray-300'} animate-bounce`} style={{ animationDelay: '0ms' }}></div>
          <div className={`w-2 h-2 rounded-full ${timeLeft > 60 ? 'bg-[#9ac026]' : 'bg-gray-300'} animate-bounce`} style={{ animationDelay: '150ms' }}></div>
          <div className={`w-2 h-2 rounded-full ${timeLeft > 30 ? 'bg-[#9ac026]' : 'bg-gray-300'} animate-bounce`} style={{ animationDelay: '300ms' }}></div>
        </div>
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

export default AdaptiveCooldownModal;
