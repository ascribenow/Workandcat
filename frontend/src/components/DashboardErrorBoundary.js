import React from 'react';

class DashboardErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error but don't crash the app
    console.error('Dashboard Error Boundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // Fallback UI
      return (
        <div className="max-w-4xl mx-auto p-6" style={{ fontFamily: 'Manrope, sans-serif' }}>
          <div className="border rounded-lg p-6" style={{ backgroundColor: '#fff5f3', borderColor: '#ff6d4d' }}>
            <h3 className="text-lg font-semibold mb-2" style={{ color: '#ff6d4d' }}>Dashboard Loading Error</h3>
            <p className="mb-4" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
              The dashboard encountered a loading error. The session functionality should still work.
            </p>
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 text-white rounded transition-colors mr-2"
              style={{ backgroundColor: '#ff6d4d', fontFamily: 'Lato, sans-serif' }}
            >
              Refresh Page
            </button>
            <button 
              onClick={() => this.setState({ hasError: false, error: null })}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded transition-colors"
              style={{ fontFamily: 'Lato, sans-serif' }}
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default DashboardErrorBoundary;