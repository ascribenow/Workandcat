import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';

const Header = ({ onScrollToSection, className = "" }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, logout } = useAuth();

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Navigation with scroll to top
  const navigateToPage = (path) => {
    navigate(path);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Handle section scrolling on landing page
  const handleSectionNavigation = (section) => {
    if (location.pathname === '/') && onScrollToSection) {
      onScrollToSection(section);
    } else {
      // If not on landing page, navigate to landing page with hash
      navigate(`/#${section}`);
    }
  };

  const getCurrentPageName = () => {
    switch (location.pathname) {
      case '/pricing':
        return 'Pricing';
      case '/contact':
        return 'Contact Us';
      case '/subscription':
        return 'Subscription';
      default:
        return null;
    }
  };

  const currentPage = getCurrentPageName();

  return (
    <header className={`bg-white shadow-sm ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          {/* Logo - Clickable to go home */}
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
            {/* How It Works */}
            <button 
              onClick={() => handleSectionNavigation('how-it-works')} 
              className={`transition-colors ${currentPage === 'How It Works' ? 'text-[#9ac026] font-semibold' : 'text-[#545454] hover:text-[#ff6d4d]'}`} 
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              How It Works
            </button>

            {/* Why 12 Works */}
            <button 
              onClick={() => handleSectionNavigation('why-12')} 
              className={`transition-colors ${currentPage === 'Why 12 Works' ? 'text-[#9ac026] font-semibold' : 'text-[#545454] hover:text-[#ff6d4d]'}`} 
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              Why 12 Works
            </button>

            {/* Subscription - Only shown when authenticated */}
            {isAuthenticated() && (
              <button 
                onClick={() => navigateToPage('/pricing')} 
                className={`transition-colors ${currentPage === 'Subscription' ? 'text-[#9ac026] font-semibold' : 'text-[#545454] hover:text-[#ff6d4d]'}`} 
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                Subscription
              </button>
            )}

            {/* Pricing */}
            <button 
              onClick={() => navigateToPage('/pricing')} 
              className={`transition-colors ${currentPage === 'Pricing' ? 'text-[#9ac026] font-semibold' : 'text-[#545454] hover:text-[#ff6d4d]'}`} 
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              Pricing
            </button>

            {/* User section - Only shown when authenticated */}
            {isAuthenticated() && (
              <div className="flex items-center space-x-4 ml-8 border-l border-gray-200 pl-8">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 bg-[#9ac026] rounded-full flex items-center justify-center">
                    <span className="text-white text-sm font-semibold">
                      {user?.name?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || 'U'}
                    </span>
                  </div>
                  <span className="text-[#545454] text-sm font-medium" style={{ fontFamily: 'Lato, sans-serif' }}>
                    {user?.name || 'User'}
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="text-[#545454] hover:text-[#ff6d4d] transition-colors text-sm"
                  style={{ fontFamily: 'Lato, sans-serif' }}
                >
                  Logout
                </button>
              </div>
            )}
          </nav>

          {/* Mobile menu button - TODO: Implement mobile menu */}
          <div className="md:hidden">
            <button className="text-[#545454] hover:text-[#ff6d4d] transition-colors">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;