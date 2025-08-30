import React, { useState } from 'react';
import { useAuth } from './AuthProvider';

const PaymentComponent = ({ planType, amount, planName, description, onSuccess, onError }) => {
  const { API, user } = useAuth();
  const [loading, setLoading] = useState(false);

  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handlePayment = async () => {
    setLoading(true);
    
    try {
      // Load Razorpay script
      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) {
        throw new Error('Failed to load Razorpay SDK');
      }

      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Please login to continue');
      }

      // For Pro Lite, create subscription; for Pro Regular, create order
      const endpoint = planType === 'pro_lite' ? 
        `${API}/api/payments/create-subscription` : 
        `${API}/api/payments/create-order`;

      const requestData = {
        plan_type: planType,
        user_email: user?.email || '',
        user_name: user?.name || '',
        user_phone: user?.phone || ''
      };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Payment initiation failed');
      }

      const result = await response.json();
      
      if (planType === 'pro_lite' && result.data.short_url) {
        // For subscriptions, redirect to Razorpay hosted page
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
        order_id: result.data.order_id,
        
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
          name: result.data.prefill.name,
          email: result.data.prefill.email,
          contact: result.data.prefill.contact
        },
        
        // Success handler
        handler: async (response) => {
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
                user_id: user?.id || ''
              })
            });

            if (!verifyResponse.ok) {
              throw new Error('Payment verification failed');
            }

            const verifyResult = await verifyResponse.json();
            
            if (onSuccess) {
              onSuccess(verifyResult.data);
            }
            
          } catch (error) {
            console.error('Payment verification error:', error);
            if (onError) {
              onError(error.message);
            }
          }
        },
        
        // Error handler
        modal: {
          ondismiss: () => {
            setLoading(false);
            if (onError) {
              onError('Payment cancelled by user');
            }
          }
        }
      };

      const razorpay = new window.Razorpay(options);
      
      razorpay.on('payment.failed', (response) => {
        setLoading(false);
        if (onError) {
          onError(response.error.description || 'Payment failed');
        }
      });

      razorpay.open();
      
    } catch (error) {
      console.error('Payment error:', error);
      setLoading(false);
      if (onError) {
        onError(error.message);
      }
    }
  };

  return (
    <button
      onClick={handlePayment}
      disabled={loading}
      className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
        planType === 'pro_regular' 
          ? 'bg-[#9ac026] text-white hover:bg-[#8bb024]' 
          : 'border-2 border-[#9ac026] text-[#9ac026] hover:bg-[#9ac026] hover:text-white'
      }`}
      style={{ fontFamily: 'Lato, sans-serif' }}
    >
      {loading ? (
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current mr-2"></div>
          {planType === 'pro_lite' ? 'Starting Subscription...' : 'Processing Payment...'}
        </div>
      ) : (
        <>
          {planType === 'pro_lite' ? 'Subscribe to Pro Lite' : 'Choose Pro Regular'}
        </>
      )}
    </button>
  );
};

export default PaymentComponent;