import React from 'react';
import { useNavigate } from 'react-router-dom';

const ContactUs = () => {
  const navigate = useNavigate();

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
        <div className="text-center mb-12">
          <h1 className="text-4xl lg:text-5xl font-bold mb-6" style={{ color: '#545454' }}>
            Contact Us
          </h1>
          <p className="text-xl" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            Get in touch with the Twelvr team
          </p>
        </div>

        <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full flex items-center justify-center" style={{ backgroundColor: '#f7fdf0' }}>
            <svg className="w-8 h-8" style={{ color: '#9ac026' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold mb-4" style={{ color: '#545454' }}>
            Content Coming Soon
          </h2>
          <p className="text-lg mb-6" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            We're setting up multiple ways for you to reach out to us. Stay tuned!
          </p>
          <button 
            onClick={() => navigate('/')}
            className="px-6 py-3 rounded-lg font-semibold transition-colors text-white"
            style={{ backgroundColor: '#9ac026', fontFamily: 'Lato, sans-serif' }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#8bb024'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#9ac026'}
          >
            Back to Home
          </button>
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
              <button onClick={() => navigate('/pricing')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pricing
              </button>
              <span className="text-[#9ac026] font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Contact Us
              </span>
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

export default ContactUs;