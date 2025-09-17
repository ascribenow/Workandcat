import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth, API } from './AuthProvider';
import SubscriptionManagement from './SubscriptionManagement';

export const SimpleDashboard = () => {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [categorizedData, setCategorizedData] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({}); // Track which categories are expanded

  useEffect(() => {
    // Only fetch data if user is authenticated and token exists
    if (user && token) {
      console.log('SimpleDashboard: User and token available, fetching data...');
      fetchDashboardData();
    } else {
      console.log('SimpleDashboard: Waiting for user/token...', { user: !!user, token: !!token });
    }
    
    // Fallback timeout to prevent infinite loading
    const fallbackTimeout = setTimeout(() => {
      console.log('SimpleDashboard: Fallback timeout triggered after 15 seconds');
      if (loading) {
        setLoading(false);
        setDashboardData({ total_sessions: 0, taxonomy_data: [] });
        setCategorizedData({ total_sessions: 0, categorized_data: [], total_categories: 0 });
      }
    }, 15000);
    
    return () => clearTimeout(fallbackTimeout);
  }, [user, token]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      console.log('SimpleDashboard: Fetching categorized taxonomy data...');
      
      // Fetch both simple and categorized data
      const [simpleResponse, categorizedResponse] = await Promise.all([
        axios.get(`${API}/dashboard/simple-taxonomy`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000
        }),
        axios.get(`${API}/dashboard/categorized-taxonomy`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000
        })
      ]);
      
      console.log('SimpleDashboard: Data received successfully!');
      console.log('SimpleDashboard: Total sessions:', simpleResponse.data?.total_sessions);
      console.log('SimpleDashboard: Categories:', categorizedResponse.data?.total_categories);
      
      setDashboardData(simpleResponse.data);
      setCategorizedData(categorizedResponse.data);
      
    } catch (error) {
      console.error('SimpleDashboard: Error fetching data:', error);
      
      // Set empty data to stop loading
      setDashboardData({ total_sessions: 0, taxonomy_data: [] });
      setCategorizedData({ total_sessions: 0, categorized_data: [], total_categories: 0 });
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

        {/* Phase Information */}
        <div className="mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Learning Phases</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div>
                  <h3 className="font-semibold text-blue-900">Phase A (Coverage & Calibration)</h3>
                  <p className="text-sm text-blue-700">Sessions 1-30: Build foundational coverage across all topics</p>
                </div>
                <div className="text-sm text-blue-600 font-medium">
                  {dashboardData?.total_sessions <= 30 ? 'Current Phase' : 'Completed'}
                </div>
              </div>
              
              <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
                <div>
                  <h3 className="font-semibold text-green-900">Phase B (Strengthen & Stretch)</h3>
                  <p className="text-sm text-green-700">Sessions 31-60: Focus on weak areas and challenge yourself</p>
                </div>
                <div className="text-sm text-green-600 font-medium">
                  {dashboardData?.total_sessions > 30 && dashboardData?.total_sessions <= 60 ? 'Current Phase' : 
                   dashboardData?.total_sessions > 60 ? 'Completed' : 'Upcoming'}
                </div>
              </div>
              
              <div className="flex items-center justify-between p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <div>
                  <h3 className="font-semibold text-purple-900">Phase C (Full Adaptivity)</h3>
                  <p className="text-sm text-purple-700">Sessions 61+: Advanced adaptive learning with personalized difficulty</p>
                </div>
                <div className="text-sm text-purple-600 font-medium">
                  {dashboardData?.total_sessions > 60 ? 'Current Phase' : 'Upcoming'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Simplified Taxonomy Table */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              Complete CAT Syllabus - Question Attempts by Difficulty
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              Shows number of questions attempted across all sessions for each topic
            </p>
            
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
          </div>
        </div>

        {/* Summary Statistics */}
        {dashboardData?.taxonomy_data && dashboardData.taxonomy_data.length > 0 && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-green-50 rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-green-600">
                {dashboardData.taxonomy_data.reduce((sum, item) => sum + item.easy_attempts, 0)}
              </div>
              <div className="text-sm font-medium text-green-700">Easy Questions</div>
            </div>
            
            <div className="bg-yellow-50 rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-yellow-600">
                {dashboardData.taxonomy_data.reduce((sum, item) => sum + item.medium_attempts, 0)}
              </div>
              <div className="text-sm font-medium text-yellow-700">Medium Questions</div>
            </div>
            
            <div className="bg-red-50 rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-red-600">
                {dashboardData.taxonomy_data.reduce((sum, item) => sum + item.hard_attempts, 0)}
              </div>
              <div className="text-sm font-medium text-red-700">Hard Questions</div>
            </div>
            
            <div className="bg-blue-50 rounded-lg p-6 text-center">
              <div className="text-3xl font-bold text-blue-600">
                {dashboardData.taxonomy_data.reduce((sum, item) => sum + item.total_attempts, 0)}
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