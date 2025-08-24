import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import "./App.css";
import { AuthProvider, useAuth } from "./components/AuthProvider";
import { Dashboard } from "./components/Dashboard";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Professional Login Component
const Login = () => {
  const [formData, setFormData] = useState({ email: "", password: "", name: "", verificationCode: "" });
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showPasswordReset, setShowPasswordReset] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetMessage, setResetMessage] = useState("");
  
  // Email verification states
  const [showEmailVerification, setShowEmailVerification] = useState(false);
  const [verificationStep, setVerificationStep] = useState(1); // 1: Send code, 2: Verify code and complete signup
  const [codeSent, setCodeSent] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const { 
    login, 
    register, 
    requestPasswordReset, 
    sendVerificationCode, 
    verifyEmailCode, 
    registerWithVerification 
  } = useAuth();

  // Countdown timer for resend code
  useEffect(() => {
    let timer;
    if (countdown > 0) {
      timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [countdown]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      let result;
      if (isRegister) {
        // Start email verification process
        setShowEmailVerification(true);
        setVerificationStep(1);
        setLoading(false);
        return;
      } else {
        result = await login(formData.email, formData.password);
      }

      if (!result.success) {
        setError(result.error);
      }
    } catch (error) {
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  const handleSendVerificationCode = async () => {
    if (!formData.email || !formData.name || !formData.password) {
      setError("Please fill in all required fields first");
      return;
    }

    setLoading(true);
    setError("");
    
    try {
      const result = await sendVerificationCode(formData.email);
      if (result.success) {
        setSuccess("Verification code sent! Please check your email.");
        setCodeSent(true);
        setVerificationStep(2);
        setCountdown(60); // 60 second countdown for resend
      } else {
        setError(result.error);
      }
    } catch (error) {
      setError("Failed to send verification code");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAndSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      // Just verify the code
      const verifyResult = await verifyEmailCode(formData.email, formData.verificationCode);
      
      if (verifyResult.success) {
        // Show success message
        setSuccess("✅ Code verified! Your email has been validated.");
        setError("");
        
        // Wait 2 seconds then redirect to login
        setTimeout(() => {
          setSuccess("Your email is now verified. Please use the regular signup form to create your account.");
          
          // Wait another 2 seconds then reset to login
          setTimeout(() => {
            resetVerificationFlow();
            setIsRegister(false); // Go back to login page
          }, 2500);
        }, 2000);
      } else {
        setError(verifyResult.error || "Invalid or expired verification code");
      }
    } catch (error) {
      setError("Verification failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const resetVerificationFlow = () => {
    setShowEmailVerification(false);
    setVerificationStep(1);
    setCodeSent(false);
    setFormData(prev => ({ ...prev, verificationCode: "" }));
    setError("");
    setSuccess("");
  };

  const handlePasswordReset = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResetMessage("");

    const result = await requestPasswordReset(resetEmail);
    if (result.success) {
      setResetMessage(result.message);
      setShowPasswordReset(false);
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  if (showPasswordReset) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
        <div className="max-w-md w-full">
          <div className="bg-white rounded-lg shadow-xl p-8">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900">Reset Password</h2>
              <p className="mt-2 text-sm text-gray-600">
                Enter your email to receive reset instructions
              </p>
            </div>

            <form onSubmit={handlePasswordReset} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? "Sending..." : "Send Reset Email"}
              </button>

              <button
                type="button"
                onClick={() => setShowPasswordReset(false)}
                className="w-full text-center text-sm text-blue-600 hover:text-blue-500"
              >
                Back to Login
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // Email Verification Flow UI
  if (showEmailVerification) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
        <div className="max-w-md w-full">
          <div className="bg-white rounded-lg shadow-xl p-8">
            <div className="text-center mb-8">
              <div className="mx-auto mb-6 flex justify-center">
                <img 
                  src="/images/twelvr-logo.png" 
                  alt="Twelvr Logo" 
                  className="h-32 w-auto"
                  style={{backgroundColor: 'transparent'}}
                />
              </div>
              <h2 className="text-2xl font-bold text-gray-900">
                {verificationStep === 1 ? "Verify Your Email" : "Enter Verification Code"}
              </h2>
              <p className="mt-2 text-sm text-gray-600">
                {verificationStep === 1 
                  ? "We'll send a 6-digit code to verify your email address"
                  : "Please enter the 6-digit code sent to your email"
                }
              </p>
            </div>

            {verificationStep === 1 ? (
              // Step 1: Send Verification Code
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Full Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Email Address</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Password</label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    minLength="6"
                  />
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                    {error}
                  </div>
                )}

                {success && (
                  <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                    {success}
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleSendVerificationCode}
                  disabled={loading}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {loading ? "Sending Code..." : "📧 Send Verification Code"}
                </button>
              </div>
            ) : (
              // Step 2: Verify Code and Complete Signup
              <form onSubmit={handleVerifyAndSignup} className="space-y-6">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-700">
                    📧 Verification code sent to: <strong>{formData.email}</strong>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">6-Digit Verification Code</label>
                  <input
                    type="text"
                    value={formData.verificationCode}
                    onChange={(e) => setFormData({...formData, verificationCode: e.target.value})}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-center text-2xl font-mono tracking-wider"
                    placeholder="000000"
                    maxLength="6"
                    pattern="[0-9]{6}"
                    required
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Code expires in 15 minutes
                  </p>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                    {error}
                  </div>
                )}

                {success && (
                  <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                    {success}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                >
                  {loading ? "Verifying..." : "✅ Verify Email"}
                </button>

                <div className="text-center space-y-2">
                  <button
                    type="button"
                    onClick={handleSendVerificationCode}
                    disabled={loading || countdown > 0}
                    className={`text-sm ${countdown > 0 ? 'text-gray-400' : 'text-blue-600 hover:text-blue-500'} disabled:cursor-not-allowed`}
                  >
                    {countdown > 0 ? `Resend code in ${countdown}s` : "Resend verification code"}
                  </button>
                </div>
              </form>
            )}

            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={resetVerificationFlow}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                ← Back to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="text-center mb-8">
            <div className="mx-auto mb-6 flex justify-center">
              <img 
                src="/images/twelvr-logo.png" 
                alt="Twelvr Logo" 
                className="h-40 w-auto"
                style={{backgroundColor: 'transparent'}}
              />
            </div>
            <p className="mt-2 text-sm text-gray-600">
              {isRegister ? "Create your account" : "Sign in to your account"}
            </p>
            <p className="mt-1 text-xs text-blue-600">
              Advanced AI-powered CAT preparation with personalized study plans
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-gray-700">Full Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Password</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
                minLength="6"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            {resetMessage && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                {resetMessage}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? "Please wait..." : (isRegister ? "Create Account" : "Sign In")}
            </button>

            <div className="text-center space-y-2">
              <button
                type="button"
                onClick={() => setIsRegister(!isRegister)}
                className="text-sm text-blue-600 hover:text-blue-500"
              >
                {isRegister ? "Already have an account? Sign in" : "Need an account? Register"}
              </button>
              
              {!isRegister && (
                <div>
                  <button
                    type="button"
                    onClick={() => setShowPasswordReset(true)}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Forgot your password?
                  </button>
                </div>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading CAT Prep Platform...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && !isAdmin()) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900">Access Denied</h2>
          <p className="mt-2 text-gray-600">You need admin privileges to access this page.</p>
        </div>
      </div>
    );
  }

  return children;
};

// Main App Content Component
const AppContent = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading CAT Prep Platform v2.0...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return <Login />;
  }

  return <Dashboard />;
};

// Root App Component
function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;