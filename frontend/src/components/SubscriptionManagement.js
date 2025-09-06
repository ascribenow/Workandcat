import React, { useState, useEffect } from 'react';
import PauseSubscriptionModal from './PauseSubscriptionModal';

const SubscriptionManagement = () => {
  const [subscriptionInfo, setSubscriptionInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isPauseModalOpen, setIsPauseModalOpen] = useState(false);
  const [error, setError] = useState('');

  const API = process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL;

  useEffect(() => {
    fetchSubscriptionInfo();
  }, []);

  const fetchSubscriptionInfo = async () => {
    try {
      const token = localStorage.getItem('cat_prep_token');
      if (!token) return;

      const response = await fetch(`${API}/api/user/subscription-management`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSubscriptionInfo(data);
      }
    } catch (error) {
      console.error('Error fetching subscription info:', error);
      setError('Unable to load subscription information');
    } finally {
      setLoading(false);
    }
  };

  const handlePauseSubscription = async () => {
    try {
      const token = localStorage.getItem('cat_prep_token');
      const response = await fetch(`${API}/api/user/pause-subscription`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setIsPauseModalOpen(false);
        
        // Show success message
        alert(`Subscription paused successfully! ${data.remaining_days} days have been saved for when you resume.`);
        
        // Refresh subscription info
        fetchSubscriptionInfo();
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to pause subscription');
      }
    } catch (error) {
      console.error('Error pausing subscription:', error);
      alert(`Error: ${error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-3 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (!subscriptionInfo?.has_subscription) {
    return null; // Don't show anything if no subscription
  }

  const subscription = subscriptionInfo.subscription;

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
          Your Subscription
        </h3>
        <div className={`px-3 py-1 rounded-full text-sm font-medium ${
          subscription.is_active 
            ? 'bg-green-100 text-green-800' 
            : subscription.is_paused 
            ? 'bg-orange-100 text-orange-800'
            : 'bg-gray-100 text-gray-800'
        }`}>
          {subscription.is_active ? 'Active' : subscription.is_paused ? 'Paused' : 'Inactive'}
        </div>
      </div>

      {/* Subscription Details */}
      <div className="space-y-3 mb-6">
        <div className="flex justify-between items-center">
          <span className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>Plan:</span>
          <span className="font-semibold" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            {subscription.plan_type === 'pro_regular' ? 'Pro Regular' : 'Pro Exclusive'}
          </span>
        </div>

        {subscription.is_active && (
          <div className="flex justify-between items-center">
            <span className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>Days Remaining:</span>
            <span className="font-semibold text-[#9ac026]" style={{ fontFamily: 'Lato, sans-serif' }}>
              {subscription.days_remaining} days
            </span>
          </div>
        )}

        {subscription.is_paused && (
          <div className="flex justify-between items-center">
            <span className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>Balance Days:</span>
            <span className="font-semibold text-orange-600" style={{ fontFamily: 'Lato, sans-serif' }}>
              {subscription.paused_days_remaining} days saved
            </span>
          </div>
        )}

        <div className="flex justify-between items-center">
          <span className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>Auto-Renew:</span>
          <span className="font-semibold" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            {subscription.auto_renew ? 'Yes' : 'No'}
          </span>
        </div>
      </div>

      {/* Action Buttons */}
      {subscription.plan_type === 'pro_regular' && (
        <div className="border-t border-gray-200 pt-4">
          {subscription.can_pause && (
            <button
              onClick={() => setIsPauseModalOpen(true)}
              className="w-full px-4 py-3 bg-orange-50 text-orange-700 border border-orange-200 rounded-lg font-semibold hover:bg-orange-100 transition-colors"
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              <div className="flex items-center justify-center">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Pause Subscription
              </div>
            </button>
          )}

          {subscription.can_resume && (
            <div className="space-y-3">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800" style={{ fontFamily: 'Lato, sans-serif' }}>
                  <strong>Resume Available:</strong> You have {subscription.paused_days_remaining} balance days waiting. 
                  Resume to get {30 + subscription.paused_days_remaining} total days for ₹1,495.
                </p>
              </div>
              <button
                onClick={() => {
                  // Navigate to resume payment flow
                  window.location.href = '/resume-subscription';
                }}
                className="w-full px-4 py-3 bg-[#9ac026] text-white rounded-lg font-semibold hover:bg-[#8bb024] transition-colors"
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                <div className="flex items-center justify-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293H15M9 10v4m6-4v4" />
                  </svg>
                  Resume Subscription
                </div>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Pause Modal */}
      <PauseSubscriptionModal
        isOpen={isPauseModalOpen}
        onClose={() => setIsPauseModalOpen(false)}
        onConfirmPause={handlePauseSubscription}
      />

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-600 text-sm" style={{ fontFamily: 'Lato, sans-serif' }}>
            {error}
          </p>
        </div>
      )}
    </div>
  );
};

export default SubscriptionManagement;