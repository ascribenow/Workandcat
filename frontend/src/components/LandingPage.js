import React, { useState } from 'react';
import { useAuth } from './AuthProvider';
import { useNavigate } from 'react-router-dom';

const LandingPage = () => {
  const { login, sendVerificationCode, verifyEmailCode, registerWithVerification } = useAuth();
  const navigate = useNavigate();
  const [showSignIn, setShowSignIn] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Two-step verification state
  const [showVerification, setShowVerification] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  const [resendCountdown, setResendCountdown] = useState(0);
  const [showPassword, setShowPassword] = useState(false);

  // Start countdown timer for resend
  React.useEffect(() => {
    let timer;
    if (resendCountdown > 0) {
      timer = setInterval(() => {
        setResendCountdown(prev => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendCountdown]);

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
    setSuccess('');
    
    // Basic validation
    if (!name.trim()) {
      setError('Full name is required');
      setLoading(false);
      return;
    }
    
    if (!email.trim()) {
      setError('Email is required');
      setLoading(false);
      return;
    }
    
    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address');
      setLoading(false);
      return;
    }
    
    if (!password.trim()) {
      setError('Password is required');
      setLoading(false);
      return;
    }
    
    if (password.length < 6) {
      setError('Password must be at least 6 characters long');
      setLoading(false);
      return;
    }
    
    try {
      // Step 1: Send verification code
      const result = await sendVerificationCode(email);
      
      if (result.success) {
        setShowVerification(true);
        setResendCountdown(60); // 60 second countdown
        setSuccess('Verification code sent! Please check your email.');
      } else {
        setError(result.error || 'Failed to send verification code');
      }
    } catch (err) {
      setError('Failed to send verification code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAndRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    if (!verificationCode.trim() || verificationCode.length !== 6) {
      setError('Please enter a valid 6-digit verification code');
      setLoading(false);
      return;
    }
    
    try {
      // Step 2: Register with verification code
      const result = await registerWithVerification(name, email, password, verificationCode);
      
      if (result.success) {
        setSuccess('Account created successfully! Welcome to Twelvr!');
        // Clear form and redirect or show success
        setTimeout(() => {
          // User will be automatically logged in by registerWithVerification
          navigate('/dashboard'); // Or wherever you want to redirect
        }, 2000);
      } else {
        setError(result.error || 'Invalid or expired verification code');
      }
    } catch (err) {
      setError('Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (resendCountdown > 0) return;
    
    setLoading(true);
    setError('');
    
    try {
      const result = await sendVerificationCode(email);
      
      if (result.success) {
        setResendCountdown(60);
        setSuccess('New verification code sent!');
      } else {
        setError(result.error || 'Failed to resend code');
      }
    } catch (err) {
      setError('Failed to resend code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const resetSignupFlow = () => {
    setShowVerification(false);
    setVerificationCode('');
    setResendCountdown(0);
    setError('');
    setSuccess('');
  };

  // Function to scroll to sign-up panel
  const scrollToSignUp = () => {
    setShowSignIn(false); // Switch to sign-up tab
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Function to scroll to top of page
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            {/* Logo - Clickable to scroll to top */}
            <div className="flex items-center">
              <button onClick={scrollToTop} className="focus:outline-none">
                <img 
                  src="https://customer-assets.emergentagent.com/job_sleepy-saha/artifacts/ss0tc3jc_Twelver%20edited.png" 
                  alt="Twelvr" 
                  className="h-16 sm:h-20 md:h-24 lg:h-28 w-auto cursor-pointer hover:opacity-80 transition-opacity"
                />
              </button>
            </div>
            
            {/* Navigation */}
            <nav className="hidden md:flex items-center space-x-8">
              <a href="#how-it-works" className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                How It Works
              </a>
              <a href="#why-12" className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Why 12 Works
              </a>
              <button onClick={() => navigate('/pricing')} className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pricing
              </button>
              <button onClick={() => navigate('/early-access')} className="text-[#545454] hover:text-[#ff6d4d] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Early Access
              </button>
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
                12 adaptive questions. 90 days to CAT readiness.<br />
                Serious prep, simple ritual.
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
                <button 
                  onClick={scrollToSignUp}
                  className="bg-[#9ac026] text-white px-6 sm:px-8 py-3 sm:py-4 rounded-full text-base sm:text-lg font-semibold hover:bg-[#8bb024] transition-colors shadow-lg"
                >
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
                <form onSubmit={showSignIn ? handleSignIn : (showVerification ? handleVerifyAndRegister : handleSignUp)}>
                  <div className="space-y-4">
                    {/* Show verification code input when in verification step */}
                    {!showSignIn && showVerification ? (
                      <>
                        <div className="text-center mb-4">
                          <h3 className="text-lg font-semibold text-[#545454] mb-2">Verify Your Email</h3>
                          <p className="text-sm text-gray-600">
                            We sent a 6-digit code to <span className="font-semibold">{email}</span>
                          </p>
                        </div>
                        
                        <div>
                          <input
                            type="text"
                            value={verificationCode}
                            onChange={(e) => {
                              const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                              setVerificationCode(value);
                            }}
                            placeholder="000000"
                            className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#9ac026] focus:border-transparent transition-colors text-center text-lg font-mono tracking-widest"
                            style={{ fontFamily: 'monospace' }}
                            maxLength="6"
                            required
                          />
                          <p className="text-xs text-gray-500 mt-1 text-center">
                            Code expires in 15 minutes
                          </p>
                        </div>

                        <div className="text-center">
                          {resendCountdown > 0 ? (
                            <p className="text-sm text-gray-500">
                              Resend code in {resendCountdown}s
                            </p>
                          ) : (
                            <button
                              type="button"
                              onClick={handleResendCode}
                              disabled={loading}
                              className="text-sm text-[#9ac026] hover:text-[#8bb024] font-medium disabled:opacity-50"
                            >
                              Resend verification code
                            </button>
                          )}
                        </div>

                        <div className="text-center">
                          <button
                            type="button"
                            onClick={resetSignupFlow}
                            className="text-sm text-gray-500 hover:text-gray-700"
                          >
                            ← Back to signup
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        {/* Regular signup/signin form */}
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
                            placeholder="Email"
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
                            minLength="6"
                          />
                          {!showSignIn && (
                            <p className="text-xs text-gray-500 mt-1">
                              Password must be at least 6 characters
                            </p>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Error and Success Messages */}
                  {error && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-red-600 text-sm">{error}</p>
                    </div>
                  )}

                  {success && (
                    <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                      <p className="text-green-600 text-sm">{success}</p>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-[#9ac026] text-white py-3 rounded-lg font-semibold hover:bg-[#8bb024] transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-6"
                    style={{ fontFamily: 'Lato, sans-serif' }}
                  >
                    {loading ? (
                      <div className="flex items-center justify-center">
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                        {showSignIn ? 'Signing In...' : (showVerification ? 'Verifying...' : 'Sending Code...')}
                      </div>
                    ) : (
                      showSignIn ? 'Sign In' : (showVerification ? 'Create Account' : 'Send Verification Code')
                    )}
                  </button>
                </form>

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
            <button 
              onClick={scrollToSignUp}
              className="bg-[#9ac026] text-white px-8 py-4 rounded-full text-lg font-semibold hover:bg-[#8bb024] transition-colors shadow-lg"
            >
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

          <button 
            onClick={() => navigate('/early-access')}
            className="bg-white text-[#9ac026] px-8 py-4 rounded-full text-lg font-semibold hover:bg-gray-100 transition-colors shadow-lg"
          >
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
            <div className="flex items-center mb-6">
              <button onClick={scrollToTop} className="focus:outline-none">
                <img 
                  src="https://customer-assets.emergentagent.com/job_sleepy-saha/artifacts/vy7femuy_Twelvr%20logo%20dark%20background.png" 
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
              onClick={scrollToSignUp}
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

            {/* Footer Navigation - At the very bottom */}
            <nav className="flex flex-wrap justify-center gap-6">
              <button onClick={() => navigate('/pricing')} className="text-gray-300 hover:text-[#9ac026] transition-colors" style={{ fontFamily: 'Lato, sans-serif' }}>
                Pricing
              </button>
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