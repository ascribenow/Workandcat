import React from 'react';
import { useNavigate } from 'react-router-dom';

const TermsConditions = () => {
  const navigate = useNavigate();

  // Navigation with scroll to top
  const navigateToPage = (path) => {
    navigate(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <button onClick={() => navigate('/')} className="focus:outline-none">
                <img 
                  src="https://customer-assets.emergentagent.com/job_adaptive-cat/artifacts/vv2teh18_Twelver%20edited.png" 
                  alt="Twelvr" 
                  className="h-12 sm:h-16 w-auto cursor-pointer hover:opacity-80 transition-opacity"
                />
              </button>
            </div>
            
            <nav className="hidden md:flex items-center space-x-8">
              <button onClick={() => navigate('/')} className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Home
              </button>
              <span className="text-[#9ac026] font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Terms & Conditions
              </span>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl lg:text-5xl font-bold mb-6" style={{ color: '#545454' }}>
            Terms & Conditions
          </h1>
          <p className="text-xl" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            The terms governing your use of Twelvr
          </p>
        </div>

        <div className="prose prose-lg max-w-none">
          <div className="mb-8">
            <p className="text-gray-600 mb-4" style={{ fontFamily: 'Lato, sans-serif' }}>
              <strong>Effective Date:</strong> 01 Aug 2025
            </p>
            <p className="text-gray-600 mb-6" style={{ fontFamily: 'Lato, sans-serif' }}>
              <strong>Company:</strong> M/s Costo Digital
            </p>
            <p className="text-lg" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
              Welcome to Twelvr, an adaptive exam preparation platform. By accessing or using our platform, you agree to these Terms.
            </p>
          </div>

          <div className="space-y-8">
            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>1. Account Responsibilities</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li>Keep your login credentials confidential.</li>
                <li>You are responsible for all activity under your account.</li>
                <li>Notify us immediately of any unauthorized use.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>2. Services Provided</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li>Adaptive question sessions ("My 12") for Quantitative Ability section only.</li>
                <li>Performance tracking, analysis, and recommendations for QA section.</li>
                <li>Access may vary depending on subscription plan.</li>
              </ul>
              <div className="mt-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                <p className="text-orange-800 font-medium" style={{ fontFamily: 'Lato, sans-serif' }}>
                  <strong>Important Notice:</strong> Twelvr currently provides preparation tools exclusively for the Quantitative Ability (QA) section of CAT. We do not cover Verbal Ability and Reading Comprehension (VARC) or Data Interpretation and Logical Reasoning (DILR) sections. Users are advised to seek additional resources for comprehensive CAT preparation covering all sections.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>3. Subscriptions and Payments</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li>Subscription fees are displayed on our website/app.</li>
                <li>Fees are payable in advance and are non-refundable (see Refund Policy).</li>
                <li>We may update pricing with prior notice.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>4. Referral Program</h2>
              <p className="mb-3 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                Twelvr offers a referral program where users can share their unique referral codes with others. The following terms apply:
              </p>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li><strong>Eligibility:</strong> Referral discounts apply only to Pro Regular and Pro Exclusive subscription plans.</li>
                <li><strong>One-time usage:</strong> Each email address can use only one referral code during their entire platform lifetime.</li>
                <li><strong>Self-referral prohibition:</strong> Users cannot use their own referral codes.</li>
                <li><strong>Discount amount:</strong> Valid referral codes provide ₹500 discount on the original plan price.</li>
                <li><strong>Successful payments only:</strong> Referral usage is recorded only after successful payment completion, not during order creation.</li>
                <li><strong>Referrer rewards:</strong> The referral code owner earns ₹500 cashback for each successful use of their code, processed manually by our admin team.</li>
                <li><strong>No stacking:</strong> Referral discounts cannot be combined with other promotions or offers.</li>
                <li><strong>Modification rights:</strong> Twelvr reserves the right to modify or discontinue the referral program at any time with notice.</li>
                <li><strong>Abuse prevention:</strong> Any fraudulent or abusive use of referral codes may result in account suspension and forfeiture of rewards.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>5. Acceptable Use</h2>
              <p className="mb-3 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>You agree not to:</p>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li>Share your account with others.</li>
                <li>Reverse-engineer or misuse our algorithms.</li>
                <li>Use the platform for unlawful purposes.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>6. Intellectual Property</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                All platform content, algorithms, and trademarks are owned by M/s Costo Digital. Users may not copy, distribute, or repurpose platform materials.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>7. Limitation of Liability</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                Twelvr is an aid for exam preparation, not a guarantee of performance. We are not liable for indirect, incidental, or consequential damages.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>8. Termination</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                We may suspend or terminate accounts for violation of these terms.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>9. Governing Law</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                These Terms shall be governed by the laws of India.
              </p>
            </section>

            <section className="border-t pt-6">
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>Contact</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                For queries, reach us at <a href="mailto:hello@twelvr.com" className="text-[#9ac026] hover:underline">hello@twelvr.com</a>
              </p>
            </section>
          </div>
        </div>
      </main>

      {/* Footer - Same as other pages */}
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
              <em>You, compounded.</em>
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
              Twelvr complements your CAT prep, it doesn't replace books or coaching
            </p>

            {/* Footer Navigation */}
            <nav className="flex flex-wrap justify-center gap-6">
              <button onClick={() => navigateToPage('/pricing')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pricing
              </button>
              <button onClick={() => navigateToPage('/contact')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Contact Us
              </button>
              <button onClick={() => navigateToPage('/privacy')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Privacy Policy
              </button>
              <span className="text-[#9ac026] font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
                Terms & Conditions
              </span>
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

export default TermsConditions;