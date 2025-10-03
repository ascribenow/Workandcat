import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth, API } from './AuthProvider';
import { useLocation } from 'react-router-dom';
import SubscriptionManagement from './SubscriptionManagement';

export const SimpleDashboard = () => {
  const { user, token } = useAuth();
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [categorizedData, setCategorizedData] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({}); // Track which categories are expanded
  
  // Adaptive insights state
  const [adaptiveInsights, setAdaptiveInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [allTimeExpanded, setAllTimeExpanded] = useState(false);  // Collapsed by default
  const [recentExpanded, setRecentExpanded] = useState(true);    // Expanded for active users

  useEffect(() => {
    // Only fetch data if user is authenticated and token exists
    if (user && token) {
      console.log('SimpleDashboard: User and token available, fetching data...');
      fetchDashboardData();
      fetchAdaptiveInsights();
    } else {
      console.log('SimpleDashboard: Waiting for user/token...', { user: !!user, token: !!token });
    }
    
    // Removed aggressive fallback timeout - let actual API errors handle fallbacks
    
    // Cleanup function removed since we removed the timeout
  }, [user, token]);

  // FIX: Refresh insights ONLY when returning from a completed session
  // Use sessionStorage flag to track if a session was just completed
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && user && token) {
        // Check if we should refresh (only if session was completed)
        const shouldRefresh = sessionStorage.getItem('dashboardNeedsRefresh');
        
        if (shouldRefresh === 'true') {
          console.log('SimpleDashboard: Session completed, refreshing data...');
          fetchDashboardData();
          fetchAdaptiveInsights();
          // Clear the flag
          sessionStorage.removeItem('dashboardNeedsRefresh');
        } else {
          console.log('SimpleDashboard: Tab became visible (no refresh needed)');
        }
      }
    };

    // Listen for tab visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user, token]);

  // FIX: Refresh data when returning to dashboard from session page
  useEffect(() => {
    if (location.pathname === '/dashboard' && user && token) {
      // Check if we're coming back from a completed session
      const shouldRefresh = sessionStorage.getItem('dashboardNeedsRefresh');
      
      if (shouldRefresh === 'true') {
        console.log('SimpleDashboard: Returned from session, refreshing data...');
        fetchDashboardData();
        fetchAdaptiveInsights();
        // Clear the flag
        sessionStorage.removeItem('dashboardNeedsRefresh');
      } else {
        console.log('SimpleDashboard: Dashboard loaded (no refresh needed)');
      }
    }
  }, [location.pathname, user, token]);

  // LIGHTWEIGHT TELEMETRY: Log dashboard state mismatches only when data is actually different
  const logDashboardMismatch = (event, apiData, displayData) => {
    const apiCount = apiData?.total_sessions || 0;
    const displayCount = displayData?.total_sessions || 0;
    const mismatch = apiCount !== displayCount;
    
    // Only log if there's an actual mismatch and the data is meaningful
    if (mismatch && apiCount > 0) {
      const mismatchData = {
        event: event,
        api_count: apiCount,
        display_count: displayCount,
        timestamp: new Date().toISOString(),
        build_hash: process.env.REACT_APP_BUILD_HASH || 'unknown'
      };
      
      console.warn('🚨 Dashboard state mismatch detected:', mismatchData);
      
      // Send to telemetry (fire-and-forget, silent failure)
      axios.post(`${API}/telemetry/ui-mismatch`, mismatchData, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 5000
      }).catch(() => {}); // Silent failure - non-critical
    }
  };

  // Function to fetch adaptive insights
  const fetchAdaptiveInsights = async () => {
    if (!user || !token) return;
    
    setInsightsLoading(true);
    try {
      console.log('SimpleDashboard: Fetching adaptive insights...');
      const response = await axios.get(`${API}/dashboard/adaptive-insights`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        timeout: 15000  // 15 second timeout
      });
      
      if (response.data) {
        setAdaptiveInsights(response.data);
        console.log('SimpleDashboard: Adaptive insights loaded successfully');
      }
    } catch (error) {
      console.error('SimpleDashboard: Error fetching adaptive insights:', error);
      // Silently fail - not critical for dashboard functionality
    } finally {
      setInsightsLoading(false);
    }
  };

  const fetchDashboardData = async (retryCount = 0) => {
    try {
      setLoading(true);
      console.log('SimpleDashboard: Fetching categorized taxonomy data...');
      console.log('SimpleDashboard: API URL:', API);
      console.log('SimpleDashboard: Token length:', token?.length);
      console.log('SimpleDashboard: User ID:', user?.id);
      console.log('SimpleDashboard: Retry attempt:', retryCount);
      
      // Fetch both simple and categorized data with increased timeouts
      const [simpleResponse, categorizedResponse] = await Promise.all([
        axios.get(`${API}/dashboard/simple-taxonomy`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 30000  // Increased from 10s to 30s for production stability
        }),
        axios.get(`${API}/dashboard/categorized-taxonomy`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 30000  // Increased from 10s to 30s for production stability
        })
      ]);
      
      console.log('SimpleDashboard: Data received successfully!');
      console.log('SimpleDashboard: Total sessions:', simpleResponse.data?.total_sessions);
      console.log('SimpleDashboard: Categories:', categorizedResponse.data?.total_categories);
      
      setDashboardData(simpleResponse.data);
      setCategorizedData(categorizedResponse.data);
      
      // TELEMETRY: Log mismatch using fresh data (not stale state)
      logDashboardMismatch('post_data_fetch', simpleResponse.data, simpleResponse.data);
      
    } catch (error) {
      console.error('SimpleDashboard: Error fetching data:', error?.message || 'Unknown error');
      
      // Only log detailed error info if it's not a network timeout
      if (error?.code !== 'ECONNABORTED' && error?.response?.status !== 408) {
        console.error('SimpleDashboard: Error details:', {
          message: error.message,
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          retryCount: retryCount
        });
      }
      
      // RETRY LOGIC: Retry up to 2 times with exponential backoff
      if (retryCount < 2) {
        const backoffDelay = Math.pow(2, retryCount) * 2000; // 2s, 4s delays
        console.log(`SimpleDashboard: Retrying in ${backoffDelay}ms... (attempt ${retryCount + 1}/3)`);
        
        setTimeout(() => {
          fetchDashboardData(retryCount + 1);
        }, backoffDelay);
        
        return; // Don't set empty data yet, let retry happen
      }
      
      // Only set fallback data if this is a real API error, not a timeout
      if (error.response?.status >= 400) {
        console.warn('SimpleDashboard: API error detected, using fallback data');
        setDashboardData({ total_sessions: 0, taxonomy_data: [] });
        setCategorizedData({ total_sessions: 0, categorized_data: [], total_categories: 0 });
      }
    } finally {
      console.log('SimpleDashboard: Setting loading to false');
      setLoading(false);
    }
  };

  const toggleCategory = (categoryName) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryName]: !prev[categoryName]
    }));
  };

  // Simple markdown to HTML converter with sanitization (security)
  const markdownToHtml = (markdown) => {
    if (!markdown) return '';
    const DOMPurify = require('dompurify');
    
    const htmlContent = markdown
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold
      .replace(/^\* (.*)/gm, '<li>$1</li>')              // List items
      .replace(/\n/g, '<br>')                            // Line breaks
      .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');       // Wrap lists
    
    // SECURITY: Sanitize HTML before rendering
    return DOMPurify.sanitize(htmlContent, {
      ALLOWED_TAGS: ['strong', 'ul', 'li', 'br'],
      ALLOWED_ATTR: []
    });
  };

  const renderAdaptiveInsights = () => {
    if (insightsLoading) {
      return (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded w-full"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
              <div className="h-4 bg-gray-200 rounded w-4/6"></div>
            </div>
          </div>
        </div>
      );
    }

    if (!adaptiveInsights) return null;

    return (
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-semibold text-gray-900">Adaptive Insights</h2>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                console.log('Manual refresh triggered');
                fetchAdaptiveInsights();
              }}
              className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors flex items-center space-x-1"
              title="Refresh insights"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Refresh</span>
            </button>
            <span className="text-xs text-gray-500">
              Updated {new Date(adaptiveInsights.last_updated_at).toLocaleDateString()}
            </span>
          </div>
        </div>
        
        {/* All-Time Journey Section */}
        <div className="mb-6">
          <button 
            className="flex items-center justify-between w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            onClick={() => setAllTimeExpanded(!allTimeExpanded)}
          >
            <h3 className="text-lg font-medium text-gray-800 flex items-center">
              <span className="mr-2">🏁</span>
              All-Time Journey
            </h3>
            <svg 
              className={`w-5 h-5 transform transition-transform ${allTimeExpanded ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {allTimeExpanded && (
            <div className="mt-3 p-4 bg-blue-50 rounded-lg">
              <div className="prose prose-sm max-w-none text-gray-700">
                <div dangerouslySetInnerHTML={{ 
                  __html: markdownToHtml(adaptiveInsights.all_time_markdown) 
                }} />
              </div>
            </div>
          )}
        </div>

        {/* Recent Momentum Section */}
        <div>
          <button 
            className="flex items-center justify-between w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            onClick={() => setRecentExpanded(!recentExpanded)}
          >
            <h3 className="text-lg font-medium text-gray-800 flex items-center">
              <span className="mr-2">📈</span>
              Recent Momentum
            </h3>
            <svg 
              className={`w-5 h-5 transform transition-transform ${recentExpanded ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {recentExpanded && (
            <div className="mt-3 p-4 bg-green-50 rounded-lg">
              <div className="prose prose-sm max-w-none text-gray-700">
                <div dangerouslySetInnerHTML={{ 
                  __html: markdownToHtml(adaptiveInsights.recent_markdown) 
                }} />
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Show loading while user/token is not available
  if (!user || !token || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your progress...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        
        {/* Sessions Count at Top */}
        <div className="mb-8">
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Your Study Progress</h1>
            <div className="text-5xl font-bold text-blue-600 mb-2">
              {dashboardData?.total_sessions || 0}
            </div>
            <p className="text-lg text-gray-600">Total Sessions Completed</p>
          </div>
        </div>

        {/* Adaptive Insights Section */}
        {renderAdaptiveInsights()}

        {/* Collapsible Categorized Taxonomy Table */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              Complete CAT Syllabus - Question Attempts by Category
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              Click on any category to expand and see subcategory breakdown. Data fetched from database CATEGORY:SUBCATEGORY fields.
            </p>
            
            <div className="space-y-2">
              {categorizedData?.categorized_data?.map((category, categoryIndex) => (
                <div key={categoryIndex} className="border border-gray-200 rounded-lg">
                  {/* Category Header - Clickable */}
                  <div 
                    className="px-4 py-4 bg-gray-50 hover:bg-gray-100 cursor-pointer flex items-center justify-between transition-colors"
                    onClick={() => toggleCategory(category.category_name)}
                  >
                    <div className="flex items-center space-x-4">
                      {/* Expand/Collapse Arrow */}
                      <div className="transform transition-transform duration-200">
                        {expandedCategories[category.category_name] ? (
                          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        )}
                      </div>
                      
                      {/* Category Name */}
                      <div className="font-semibold text-gray-900 text-lg">
                        {category.category_name}
                      </div>
                    </div>
                    
                    {/* Category Summary (Easy | Medium | Hard) */}
                    <div className="flex items-center space-x-6">
                      <div className="text-center">
                        <div className="text-sm font-medium text-green-600">{category.total_easy}</div>
                        <div className="text-xs text-gray-500">Easy</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm font-medium text-yellow-600">{category.total_medium}</div>
                        <div className="text-xs text-gray-500">Medium</div>
                      </div>
                      <div className="text-center">
                        <div className="text-sm font-medium text-red-600">{category.total_hard}</div>
                        <div className="text-xs text-gray-500">Hard</div>
                      </div>
                      <div className="text-center border-l border-gray-300 pl-6">
                        <div className="text-sm font-bold text-gray-900">{category.total_attempts}</div>
                        <div className="text-xs text-gray-500">Total</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Collapsible Subcategory Content */}
                  {expandedCategories[category.category_name] && (
                    <div className="border-t border-gray-200">
                      <div className="overflow-x-auto">
                        <table className="min-w-full">
                          <thead>
                            <tr className="bg-gray-100">
                              <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 uppercase tracking-wider">
                                Subcategory
                              </th>
                              <th className="px-4 py-3 text-center text-sm font-medium text-gray-600 uppercase tracking-wider">
                                Easy
                              </th>
                              <th className="px-4 py-3 text-center text-sm font-medium text-gray-600 uppercase tracking-wider">
                                Medium
                              </th>
                              <th className="px-4 py-3 text-center text-sm font-medium text-gray-600 uppercase tracking-wider">
                                Hard
                              </th>
                              <th className="px-4 py-3 text-center text-sm font-medium text-gray-600 uppercase tracking-wider">
                                Total
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-100">
                            {category.subcategories?.map((subcategory, subIndex) => (
                              <tr key={subIndex} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-sm text-gray-900">
                                  <div className="font-medium">
                                    {subcategory.subcategory_name}
                                  </div>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-sm font-medium ${
                                    subcategory.easy_attempts > 0 
                                      ? 'bg-green-100 text-green-800' 
                                      : 'bg-gray-100 text-gray-400'
                                  }`}>
                                    {subcategory.easy_attempts}
                                    {subcategory.easy_attempts > 0 && (
                                      <span className="ml-1 text-xs">
                                        ({subcategory.easy_accuracy}%)
                                      </span>
                                    )}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-sm font-medium ${
                                    subcategory.medium_attempts > 0 
                                      ? 'bg-yellow-100 text-yellow-800' 
                                      : 'bg-gray-100 text-gray-400'
                                  }`}>
                                    {subcategory.medium_attempts}
                                    {subcategory.medium_attempts > 0 && (
                                      <span className="ml-1 text-xs">
                                        ({subcategory.medium_accuracy}%)
                                      </span>
                                    )}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-sm font-medium ${
                                    subcategory.hard_attempts > 0 
                                      ? 'bg-red-100 text-red-800' 
                                      : 'bg-gray-100 text-gray-400'
                                  }`}>
                                    {subcategory.hard_attempts}
                                    {subcategory.hard_attempts > 0 && (
                                      <span className="ml-1 text-xs">
                                        ({subcategory.hard_accuracy}%)
                                      </span>
                                    )}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-center">
                                  <span className="inline-flex items-center px-2 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                                    {subcategory.total_attempts}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )) || []}
              
              {(!categorizedData?.categorized_data || categorizedData.categorized_data.length === 0) && (
                <div className="text-center py-12 text-gray-500 border border-gray-200 rounded-lg">
                  <div className="mb-4">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H9a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-gray-900 mb-2">No Study Data Yet</p>
                  <p>Complete some adaptive sessions to see your progress across the CAT syllabus</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Summary Statistics - Updated for Categorized Data */}
        {categorizedData?.categorized_data && categorizedData.categorized_data.length > 0 && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-green-50 rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-green-600">
                {categorizedData.categorized_data.reduce((sum, category) => sum + category.total_easy, 0)}
              </div>
              <div className="text-sm font-medium text-green-700">Easy Questions</div>
            </div>
            
            <div className="bg-yellow-50 rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-yellow-600">
                {categorizedData.categorized_data.reduce((sum, category) => sum + category.total_medium, 0)}
              </div>
              <div className="text-sm font-medium text-yellow-700">Medium Questions</div>
            </div>
            
            <div className="bg-red-50 rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-red-600">
                {categorizedData.categorized_data.reduce((sum, category) => sum + category.total_hard, 0)}
              </div>
              <div className="text-sm font-medium text-red-700">Hard Questions</div>
            </div>
            
            <div className="bg-blue-50 rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-blue-600">
                {categorizedData.categorized_data.reduce((sum, category) => sum + category.total_attempts, 0)}
              </div>
              <div className="text-sm font-medium text-blue-700">Total Questions</div>
            </div>
          </div>
        )}

        {/* Subscription Management */}
        <div className="mt-8">
          <SubscriptionManagement />
        </div>
        
      </div>
    </div>
  );
};