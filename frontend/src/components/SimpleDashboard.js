import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Smart API URL detection (same as in Dashboard.js)
const getBackendURL = () => {
  // If environment variable is set, use it
  if (process.env.REACT_APP_BACKEND_URL && process.env.REACT_APP_BACKEND_URL.trim()) {
    return process.env.REACT_APP_BACKEND_URL;
  }
  
  // Auto-detect based on current domain
  const currentDomain = window.location.hostname;
  
  if (currentDomain === 'localhost' || currentDomain === '127.0.0.1') {
    return 'http://localhost:8001';
  } else if (currentDomain === 'twelvr.com' || currentDomain.includes('twelvr')) {
    return 'https://adaptive-quant.emergent.host';
  } else if (currentDomain.includes('preview.emergentagent.com')) {
    return '';
  } else {
    return '';
  }
};

const BACKEND_URL = getBackendURL();
const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

export const SimpleDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      console.log('SimpleDashboard: Fetching simple taxonomy data...');
      
      const response = await axios.get(`${API}/dashboard/simple-taxonomy`);
      console.log('SimpleDashboard: Data received:', response.data);
      
      setDashboardData(response.data);
      
    } catch (error) {
      console.error('SimpleDashboard: Error fetching data:', error);
      // Set empty data to stop loading
      setDashboardData({ total_sessions: 0, taxonomy_data: [] });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
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
            
            <div className="overflow-x-auto">
              <table className="min-w-full table-auto">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 uppercase tracking-wider">
                      Category - Subcategory - Type
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-500 uppercase tracking-wider">
                      Easy
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-500 uppercase tracking-wider">
                      Medium
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-500 uppercase tracking-wider">
                      Hard
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {dashboardData?.taxonomy_data?.map((item, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-4 text-sm text-gray-900">
                        <div className="font-medium">
                          {item.category} - {item.subcategory} - {item.type}
                        </div>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                          item.easy_attempts > 0 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-gray-100 text-gray-400'
                        }`}>
                          {item.easy_attempts}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                          item.medium_attempts > 0 
                            ? 'bg-yellow-100 text-yellow-800' 
                            : 'bg-gray-100 text-gray-400'
                        }`}>
                          {item.medium_attempts}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                          item.hard_attempts > 0 
                            ? 'bg-red-100 text-red-800' 
                            : 'bg-gray-100 text-gray-400'
                        }`}>
                          {item.hard_attempts}
                        </span>
                      </td>
                    </tr>
                  )) || []}
                </tbody>
              </table>
            </div>
            
            {(!dashboardData?.taxonomy_data || dashboardData.taxonomy_data.length === 0) && (
              <div className="text-center py-8 text-gray-500">
                <p>Complete some study sessions to see your progress across the CAT syllabus</p>
              </div>
            )}
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
        
      </div>
    </div>
  );
};