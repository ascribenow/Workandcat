import React from 'react';
import { useNavigate } from 'react-router-dom';

const Pricing = () => {
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
                  src="https://customer-assets.emergentagent.com/job_sleepy-saha/artifacts/ss0tc3jc_Twelver%20edited.png" 
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
                Pricing
              </span>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl lg:text-5xl font-bold mb-6" style={{ color: '#545454' }}>
            Pricing
          </h1>
          <p className="text-xl" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            Choose the perfect plan for your CAT preparation journey
          </p>
        </div>

        <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full flex items-center justify-center" style={{ backgroundColor: '#f7fdf0' }}>
            <svg className="w-8 h-8" style={{ color: '#9ac026' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold mb-4" style={{ color: '#545454' }}>
            Content Coming Soon
          </h2>
          <p className="text-lg mb-6" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            We're crafting the perfect pricing plans for your Daily-12 CAT preparation.
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
    </div>
  );
};

export default Pricing;