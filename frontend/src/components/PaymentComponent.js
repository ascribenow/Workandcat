import React, { useState } from 'react';
import { useAuth } from './AuthProvider';
import { API } from './AuthProvider';

const PaymentComponent = ({ planType, amount, planName, description, onSuccess, onError }) => {
  const { user, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);

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

  const handlePayment = async () => {
    console.log('Payment button clicked for plan:', planType);
    setLoading(true);
    
    try {
      // Check authentication first
      const token = localStorage.getItem('cat_prep_token');
      if (!token || !isAuthenticated()) {
        alert('Please login to purchase a plan');
        setLoading(false);
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

      // For Pro Lite, create subscription; for Pro Regular, create order
      const endpoint = planType === 'pro_lite' ? 
        `${API}/api/payments/create-subscription` : 
        `${API}/api/payments/create-order`;

      const requestData = {
        plan_type: planType,
        user_email: user?.email || '',
        user_name: user?.name || user?.full_name || '',
        user_phone: user?.phone || ''
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
      
      if (planType === 'pro_lite' && result.data.short_url) {
        // For subscriptions, redirect to Razorpay hosted page
        console.log('Redirecting to subscription URL:', result.data.short_url);
        window.open(result.data.short_url, '_blank');
        setLoading(false);
        return;
      }

      // For one-time payments (Pro Regular), open Razorpay checkout
      const options = {
        key: result.data.key,
        amount: result.data.amount,
        currency: 'INR',
        name: 'Twelvr',
        description: result.data.description,
        image: '/favicon.png', // Your logo
        order_id: result.data.order_id || result.data.id,
        
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
          name: result.data.prefill?.name || user?.name || user?.full_name || '',
          email: result.data.prefill?.email || user?.email || '',
          contact: result.data.prefill?.contact || user?.phone || ''
        },
        
        // Success handler
        handler: async (response) => {
          console.log('Payment successful:', response);
          try {
            // Verify payment
            const verifyResponse = await fetch(`${API}/api/payments/verify-payment`, {
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

  return (
    <button
      onClick={handlePayment}
      disabled={loading}
      className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
        planType === 'pro_regular' 
          ? 'bg-[#9ac026] text-white hover:bg-[#8bb024] disabled:bg-gray-400' 
          : 'border-2 border-[#9ac026] text-[#9ac026] hover:bg-[#9ac026] hover:text-white disabled:border-gray-400 disabled:text-gray-400'
      }`}
      style={{ fontFamily: 'Lato, sans-serif' }}
    >
      {loading ? (
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current mr-2"></div>
          {planType === 'pro_lite' ? 'Starting Subscription...' : 'Processing Payment...'}
        </div>
      ) : !localStorage.getItem('token') ? (
        <>
          {planType === 'pro_lite' ? 'Login to Subscribe' : 'Login to Purchase'}
        </>
      ) : (
        <>
          {planType === 'pro_lite' ? 'Subscribe to Pro Lite' : 'Choose Pro Regular'}
        </>
      )}
    </button>
  );
};

export default PaymentComponent;