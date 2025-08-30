import React from 'react';
import { useNavigate } from 'react-router-dom';

const CancellationRefund = () => {
  const navigate = useNavigate();

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
                Cancellation & Refund
              </span>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl lg:text-5xl font-bold mb-6" style={{ color: '#545454' }}>
            Cancellation & Refund Policy
          </h1>
          <p className="text-xl" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            Our policies for cancellations and refunds
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
              At Twelvr, our services are subscription-based, delivering personalized daily sessions.
            </p>
          </div>

          <div className="space-y-8">
            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>1. Cancellations</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li>You may cancel your subscription at any time through your account settings.</li>
                <li>Cancellation stops auto-renewal but does not entitle you to a refund for prior payments.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>2. Refunds</h2>
              <ul className="space-y-2 text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                <li><strong>Strict No-Refund Policy:</strong> Once a payment is processed, it is non-refundable.</li>
                <li>Partial usage of subscription or dissatisfaction with performance outcomes does not qualify for a refund.</li>
              </ul>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>3. Exceptional Cases</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                If a technical error (such as double billing) occurs, please contact support. Verified cases will be rectified.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>4. Changes to Policy</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                We may update this policy periodically. Continued use of the platform constitutes agreement to the updated policy.
              </p>
            </section>

            <section className="border-t pt-6">
              <h2 className="text-2xl font-bold mb-4" style={{ color: '#545454' }}>Contact</h2>
              <p className="text-gray-700" style={{ fontFamily: 'Lato, sans-serif' }}>
                For billing concerns, reach us at <a href="mailto:support@twelvr.com" className="text-[#9ac026] hover:underline">support@twelvr.com</a>
              </p>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
};

export default CancellationRefund;