import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';

const PaymentComponent = ({ planType, amount, planName, description, onSuccess, onError }) => {
  const { API, user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [referralCode, setReferralCode] = useState('');
  const [validatingReferral, setValidatingReferral] = useState(false);
  const [referralValidation, setReferralValidation] = useState(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      // Check if Razorpay is already loaded
      if (window.Razorpay) {
        resolve(true);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const validateReferralCode = async (code) => {
    if (!code || code.length !== 6) {
      setReferralValidation(null);
      return;
    }

    setValidatingReferral(true);
    try {
      const token = localStorage.getItem('cat_prep_token');
      const response = await fetch(`${API}/referral/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          referral_code: code,
          user_email: user?.email || ''
        })
      });

      const result = await response.json();
      setReferralValidation(result);
    } catch (error) {
      console.error('Error validating referral code:', error);
      setReferralValidation({
        valid: false,
        can_use: false,
        error: 'Error validating referral code'
      });
    } finally {
      setValidatingReferral(false);
    }
  };

  const handlePayment = async () => {
    console.log('Payment button clicked for plan:', planType);
    setLoading(true);
    
    try {
      // Check authentication first
      const token = localStorage.getItem('cat_prep_token');
      if (!token || !isAuthenticated()) {
        alert('Please login to purchase a plan');
        setLoading(false);
        // Redirect to landing page for sign-in
        navigate('/');
        return;
      }

      if (!user) {
        alert('User data not loaded. Please refresh and try again.');
        setLoading(false);
        return;
      }

      console.log('User authenticated:', user);

      // Load Razorpay script
      console.log('Loading Razorpay script...');
      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) {
        throw new Error('Failed to load Razorpay SDK. Please check your internet connection.');
      }
      console.log('Razorpay script loaded successfully');

      // For Pro Regular, create subscription; for Pro Exclusive, create order
      const endpoint = planType === 'pro_regular' ? 
        `${API}/payments/create-subscription` : 
        `${API}/payments/create-order`;

      const requestData = {
        plan_type: planType,
        user_email: user?.email || '',
        user_name: user?.name || user?.full_name || '',
        user_phone: user?.phone || '',
        referral_code: referralCode || null
      };

      console.log('Making API call to:', endpoint);
      console.log('Request data:', requestData);

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestData)
      });

      console.log('API response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        console.error('API error:', errorData);
        throw new Error(errorData.detail || 'Payment initiation failed');
      }

      const result = await response.json();
      console.log('Payment data received:', result);
      
      // Handle subscription-style payment or one-time payment
      if (planType === 'pro_regular') {
        if (result.short_url) {
          // For true subscriptions, redirect to Razorpay hosted page
          console.log('Redirecting to subscription URL:', result.short_url);
          window.open(result.short_url, '_blank');
          setLoading(false);
          return;
        } else if (result.subscription_style) {
          // For subscription-style one-time payment, show message
          console.log('Pro Regular subscription-style payment:', result.message);
        }
      }

      // For one-time payments (Pro Exclusive), open Razorpay checkout
      const options = {
        key: result.key,
        amount: result.amount,
        currency: 'INR',
        name: 'Twelvr',
        description: result.description,
        image: '/favicon.png', // Your logo
        order_id: result.order_id || result.id,
        
        // Payment methods configuration
        method: {
          card: true,
          netbanking: true,
          wallet: true,
          upi: true,
          emi: false // Disable EMI for smaller amounts if needed
        },
        
        // Theme
        theme: {
          color: '#9ac026'
        },
        
        // Modal settings
        modal: {
          backdropclose: false,
          escape: true,
          handleback: true
        },
        
        // Prefill user data
        prefill: {
          name: result.prefill?.name || user?.name || user?.full_name || '',
          email: result.prefill?.email || user?.email || '',
          contact: result.prefill?.contact || user?.phone || ''
        },
        
        // Success handler
        handler: async (response) => {
          console.log('Payment successful:', response);
          try {
            // Verify payment
            const verifyResponse = await fetch(`${API}/payments/verify-payment`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                user_id: user?.id || user?.user_id || ''
              })
            });

            if (!verifyResponse.ok) {
              throw new Error('Payment verification failed');
            }

            const verifyResult = await verifyResponse.json();
            console.log('Payment verified:', verifyResult);
            
            if (onSuccess) {
              onSuccess(verifyResult.data);
            } else {
              alert('Payment successful! Redirecting to dashboard...');
              window.location.href = '/dashboard';
            }
            
          } catch (error) {
            console.error('Payment verification error:', error);
            if (onError) {
              onError(error.message);
            } else {
              alert('Payment completed but verification failed. Please contact support.');
            }
          }
        },
        
        // Error handler
        modal: {
          ondismiss: () => {
            console.log('Payment modal dismissed');
            setLoading(false);
            if (onError) {
              onError('Payment cancelled by user');
            }
          }
        }
      };

      console.log('Opening Razorpay checkout with options:', options);
      const razorpay = new window.Razorpay(options);
      
      razorpay.on('payment.failed', (response) => {
        console.error('Payment failed:', response);
        setLoading(false);
        if (onError) {
          onError(response.error.description || 'Payment failed');
        } else {
          alert('Payment failed: ' + (response.error.description || 'Unknown error'));
        }
      });

      razorpay.open();
      
    } catch (error) {
      console.error('Payment error:', error);
      setLoading(false);
      if (onError) {
        onError(error.message);
      } else {
        alert('Payment initiation failed: ' + error.message);
      }
    }
  };

  const handleButtonClick = () => {
    const token = localStorage.getItem('cat_prep_token');
    if (!token || !isAuthenticated()) {
      alert('Please login to purchase a plan');
      // Redirect to landing page for sign-in
      navigate('/');
      return;
    }
    setShowPaymentModal(true);
  };

  const calculateDiscountedAmount = () => {
    // SECURITY: Frontend should NEVER calculate amounts
    // Display amounts should come from backend validation response only
    if (referralValidation && referralValidation.valid && referralValidation.can_use) {
      // Show discount amount from backend validation response
      return referralValidation.discounted_amount || amount;
    }
    return amount;
  };

  return (
    <>
      <button
        onClick={handleButtonClick}
        disabled={loading}
        className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
          planType === 'pro_exclusive' 
            ? 'bg-[#9ac026] text-white hover:bg-[#8bb024] disabled:bg-gray-400' 
            : 'border-2 border-[#9ac026] text-[#9ac026] hover:bg-[#9ac026] hover:text-white disabled:border-gray-400 disabled:text-gray-400'
        }`}
        style={{ fontFamily: 'Lato, sans-serif' }}
      >
        {!localStorage.getItem('cat_prep_token') || !isAuthenticated() ? (
          <>
            {planType === 'pro_regular' ? 'Login to Subscribe' : 'Login to Purchase'}
          </>
        ) : (
          <>
            {planType === 'pro_regular' ? 'Subscribe to Pro Regular' : 'Choose Pro Exclusive'}
          </>
        )}
      </button>

      {/* Payment Modal */}
      {showPaymentModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-gray-800">{planName}</h3>
              <button
                onClick={() => setShowPaymentModal(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>

            <div className="mb-4">
              <p className="text-gray-600 mb-2">{description}</p>
              <div className="flex items-center justify-between">
                <span className="text-lg font-semibold">Amount:</span>
                <div className="text-right">
                  {referralValidation && referralValidation.valid && referralValidation.can_use ? (
                    <>
                      <span className="text-gray-400 line-through text-sm">₹{(amount/100).toFixed(0)}</span>
                      <span className="text-green-600 font-bold text-lg ml-2">₹{(calculateDiscountedAmount()/100).toFixed(0)}</span>
                      <div className="text-green-600 text-sm">₹500 referral discount applied!</div>
                    </>
                  ) : (
                    <span className="text-lg font-bold">₹{(amount/100).toFixed(0)}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Referral Code Input */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Referral Code (Optional)
                <span className="text-gray-500 font-normal"> - Get ₹500 off</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={referralCode}
                  onChange={(e) => {
                    const code = e.target.value.toUpperCase().slice(0, 6);
                    setReferralCode(code);
                    if (code.length === 6) {
                      validateReferralCode(code);
                    } else {
                      setReferralValidation(null);
                    }
                  }}
                  placeholder="Enter 6-character code"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#9ac026] focus:border-transparent"
                  maxLength={6}
                />
                {validatingReferral && (
                  <div className="absolute right-2 top-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#9ac026]"></div>
                  </div>
                )}
              </div>
              
              {/* Referral Validation Messages */}
              {referralValidation && (
                <div className={`mt-2 text-sm ${referralValidation.valid && referralValidation.can_use ? 'text-green-600' : 'text-red-600'}`}>
                  {referralValidation.valid && referralValidation.can_use ? (
                    <div className="flex items-center">
                      <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      Valid! You'll save ₹500 on this purchase.
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      {referralValidation.error}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Payment Button */}
            <button
              onClick={() => {
                setShowPaymentModal(false);
                handlePayment();
              }}
              disabled={loading}
              className="w-full py-3 px-6 bg-[#9ac026] text-white rounded-lg font-semibold hover:bg-[#8bb024] disabled:bg-gray-400 transition-colors"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current mr-2"></div>
                  {planType === 'pro_regular' ? 'Starting Subscription...' : 'Processing Payment...'}
                </div>
              ) : (
                <>
                  {planType === 'pro_regular' ? 'Subscribe Now' : 'Pay Now'} - ₹{(calculateDiscountedAmount()/100).toFixed(0)}
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default PaymentComponent;