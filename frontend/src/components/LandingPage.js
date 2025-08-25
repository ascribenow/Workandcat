import React, { useState } from 'react';
import { useAuth } from './AuthProvider';

const LandingPage = () => {
  const { login, register } = useAuth();
  const [showSignIn, setShowSignIn] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSignIn = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await login(email, password);
    } catch (err) {
      setError('Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await register(name, email, password);
    } catch (err) {
      setError('Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            {/* Logo - Just the Twelvr typeface */}
            <div className="flex items-center">
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold" style={{ 
                color: '#545454',
                fontFamily: 'Manrope, sans-serif',
                letterSpacing: '-0.02em'
              }}>
                Twelvr
              </h1>
            </div>
            
            {/* Navigation */}
            <nav className="hidden md:flex items-center space-x-8">
              <a href="#how-it-works" className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                How It Works
              </a>
              <a href="#why-12" className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Why 12 Works
              </a>
              <a href="#early-access" className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Early Access
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section with Sign-in Panel (Duolingo Style) */}
      <section className="relative bg-gradient-to-br from-gray-50 to-white py-8 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            
            {/* Left Content */}
            <div className="text-center lg:text-left order-2 lg:order-1">
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-[#545454] mb-4 lg:mb-6">
                Your best CAT attempt.{' '}
                <span className="text-[#9ac026]">Just 12 questions a day.</span>
              </h1>
              
              <p className="text-lg lg:text-xl text-[#545454] mb-6 lg:mb-8" style={{ fontFamily: 'Lato, sans-serif' }}>
                12 adaptive questions. 90 days to CAT readiness. Serious prep, simple ritual.
              </p>

              {/* 12 Dots Visual */}
              <div className="flex justify-center lg:justify-start mb-6 lg:mb-8">
                <div className="grid grid-cols-6 gap-1 sm:gap-2">
                  {[...Array(12)].map((_, i) => (
                    <div 
                      key={i} 
                      className="w-2 h-2 sm:w-3 sm:h-3 rounded-full bg-[#9ac026] opacity-80"
                      style={{
                        animationDelay: `${i * 0.1}s`,
                        animation: 'pulse 2s infinite'
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Mobile CTA */}
              <div className="lg:hidden mb-6">
                <button className="bg-[#9ac026] text-white px-6 sm:px-8 py-3 sm:py-4 rounded-full text-base sm:text-lg font-semibold hover:bg-[#8bb024] transition-colors shadow-lg">
                  Start My Daily-12
                </button>
              </div>
            </div>

            {/* Right Sign-in Panel (Duolingo Style) */}
            <div className="flex justify-center lg:justify-end order-1 lg:order-2">
              <div className="bg-white p-6 sm:p-8 rounded-2xl shadow-xl border border-gray-100 w-full max-w-md mx-4 sm:mx-0">
                
                {/* Toggle Buttons */}
                <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => setShowSignIn(true)}
                    className={`flex-1 py-3 px-4 rounded-md text-sm font-medium transition-colors ${
                      showSignIn 
                        ? 'bg-white text-[#545454] shadow-sm' 
                        : 'text-gray-500 hover:text-[#545454]'
                    }`}
                  >
                    Sign In
                  </button>
                  <button
                    onClick={() => setShowSignIn(false)}
                    className={`flex-1 py-3 px-4 rounded-md text-sm font-medium transition-colors ${
                      !showSignIn 
                        ? 'bg-white text-[#545454] shadow-sm' 
                        : 'text-gray-500 hover:text-[#545454]'
                    }`}
                  >
                    Sign Up
                  </button>
                </div>

                {/* Form */}
                <form onSubmit={showSignIn ? handleSignIn : handleSignUp}>
                  <div className="space-y-4">
                    {!showSignIn && (
                      <div>
                        <input
                          type="text"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          placeholder="Full name"
                          className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#9ac026] focus:border-transparent transition-colors"
                          style={{ fontFamily: 'Lato, sans-serif' }}
                          required
                        />
                      </div>
                    )}
                    
                    <div>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="Email address"
                        className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#9ac026] focus:border-transparent transition-colors"
                        style={{ fontFamily: 'Lato, sans-serif' }}
                        required
                      />
                    </div>
                    
                    <div>
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Password"
                        className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#9ac026] focus:border-transparent transition-colors"
                        style={{ fontFamily: 'Lato, sans-serif' }}
                        required
                      />
                    </div>
                  </div>

                  {error && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-600" style={{ fontFamily: 'Lato, sans-serif' }}>{error}</p>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full mt-6 bg-[#9ac026] text-white py-3 rounded-lg font-semibold hover:bg-[#8bb024] transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Loading...' : (showSignIn ? 'Sign In' : 'Start My Daily-12')}
                  </button>
                </form>

                {/* Alternative Sign-in Options */}
                <div className="mt-6">
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-gray-200" />
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="px-2 bg-white text-gray-500" style={{ fontFamily: 'Lato, sans-serif' }}>
                        Or continue with
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <button className="w-full inline-flex justify-center py-3 px-4 border border-gray-200 rounded-lg bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 hover:border-[#ff6d4d] transition-colors">
                      <svg className="h-5 w-5" viewBox="0 0 24 24">
                        <path fill="#4285f4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34a853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#fbbc05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#ea4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                      <span className="ml-2">Google</span>
                    </button>
                    
                    <button className="w-full inline-flex justify-center py-3 px-4 border border-gray-200 rounded-lg bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 hover:border-[#ff6d4d] transition-colors">
                      <svg className="h-5 w-5" fill="#1877f2" viewBox="0 0 24 24">
                        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                      </svg>
                      <span className="ml-2">Facebook</span>
                    </button>
                  </div>
                </div>

                {showSignIn && (
                  <div className="mt-4 text-center">
                    <a href="#" className="text-sm text-[#9ac026] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                      Forgot your password?
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Why Twelvr Section */}
      <section className="py-16 lg:py-24 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl lg:text-5xl font-bold text-[#545454] mb-8">
            No more overwhelm. Just progress.
          </h2>
          
          <div className="max-w-4xl mx-auto">
            <p className="text-lg lg:text-xl text-[#545454] mb-6" style={{ fontFamily: 'Lato, sans-serif' }}>
              CAT prep usually means 1000+ questions, hours of classes, and constant pressure.
            </p>
            <p className="text-lg lg:text-xl text-[#545454] mb-6" style={{ fontFamily: 'Lato, sans-serif' }}>
              <strong>Twelvr flips the script.</strong>
            </p>
            <p className="text-lg lg:text-xl text-[#545454] mb-6" style={{ fontFamily: 'Lato, sans-serif' }}>
              Every day you get exactly <strong className="text-[#9ac026]">12 adaptive questions</strong> — starting easy, building to hard — so you stay consistent, confident, and covered.
            </p>
            <p className="text-lg lg:text-xl text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
              Prep that fits your busy life, without sacrificing seriousness.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-16 lg:py-24 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-5xl font-bold text-[#545454] mb-8">
              Your daily CAT prep ritual.
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-[#9ac026] rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-[#545454] mb-4">Step 1 — Sign in.</h3>
              <p className="text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pick your reminder time.
              </p>
            </div>

            {/* Step 2 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-[#9ac026] rounded-full flex items-center justify-center mx-auto mb-6">
                <div className="grid grid-cols-3 gap-1">
                  {[...Array(9)].map((_, i) => (
                    <div key={i} className="w-1 h-1 bg-white rounded-full" />
                  ))}
                </div>
              </div>
              <h3 className="text-xl font-bold text-[#545454] mb-4">Step 2 — Do your 12.</h3>
              <p className="text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
                20-30 minutes, adaptive, focused.
              </p>
            </div>

            {/* Step 3 */}
            <div className="text-center">
              <div className="w-16 h-16 bg-[#9ac026] rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-[#545454] mb-4">Step 3 — You're covered.</h3>
              <p className="text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
                One win every day.
              </p>
            </div>
          </div>

          <div className="text-center mt-12">
            <button className="bg-[#9ac026] text-white px-8 py-4 rounded-full text-lg font-semibold hover:bg-[#8bb024] transition-colors shadow-lg">
              Try Today's Daily-12
            </button>
          </div>
        </div>
      </section>

      {/* Why 12 Works Section */}
      <section id="why-12" className="py-16 lg:py-24 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-5xl font-bold text-[#545454] mb-8">
              The science behind 12.
            </h2>
            <p className="text-lg text-[#545454] mb-12" style={{ fontFamily: 'Lato, sans-serif' }}>
              Twelvr is grounded in learning science:
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-gray-50 p-8 rounded-2xl">
              <div className="w-12 h-12 bg-[#9ac026] rounded-lg flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-[#545454] mb-4">Spaced practice</h3>
              <p className="text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
                Improves recall vs. cramming.
              </p>
            </div>

            <div className="bg-gray-50 p-8 rounded-2xl">
              <div className="w-12 h-12 bg-[#9ac026] rounded-lg flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-[#545454] mb-4">Active recall</h3>
              <p className="text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
                Strengthens memory by testing, not reading.
              </p>
            </div>

            <div className="bg-gray-50 p-8 rounded-2xl">
              <div className="w-12 h-12 bg-[#9ac026] rounded-lg flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-[#545454] mb-4">Microlearning</h3>
              <p className="text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
                Short bursts fit into busy days.
              </p>
            </div>
          </div>

          <div className="text-center mt-12">
            <p className="text-lg text-[#545454] font-semibold" style={{ fontFamily: 'Lato, sans-serif' }}>
              12 daily questions = sustainable consistency → better CAT performance.
            </p>
          </div>
        </div>
      </section>

      {/* For Busy Professionals Section */}
      <section className="py-16 lg:py-24 bg-[#545454]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl lg:text-5xl font-bold text-white mb-8">
            Built for working professionals who want CAT success.
          </h2>
          
          <div className="max-w-4xl mx-auto">
            <p className="text-lg lg:text-xl text-gray-200 mb-6" style={{ fontFamily: 'Lato, sans-serif' }}>
              You don't need another 3-hour lecture. You need a system that keeps you moving forward, even on packed workdays.
            </p>
            <p className="text-lg lg:text-xl text-gray-200" style={{ fontFamily: 'Lato, sans-serif' }}>
              Twelvr makes sure you're covered daily — so no matter how hectic life gets, your CAT prep never stops.
            </p>
          </div>
        </div>
      </section>

      {/* Early Access Section */}
      <section id="early-access" className="py-16 lg:py-24 bg-gradient-to-br from-[#9ac026] to-[#8bb024]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl lg:text-5xl font-bold text-white mb-8">
            Be part of the Founders' Circle.
          </h2>
          
          <div className="max-w-4xl mx-auto mb-12">
            <p className="text-lg lg:text-xl text-white mb-6" style={{ fontFamily: 'Lato, sans-serif' }}>
              We're launching Twelvr with ambitious CAT aspirants like you.
            </p>
            <p className="text-lg lg:text-xl text-white" style={{ fontFamily: 'Lato, sans-serif' }}>
              Join our Early Circle, get early access, and help shape the system built for serious professionals.
            </p>
          </div>

          <button className="bg-white text-[#9ac026] px-8 py-4 rounded-full text-lg font-semibold hover:bg-gray-100 transition-colors shadow-lg">
            Join Early Access
          </button>
        </div>
      </section>

      {/* Manifesto Section */}
      <section className="py-16 lg:py-24 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-5xl font-bold text-[#545454] mb-12">
              Our belief.
            </h2>
          </div>

          <div className="max-w-4xl mx-auto text-center space-y-8">
            <p className="text-xl lg:text-2xl text-[#545454] font-medium" style={{ fontFamily: 'Lato, sans-serif' }}>
              Prep shouldn't feel overwhelming.
            </p>
            <p className="text-xl lg:text-2xl text-[#545454] font-medium" style={{ fontFamily: 'Lato, sans-serif' }}>
              Progress is built in small, daily victories.
            </p>
            <p className="text-xl lg:text-2xl text-[#545454] font-medium" style={{ fontFamily: 'Lato, sans-serif' }}>
              Learning should fit your life, not the other way around.
            </p>
            <div className="pt-8">
              <p className="text-lg text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
                That's why Twelvr exists: your daily sparring partner, keeping you covered, consistent, and always moving forward.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#545454] text-white py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center text-center">
            <div className="flex items-center mb-8">
              <img 
                src="https://customer-assets.emergentagent.com/job_sleepy-saha/artifacts/55q6ml5l_twelvr%20revised%20logo.png" 
                alt="Twelvr" 
                className="h-16 sm:h-20 w-auto filter brightness-0 invert"
                style={{ 
                  backgroundColor: 'transparent',
                  mixBlendMode: 'normal'
                }}
              />
            </div>
            
            <p className="text-lg mb-8" style={{ fontFamily: 'Lato, sans-serif' }}>
              <em>Consistency, Compounded.</em>
            </p>

            <button className="bg-[#9ac026] text-white px-6 py-3 rounded-full font-semibold hover:bg-[#8bb024] transition-colors mb-8">
              Start My Daily-12
            </button>

            <p className="text-sm text-gray-300 max-w-2xl" style={{ fontFamily: 'Lato, sans-serif' }}>
              Twelvr complements your CAT prep — it doesn't replace books or coaching.
            </p>
          </div>
        </div>
      </footer>

      {/* Custom Styles */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.8; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};

export default LandingPage;