import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FeedbackModal from './FeedbackModal';

const ContactUs = () => {
  const navigate = useNavigate();
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);

  // Navigation with scroll to top
  const navigateToPage = (path) => {
    navigate(path);
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
              <button onClick={() => navigate('/pricing')} className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pricing
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl lg:text-5xl font-bold mb-6" style={{ color: '#545454' }}>
            We're Here to Help
          </h1>
          <p className="text-xl" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            Questions, doubts, or just want to chat? Our team is ready to support your CAT journey
          </p>
        </div>

        {/* Support Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
          
          {/* Technical Support */}
          <div className="bg-white border-2 border-gray-200 rounded-2xl p-8 hover:border-[#9ac026] transition-colors">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full flex items-center justify-center" style={{ backgroundColor: '#f0f9ff' }}>
              <svg className="w-8 h-8 text-[#9ac026]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold mb-4 text-center" style={{ color: '#545454' }}>
              Real Time Support
            </h3>
            <p className="text-gray-600 mb-6 text-center" style={{ fontFamily: 'Lato, sans-serif' }}>
              Stuck with a login issue? Payment not going through? Session not loading? Our tech team is standing by to help you get back on track, fast.
            </p>
            <div className="text-center">
              <a 
                href="mailto:hello@twelvr.com"
                className="inline-flex items-center px-6 py-3 bg-[#9ac026] text-white rounded-lg font-semibold hover:bg-[#8bb024] transition-colors"
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                hello@twelvr.com
              </a>
            </div>
          </div>

          {/* Student Feedback */}
          <div className="bg-white border-2 border-gray-200 rounded-2xl p-8 hover:border-[#9ac026] transition-colors">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full flex items-center justify-center" style={{ backgroundColor: '#fef7ff' }}>
              <svg className="w-8 h-8 text-[#9ac026]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold mb-4 text-center" style={{ color: '#545454' }}>
              Share Your Experience
            </h3>
            <p className="text-gray-600 mb-6 text-center" style={{ fontFamily: 'Lato, sans-serif' }}>
              Your feedback shapes Twelvr! Tell us what's working, what isn't, and what you'd love to see. Every student voice helps us build better prep tools.
            </p>
            <div className="text-center">
              <button 
                onClick={() => setIsFeedbackModalOpen(true)}
                className="inline-flex items-center px-6 py-3 border-2 border-[#9ac026] text-[#9ac026] rounded-lg font-semibold hover:bg-[#9ac026] hover:text-white transition-colors"
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                Send Feedback
              </button>
            </div>
          </div>
        </div>

        {/* Response Time Notice */}
        <div className="bg-gradient-to-r from-[#9ac026] to-[#8bb024] rounded-2xl p-8 text-center text-white mb-16">
          <h2 className="text-3xl font-bold mb-4">
            Quick Response Guarantee
          </h2>
          <p className="text-lg mb-4" style={{ fontFamily: 'Lato, sans-serif' }}>
            We typically respond within <strong>2-4 hours</strong> during weekdays, because we know every moment counts in your CAT prep journey.
          </p>
          <p className="text-sm opacity-90" style={{ fontFamily: 'Lato, sans-serif' }}>
            Weekend responses might take a bit longer, but we're never too far away from helping a fellow CAT aspirant!
          </p>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12" style={{ color: '#545454' }}>
            Quick Answers
          </h2>
          
          <div className="space-y-6">
            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-3" style={{ color: '#545454' }}>
                "My 12 session isn't loading. What should I do?"
              </h3>
              <p style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                Try refreshing the page first. If that doesn't work, clear your browser cache or try a different browser. Still stuck? Email us immediately at hello@twelvr.com - we'll get you back to your session in minutes.
              </p>
            </div>

            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-3" style={{ color: '#545454' }}>
                "I want to suggest a new feature. How?"
              </h3>
              <p style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                We love feature requests! Email us at hello@twelvr.com with "Feature Request" in the subject line. Be as detailed as you want - we read every single suggestion and many have made it into Twelvr.
              </p>
            </div>

            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-3" style={{ color: '#545454' }}>
                "Can I talk to someone on the phone?"
              </h3>
              <p style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                Right now, we handle support through email for faster response times and better issue tracking. Email hello@twelvr.com and we'll get back to you super quickly - often faster than a phone call!
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
              <em>You, Compounded.</em>
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
              Start My 12
            </button>

            {/* Disclaimer */}
            <p className="text-sm text-gray-300 max-w-2xl mb-8" style={{ fontFamily: 'Lato, sans-serif' }}>
              Twelvr complements your CAT prep — it doesn't replace books or coaching.
            </p>

            {/* Footer Navigation */}
            <nav className="flex flex-wrap justify-center gap-6">
              <button onClick={() => navigateToPage('/pricing')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pricing
              </button>
              <span className="text-[#9ac026] font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Contact Us
              </span>
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

      {/* Feedback Modal */}
      <FeedbackModal 
        isOpen={isFeedbackModalOpen} 
        onClose={() => setIsFeedbackModalOpen(false)} 
      />
    </div>
  );
};

export default ContactUs;