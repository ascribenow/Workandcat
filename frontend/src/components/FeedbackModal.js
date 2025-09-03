import React, { useState } from 'react';

const FeedbackModal = ({ isOpen, onClose }) => {
  const [feedback, setFeedback] = useState('');
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [error, setError] = useState('');

  const maxCharacters = 1000;
  const isSubmitDisabled = !feedback.trim() || isSubmitting;

  const API = process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL;

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!feedback.trim()) {
      setError('Feedback is required');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const response = await fetch(`${API}/api/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          feedback: feedback.trim(),
          user_email: email.trim() || null
        })
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      // Show success message
      setShowSuccess(true);
      
      // Auto-close modal after 3 seconds
      setTimeout(() => {
        handleClose();
      }, 3000);

    } catch (err) {
      setError('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFeedback('');
    setEmail('');
    setError('');
    setShowSuccess(false);
    setIsSubmitting(false);
    onClose();
  };

  const handleFeedbackChange = (e) => {
    if (e.target.value.length <= maxCharacters) {
      setFeedback(e.target.value);
      setError('');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
              Share Your Feedback
            </h2>
            <button
              onClick={handleClose}
              disabled={isSubmitting}
              className="text-gray-400 hover:text-gray-600 text-2xl font-light disabled:opacity-50"
            >
              ×
            </button>
          </div>
          <p className="text-gray-600 mt-2" style={{ fontFamily: 'Lato, sans-serif' }}>
            Help us make Twelvr better for your CAT journey
          </p>
        </div>

        {/* Success Message */}
        {showSuccess && (
          <div className="p-6">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center" style={{ backgroundColor: '#f0f9ff' }}>
                <svg className="w-8 h-8 text-[#9ac026]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2" style={{ color: '#545454' }}>
                Thank You! 🎉
              </h3>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                Your feedback is incredibly valuable to us! Every suggestion helps us build better tools for CAT aspirants like you. We review every piece of feedback and many suggestions make it into Twelvr.
              </p>
              <p className="text-sm text-gray-500 mt-3" style={{ fontFamily: 'Lato, sans-serif' }}>
                This window will close automatically...
              </p>
            </div>
          </div>
        )}

        {/* Form */}
        {!showSuccess && (
          <form onSubmit={handleSubmit} className="p-6">
            {/* Feedback Text Area */}
            <div className="mb-4">
              <label htmlFor="feedback" className="block text-sm font-semibold mb-2" style={{ color: '#545454' }}>
                Your Feedback *
              </label>
              <textarea
                id="feedback"
                value={feedback}
                onChange={handleFeedbackChange}
                placeholder="Tell us what's working, what isn't, or what you'd love to see in Twelvr..."
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#9ac026] focus:border-transparent resize-none"
                rows={5}
                style={{ fontFamily: 'Lato, sans-serif' }}
                disabled={isSubmitting}
              />
              <div className="flex justify-between items-center mt-1">
                <span className={`text-xs ${feedback.length > maxCharacters * 0.9 ? 'text-red-500' : 'text-gray-400'}`}>
                  {feedback.length}/{maxCharacters} characters
                </span>
                {feedback.length >= maxCharacters && (
                  <span className="text-xs text-red-500">Character limit reached</span>
                )}
              </div>
            </div>

            {/* Email Field */}
            <div className="mb-6">
              <label htmlFor="email" className="block text-sm font-semibold mb-2" style={{ color: '#545454' }}>
                Your Email <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@example.com"
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#9ac026] focus:border-transparent"
                style={{ fontFamily: 'Lato, sans-serif' }}
                disabled={isSubmitting}
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave your email if you'd like us to follow up on your feedback
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-600 text-sm" style={{ fontFamily: 'Lato, sans-serif' }}>
                  {error}
                </p>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSubmitting}
                className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors disabled:opacity-50"
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitDisabled}
                className={`flex-1 px-4 py-3 rounded-lg font-semibold transition-colors ${
                  isSubmitDisabled
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-[#9ac026] text-white hover:bg-[#8bb024]'
                }`}
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                {isSubmitting ? (
                  <div className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Sending...
                  </div>
                ) : (
                  'Send Feedback'
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default FeedbackModal;