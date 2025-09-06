import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from './Header';
import PaymentComponent from './PaymentComponent';
import { getPlanContext, clearPlanContext, PLAN_TYPES } from '../utils/planContext';

const Pricing = () => {
  const navigate = useNavigate();
  const [paymentStatus, setPaymentStatus] = useState({ message: '', type: '' });
  const [highlightedPlan, setHighlightedPlan] = useState(null);

  // Check for plan context on component mount
  useEffect(() => {
    const planContext = getPlanContext();
    if (planContext) {
      setHighlightedPlan(planContext.planType);
      setPaymentStatus({
        message: `Complete your ${planContext.planType === PLAN_TYPES.PRO_REGULAR ? 'Pro Regular' : 'Pro Exclusive'} purchase within ${Math.floor((planContext.expiresAt - Date.now()) / (60 * 1000))} minutes.`,
        type: 'info'
      });
      
      // Clear the context after showing the message
      setTimeout(() => {
        clearPlanContext();
        setPaymentStatus({ message: '', type: '' });
      }, 5000);
    }
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Navigation with scroll to top
  const navigateToPage = (path) => {
    navigate(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePaymentSuccess = (paymentData) => {
    setPaymentStatus({
      message: 'Payment successful! Your subscription is now active.',
      type: 'success'
    });
    
    // Redirect to dashboard after 3 seconds
    setTimeout(() => {
      navigate('/dashboard');
    }, 3000);
  };

  const handlePaymentError = (errorMessage) => {
    setPaymentStatus({
      message: errorMessage || 'Payment failed. Please try again.',
      type: 'error'
    });
    
    // Clear error message after 5 seconds
    setTimeout(() => {
      setPaymentStatus({ message: '', type: '' });
    }, 5000);
  };

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
      {/* Header using shared component */}
      <Header />

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl lg:text-5xl font-bold mb-6" style={{ color: '#545454' }}>
            Choose Your Daily-12 Plan
          </h1>
          <p className="text-xl" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            Consistent prep, smart pricing, serious results
          </p>
        </div>

        {/* Payment Status Messages */}
        {paymentStatus.message && (
          <div className={`mb-8 p-4 rounded-lg border ${
            paymentStatus.type === 'success' 
              ? 'bg-green-50 border-green-200 text-green-800' 
              : paymentStatus.type === 'info'
              ? 'bg-blue-50 border-blue-200 text-blue-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            <div className="flex items-center">
              {paymentStatus.type === 'success' ? (
                <svg className="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : paymentStatus.type === 'info' ? (
                <svg className="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              )}
              <p style={{ fontFamily: 'Lato, sans-serif' }}>{paymentStatus.message}</p>
            </div>
          </div>
        )}

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          
          {/* Free Trial */}
          <div className="bg-white border-2 border-gray-200 rounded-2xl p-8 text-center hover:border-[#9ac026] transition-colors">
            <div className="mb-6">
              <h3 className="text-2xl font-bold mb-2" style={{ color: '#545454' }}>Free Trial</h3>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                Perfect for testing the waters
              </p>
            </div>
            
            <div className="mb-8">
              <div className="flex items-baseline justify-center mb-2">
                <span className="text-5xl font-bold" style={{ color: '#545454' }}>₹0</span>
              </div>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                30 sessions total
              </p>
            </div>

            <div className="space-y-4 mb-8">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  30 adaptive Daily-12 sessions
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Limited Adaptive (Mindprint)
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Progress dashboard & analytics
                </span>
              </div>
            </div>

            <button 
              onClick={() => {
                // Check if user is authenticated
                // For now, redirect to home page for signup - this can be enhanced later
                navigate('/');
              }}
              className="w-full py-3 px-6 border-2 border-[#9ac026] text-[#9ac026] rounded-lg font-semibold hover:bg-[#9ac026] hover:text-white transition-colors"
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              Start Free Trial
            </button>
          </div>

          {/* Pro Lite */}
          <div className={`bg-white border-2 rounded-2xl p-8 text-center hover:border-[#9ac026] transition-colors ${
            highlightedPlan === PLAN_TYPES.PRO_LITE ? 'border-[#9ac026] ring-2 ring-[#9ac026] ring-opacity-20' : 'border-gray-200'
          }`}>
            <div className="mb-6">
              <h3 className="text-2xl font-bold mb-2" style={{ color: '#545454' }}>Pro Lite</h3>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                For long-term prep spaced across months
              </p>
            </div>
            
            <div className="mb-8">
              <div className="flex items-baseline justify-center mb-2">
                <span className="text-5xl font-bold" style={{ color: '#545454' }}>₹1,495</span>
              </div>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                30 days, unlimited sessions
              </p>
            </div>

            <div className="space-y-4 mb-8">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Unlimited Daily-12 sessions (30 days)
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Full Adaptivity (Trend Matrix + Reflex Loop + Learning Impact)
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Progress dashboard & analytics
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Comprehensive performance reports
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Renews every month, pause anytime
                </span>
              </div>
            </div>

            <PaymentComponent
              planType="pro_lite"
              amount={149500}
              planName="Pro Lite"
              description="Pro Lite - Unlimited Daily-12 sessions for 30 days"
              onSuccess={handlePaymentSuccess}
              onError={handlePaymentError}
            />
          </div>

          {/* Pro Regular - Ideal for CAT 2025 */}
          <div className={`bg-white border-2 rounded-2xl p-8 text-center relative shadow-lg transform scale-105 ${
            highlightedPlan === PLAN_TYPES.PRO_REGULAR ? 'border-[#9ac026] ring-2 ring-[#9ac026] ring-opacity-20' : 'border-[#9ac026]'
          }`}>
            <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
              <span className="bg-[#9ac026] text-white px-4 py-1 rounded-full text-sm font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Ideal for CAT 2025
              </span>
            </div>
            
            <div className="mb-6 mt-4">
              <h3 className="text-2xl font-bold mb-2" style={{ color: '#545454' }}>Pro Regular</h3>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                Best for the small time window to CAT 2025
              </p>
            </div>
            
            <div className="mb-8">
              <div className="flex items-baseline justify-center mb-2">
                <span className="text-5xl font-bold" style={{ color: '#545454' }}>₹2,565</span>
              </div>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                60 days, unlimited sessions
              </p>
            </div>

            <div className="space-y-4 mb-8">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Unlimited Daily-12 sessions (60 days)
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Full Adaptivity (Trend Matrix + Reflex Loop + Learning Impact)
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Progress dashboard & analytics
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Comprehensive performance reports
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Full syllabus coverage in 90 sessions (only for Quantitative Ability section)
                </span>
              </div>
              <div className="flex items-center border-l-4 border-[#9ac026] pl-2 bg-gray-50 rounded-r-md py-2">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left font-medium" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Ask Twelvr: Real-time doubt resolution per question
                </span>
              </div>
            </div>

            <PaymentComponent
              planType="pro_regular"
              amount={256500}
              planName="Pro Regular"
              description="Pro Regular - Unlimited Daily-12 sessions for 60 days with Ask Twelvr"
              onSuccess={handlePaymentSuccess}
              onError={handlePaymentError}
            />
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12" style={{ color: '#545454' }}>
            Frequently Asked Questions
          </h2>
          
          <div className="space-y-8">
            <div className="bg-gradient-to-r from-orange-50 to-red-50 border border-orange-200 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-3 text-orange-800">
                What sections of CAT does Twelvr cover?
              </h3>
              <p className="text-orange-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <strong>Important:</strong> Twelvr currently focuses exclusively on the <strong>Quantitative Ability (QA)</strong> section of CAT. We do not cover Verbal Ability and Reading Comprehension (VARC) or Data Interpretation and Logical Reasoning (DILR) sections. Our AI-powered system is specifically designed to master QA concepts and problem-solving techniques.
              </p>
            </div>

            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-3" style={{ color: '#545454' }}>
                How does the Free Trial work?
              </h3>
              <p style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                Get 30 complete Daily-12 sessions to experience our adaptive system. No credit card required, no time limits, just 30 high-quality prep sessions to see how Twelvr works for you.
              </p>
            </div>

            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-3" style={{ color: '#545454' }}>
                What's the difference between Pro Lite and Pro Regular?
              </h3>
              <p style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                Pro Lite gives you 30 days of unlimited sessions, perfect for focused monthly prep cycles. Pro Regular extends to 60 days with enhanced analytics and priority support, ideal for comprehensive CAT preparation.
              </p>
            </div>

            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-3" style={{ color: '#545454' }}>
                Can I do more than one session per day?
              </h3>
              <p style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                Absolutely! While our system is designed around the Daily-12 concept, Pro plans give you unlimited sessions. You can do multiple sessions per day to accelerate your preparation.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer - Same as Landing Page */}
      <footer className="bg-[#545454] text-white py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center text-center">
            <div className="flex items-center mb-6">
              <button onClick={() => navigate('/')} className="focus:outline-none">
                <img 
                  src="https://customer-assets.emergentagent.com/job_adaptive-cat/artifacts/5x4yfapf_Twelvr%20logo%20dark%20background.png" 
                  alt="Twelvr" 
                  className="h-12 sm:h-16 w-auto cursor-pointer hover:opacity-80 transition-opacity"
                  style={{ 
                    backgroundColor: 'transparent'
                  }}
                />
              </button>
            </div>
            
            <p className="text-lg mb-8" style={{ fontFamily: 'Lato, sans-serif' }}>
              <em>Consistency, Compounded.</em>
            </p>

            <button 
              onClick={() => navigate('/')}
              className="px-6 py-3 rounded-full font-semibold transition-colors mb-8 text-white"
              style={{ 
                backgroundColor: '#9ac026',
                fontFamily: 'Lato, sans-serif'
              }}
              onMouseOver={(e) => e.target.style.backgroundColor = '#8bb024'}
              onMouseOut={(e) => e.target.style.backgroundColor = '#9ac026'}
            >
              Start My Daily-12
            </button>

            {/* Disclaimer */}
            <p className="text-sm text-gray-300 max-w-2xl mb-8" style={{ fontFamily: 'Lato, sans-serif' }}>
              Twelvr complements your CAT prep — it doesn't replace books or coaching.
            </p>

            {/* Footer Navigation */}
            <nav className="flex flex-wrap justify-center gap-6">
              <span className="text-[#9ac026] font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pricing
              </span>
              <button onClick={() => navigateToPage('/contact')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Contact Us
              </button>
              <button onClick={() => navigateToPage('/privacy')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Privacy Policy
              </button>
              <button onClick={() => navigateToPage('/terms')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Terms & Conditions
              </button>
              <button onClick={() => navigateToPage('/refund')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Cancellation & Refund Policy
              </button>
            </nav>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Pricing;