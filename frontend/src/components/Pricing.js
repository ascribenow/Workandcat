import React from 'react';
import { useNavigate } from 'react-router-dom';

const Pricing = () => {
  const navigate = useNavigate();

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
      {/* Header - Same as Landing Page */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            {/* Logo - Clickable to scroll to top */}
            <div className="flex items-center">
              <button onClick={() => navigate('/')} className="focus:outline-none">
                <img 
                  src="https://customer-assets.emergentagent.com/job_adaptive-cat/artifacts/vv2teh18_Twelver%20edited.png" 
                  alt="Twelvr" 
                  className="h-16 sm:h-20 md:h-24 lg:h-28 w-auto cursor-pointer hover:opacity-80 transition-opacity"
                />
              </button>
            </div>
            
            {/* Navigation */}
            <nav className="hidden md:flex items-center space-x-8">
              <button onClick={() => navigate('/')} className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                How It Works
              </button>
              <button onClick={() => navigate('/')} className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Why 12 Works
              </button>
              <span className="text-[#9ac026] font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pricing
              </span>
            </nav>
          </div>
        </div>
      </header>

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
                  Mindprint Engine included
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Basic progress tracking
                </span>
              </div>
            </div>

            <button 
              className="w-full py-3 px-6 border-2 border-[#9ac026] text-[#9ac026] rounded-lg font-semibold hover:bg-[#9ac026] hover:text-white transition-colors"
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              Start Free Trial
            </button>
          </div>

          {/* Pro Lite - Most Popular */}
          <div className="bg-white border-2 border-[#9ac026] rounded-2xl p-8 text-center relative shadow-lg transform scale-105">
            <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
              <span className="bg-[#9ac026] text-white px-4 py-1 rounded-full text-sm font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Most Popular
              </span>
            </div>
            
            <div className="mb-6 mt-4">
              <h3 className="text-2xl font-bold mb-2" style={{ color: '#545454' }}>Pro Lite</h3>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                For focused, consistent prep
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
                  Unlimited Daily-12 sessions
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Full Mindprint Engine + Reflex Loop
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Advanced progress analytics
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  CAT Trend Matrix insights
                </span>
              </div>
            </div>

            <button 
              className="w-full py-3 px-6 bg-[#9ac026] text-white rounded-lg font-semibold hover:bg-[#8bb024] transition-colors"
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              Choose Pro Lite
            </button>
          </div>

          {/* Pro Regular */}
          <div className="bg-white border-2 border-gray-200 rounded-2xl p-8 text-center hover:border-[#9ac026] transition-colors">
            <div className="mb-6">
              <h3 className="text-2xl font-bold mb-2" style={{ color: '#545454' }}>Pro Regular</h3>
              <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
                For intensive CAT preparation
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
                  Unlimited Daily-12 sessions
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Complete AI suite (all engines)
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
                  Extended CAT readiness tracking
                </span>
              </div>
              <div className="flex items-center">
                <svg className="w-5 h-5 text-[#9ac026] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-left" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Priority support
                </span>
              </div>
            </div>

            <button 
              className="w-full py-3 px-6 border-2 border-[#9ac026] text-[#9ac026] rounded-lg font-semibold hover:bg-[#9ac026] hover:text-white transition-colors"
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              Choose Pro Regular
            </button>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12" style={{ color: '#545454' }}>
            Frequently Asked Questions
          </h2>
          
          <div className="space-y-8">
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
              <button onClick={() => navigate('/contact')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Contact Us
              </button>
              <button onClick={() => navigate('/privacy')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Privacy Policy
              </button>
              <button onClick={() => navigate('/terms')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Terms & Conditions
              </button>
              <button onClick={() => navigate('/refund')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
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