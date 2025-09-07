import React from 'react';
import { useNavigate } from 'react-router-dom';

const PrivacyPolicy = () => {
  const navigate = useNavigate();

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
        <div className="text-center mb-12">
          <h1 className="text-4xl lg:text-5xl font-bold mb-6" style={{ color: '#545454' }}>
            Privacy Policy
          </h1>
          <p className="text-xl" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            How we protect and handle your personal information
          </p>
        </div>

        <div className="prose prose-lg max-w-none">
          <div className="mb-8">
            <p className="text-gray-600 mb-4" style={{ fontFamily: 'Lato, sans-serif' }}>
              <strong>Effective Date:</strong> 01 Aug 2025
            </p>
            <p className="text-gray-600 mb-6" style={{ fontFamily: 'Lato, sans-serif' }}>
              <strong>Company:</strong> M/s Costo Digital ("we," "our," or "us")
            </p>
            <p className="text-lg" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
              At M/s Costo Digital, we value your trust. This Privacy Policy explains how we collect, use, and protect your information when you use our platform, Twelvr.
            </p>
          </div>

          <div className="space-y-8">
            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>1. Information We Collect</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li><strong>Account Information:</strong> Name, email, and password when you register.</li>
                <li><strong>Usage Data:</strong> Questions attempted, accuracy, time spent, performance trends.</li>
                <li><strong>Device Data:</strong> IP address, browser type, operating system.</li>
                <li><strong>Payment Information:</strong> Processed securely via third-party payment gateways.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>2. How We Use Your Information</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li>To personalize your daily 12-question sessions.</li>
                <li>To track progress, mastery, and learning outcomes.</li>
                <li>To improve our algorithms and platform experience.</li>
                <li>To communicate updates, features, or offers.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>3. Data Sharing</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li>We do not sell your personal data.</li>
                <li>Payment data is handled only by trusted, PCI-compliant payment processors.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>4. Data Security</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                We use industry-standard encryption and secure servers. While we strive for best practices, no system is 100% secure.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>5. User Rights</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li>You may request to access, update, or delete your personal information.</li>
                <li>You may opt out of promotional communication at any time.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>6. Changes</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                We may update this policy from time to time. Users will be notified via email or platform updates.
              </p>
            </section>

            <section className="border-t pt-6">
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>Contact</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                For privacy concerns, reach us at <a href="mailto:hello@twelvr.com" className="text-[#9ac026] hover:underline">hello@twelvr.com</a>
              </p>
            </section>
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
              Start My Daily-12
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
              <button onClick={() => navigateToPage('/contact')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Contact Us
              </button>
              <span className="text-[#9ac026] font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Privacy Policy
              </span>
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

export default PrivacyPolicy;