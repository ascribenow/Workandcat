import React, { createContext, useContext, useEffect, useState } from 'react';
import axios from 'axios';

// Smart API URL detection
const getBackendURL = () => {
  // If environment variable is set, use it
  if (process.env.REACT_APP_BACKEND_URL && process.env.REACT_APP_BACKEND_URL.trim()) {
    return process.env.REACT_APP_BACKEND_URL;
  }
  
  // Auto-detect based on current domain
  const currentDomain = window.location.hostname;
  
  if (currentDomain === 'localhost' || currentDomain === '127.0.0.1') {
    // Local development - use direct backend URL
    return 'http://localhost:8001';
  } else if (currentDomain === 'twelvr.com' || currentDomain.includes('twelvr')) {
    // Custom domain - use environment variable or relative path
    return process.env.REACT_APP_BACKEND_URL || '';
  } else if (currentDomain.includes('preview.emergentagent.com')) {
    // Preview domain - use relative URLs
    return '';
  } else {
    // Default fallback for other domains
    return '';
  }
};

const BACKEND_URL = getBackendURL();
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

console.log(`🔗 API Configuration: Backend URL = "${BACKEND_URL}", API = "${API}"`);

// Create Auth Context
const AuthContext = createContext();

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Auth Provider Component
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedToken = localStorage.getItem('cat_prep_token');
        const storedUser = localStorage.getItem('cat_prep_user');

        if (storedToken && storedUser) {
          const userData = JSON.parse(storedUser);
          
          // Verify token is still valid
          try {
            const response = await axios.get(`${API}/auth/me`, {
              headers: { Authorization: `Bearer ${storedToken}` }
            });
            
            setToken(storedToken);
            setUser(response.data);
            
            // Set default authorization header
            axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
          } catch (error) {
            // Token is invalid, clear storage
            localStorage.removeItem('cat_prep_token');
            localStorage.removeItem('cat_prep_user');
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Login function
  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, {
        email,
        password
      });

      const { access_token, user: userData } = response.data;

      // Store in localStorage
      localStorage.setItem('cat_prep_token', access_token);
      localStorage.setItem('cat_prep_user', JSON.stringify(userData));

      // Set auth state
      setToken(access_token);
      setUser(userData);

      // Set default authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      return { success: true, user: userData };
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed';
      return { success: false, error: message };
    }
  };

  // Register function
  const register = async (name, email, password) => {
    try {
      const response = await axios.post(`${API}/auth/register`, {
        full_name: name,
        email,
        password
      });

      const { access_token, user: userData } = response.data;

      // Store in localStorage
      localStorage.setItem('cat_prep_token', access_token);
      localStorage.setItem('cat_prep_user', JSON.stringify(userData));

      // Set auth state
      setToken(access_token);
      setUser(userData);

      // Set default authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      return { success: true, user: userData };
    } catch (error) {
      const message = error.response?.data?.detail || 'Registration failed';
      return { success: false, error: message };
    }
  };

  // Send email verification code
  const sendVerificationCode = async (email) => {
    try {
      const response = await axios.post(`${API}/auth/send-verification-code`, {
        email
      });
      
      return { 
        success: true, 
        message: response.data.message || 'Verification code sent successfully'
      };
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to send verification code';
      return { success: false, error: message };
    }
  };

  // Verify email code
  const verifyEmailCode = async (email, code) => {
    try {
      const response = await axios.post(`${API}/auth/verify-email-code`, {
        email,
        code
      });
      
      return { 
        success: true, 
        message: response.data.message || 'Email verification successful'
      };
    } catch (error) {
      const message = error.response?.data?.detail || 'Invalid or expired verification code';
      return { success: false, error: message };
    }
  };

  // Register with email verification
  const registerWithVerification = async (name, email, password, code) => {
    try {
      const response = await axios.post(`${API}/auth/signup-with-verification`, {
        full_name: name,
        email,
        password,
        code
      });

      const { access_token, user: userData } = response.data;

      // Store in localStorage
      localStorage.setItem('cat_prep_token', access_token);
      localStorage.setItem('cat_prep_user', JSON.stringify(userData));

      // Set auth state
      setToken(access_token);
      setUser(userData);

      // Set default authorization header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      return { success: true, user: userData };
    } catch (error) {
      const message = error.response?.data?.detail || 'Registration with verification failed';
      return { success: false, error: message };
    }
  };

  // Get Gmail authorization URL
  const getGmailAuthURL = async () => {
    try {
      const response = await axios.get(`${API}/auth/gmail/authorize`);
      return { 
        success: true, 
        authUrl: response.data.authorization_url 
      };
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to get authorization URL';
      return { success: false, error: message };
    }
  };

  // Handle Gmail callback
  const handleGmailCallback = async (authorizationCode) => {
    try {
      const response = await axios.post(`${API}/auth/gmail/callback`, {
        authorization_code: authorizationCode
      });
      
      return { 
        success: true, 
        message: response.data.message || 'Gmail authentication successful'
      };
    } catch (error) {
      const message = error.response?.data?.detail || 'Gmail authentication failed';
      return { success: false, error: message };
    }
  };

  // Logout function
  const logout = () => {
    // Clear localStorage
    localStorage.removeItem('cat_prep_token');
    localStorage.removeItem('cat_prep_user');

    // Clear auth state
    setToken(null);
    setUser(null);

    // Remove default authorization header
    delete axios.defaults.headers.common['Authorization'];
  };

  // Request password reset with code
  const requestPasswordReset = async (email) => {
    try {
      await axios.post(`${API}/auth/password-reset`, { email });
      return { success: true, message: 'If an account with this email exists, a password reset code has been sent.' };
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to send reset email';
      return { success: false, error: message };
    }
  };

  // Verify password reset code and set new password
  const verifyPasswordReset = async (email, code, newPassword) => {
    try {
      const response = await axios.post(`${API}/auth/password-reset-verify`, {
        email,
        code,
        new_password: newPassword
      });
      
      return { 
        success: true, 
        message: response.data.message || 'Password reset successfully!'
      };
    } catch (error) {
      const message = error.response?.data?.detail || 'Invalid or expired reset code';
      return { success: false, error: message };
    }
  };

  // Check if user is admin
  const isAdmin = () => {
    return user?.is_admin || false;
  };

  // Check if user is authenticated
  const isAuthenticated = () => {
    // During loading, check localStorage for stored token to prevent race condition
    if (loading && localStorage.getItem('cat_prep_token')) {
      return true;
    }
    return !!(token && user);
  };

  const value = {
    user,
    token,
    loading,
    API,
    login,
    register,
    logout,
    requestPasswordReset,
    verifyPasswordReset,
    sendVerificationCode,
    verifyEmailCode,
    registerWithVerification,
    getGmailAuthURL,
    handleGmailCallback,
    isAdmin,
    isAuthenticated,
    // Utility functions
    getUserId: () => user?.id,
    getUserName: () => user?.name,
    getUserEmail: () => user?.email,
    isEmailVerified: () => user?.email_verified || false
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};