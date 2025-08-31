import React from 'react';
import { useNavigate } from 'react-router-dom';

const UpgradeModal = ({ isOpen, onClose, completedSessions = 15 }) => {
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleUpgrade = () => {
    onClose();
    navigate('/pricing');
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        {/* Header with celebration icon */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-[#9ac026] rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">🎉</span>
          </div>
          <h2 className="text-2xl font-bold text-[#545454] mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Congratulations!
          </h2>
          <p className="text-lg text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
            You've completed <span className="font-semibold text-[#9ac026]">{completedSessions} sessions</span> of your free trial!
          </p>
        </div>

        {/* Message */}
        <div className="mb-8">
          <p className="text-[#545454] text-center leading-relaxed" style={{ fontFamily: 'Lato, sans-serif' }}>
            You're making great progress! 🚀<br/>
            Ready to unlock unlimited sessions and take your CAT prep to the next level?
          </p>
        </div>

        {/* Benefits highlight */}
        <div className="bg-green-50 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-[#545454] mb-2" style={{ fontFamily: 'Lato, sans-serif' }}>
            🌟 What you'll get with Pro:
          </h3>
          <ul className="text-sm text-[#545454] space-y-1" style={{ fontFamily: 'Lato, sans-serif' }}>
            <li>✅ Unlimited practice sessions</li>
            <li>✅ Advanced adaptive learning</li>
            <li>✅ Detailed progress analytics</li>
            <li>✅ Ask Twelvr - AI doubt resolution</li>
          </ul>
        </div>

        {/* Action buttons */}
        <div className="flex space-x-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 border border-gray-300 text-[#545454] rounded-lg hover:bg-gray-50 transition-colors font-medium"
            style={{ fontFamily: 'Lato, sans-serif' }}
          >
            Maybe Later
          </button>
          <button
            onClick={handleUpgrade}
            className="flex-1 px-4 py-3 bg-[#9ac026] text-white rounded-lg hover:bg-[#8bb024] transition-colors font-semibold"
            style={{ fontFamily: 'Lato, sans-serif' }}
          >
            Upgrade Now 🚀
          </button>
        </div>

        {/* Reassuring note */}
        <p className="text-xs text-gray-500 text-center mt-4" style={{ fontFamily: 'Lato, sans-serif' }}>
          Your progress is saved and you can continue from where you left off
        </p>
      </div>
    </div>
  );
};

export default UpgradeModal;