import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './AuthProvider';
import { StudyPlanSystem } from './StudyPlanSystem';
import { SessionSystem } from './SessionSystem';
import { SimpleDashboard } from './SimpleDashboard';
import PYQFilesTable from './PYQFilesTable';

// Smart API URL detection (same as in AuthProvider)
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
    // Custom domain - use correct emergent.host backend URL
    return 'https://adaptive-quant.emergent.host';
  } else if (currentDomain.includes('preview.emergentagent.com')) {
    // Preview domain - use relative URLs
    return '';
  } else {
    // Default fallback for other domains
    return '';
  }
};

const BACKEND_URL = getBackendURL();
const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

export const Dashboard = () => {
  const { user, logout, isAdmin } = useAuth();
  const [currentView, setCurrentView] = useState('dashboard');
  const [dashboardData, setDashboardData] = useState(null);
  const [masteryData, setMasteryData] = useState(null);
  const [progressData, setProgressData] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboard = async () => {
      if (currentView === 'dashboard') {
        // Directly show regular dashboard for all users
        fetchDashboardData();
      }
    };
    
    loadDashboard();
  }, [currentView]);

  const getCategoryColor = (category) => {
    const colors = {
      'A': 'bg-blue-100 text-blue-800',
      'B': 'bg-green-100 text-green-800', 
      'C': 'bg-purple-100 text-purple-800',
      'D': 'bg-orange-100 text-orange-800',
      'E': 'bg-pink-100 text-pink-800'
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  const getMasteryColor = (percentage) => {
    if (percentage >= 85) return 'bg-green-500';
    if (percentage >= 60) return 'bg-blue-500';
    if (percentage >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      console.log('Dashboard: Starting to fetch data...');
      console.log('Dashboard: API endpoint:', API);
      console.log('Dashboard: User:', user);
      
      // Fetch mastery data with detailed progress
      // Using global axios authorization header set by AuthProvider
      console.log('Dashboard: Fetching mastery data...');
      const masteryResponse = await axios.get(`${API}/dashboard/mastery`);
      console.log('Dashboard: Mastery data received:', masteryResponse.data);
      setMasteryData(masteryResponse.data);

      // Fetch overall progress data
      console.log('Dashboard: Fetching progress data...');
      const progressResponse = await axios.get(`${API}/dashboard/progress`);
      console.log('Dashboard: Progress data received:', progressResponse.data);
      setProgressData(progressResponse.data);
      
      console.log('Dashboard: Data loading completed successfully');
      
    } catch (error) {
      console.error('Dashboard: Error fetching dashboard data:', error);
      console.error('Dashboard: Error response:', error.response?.data);
      console.error('Dashboard: Error status:', error.response?.status);
      
      // Set empty data to stop loading state
      setMasteryData({ mastery_by_topic: [], total_topics: 0, detailed_progress: [] });
      setProgressData({ total_sessions: 0, total_minutes: 0, current_streak: 0, sessions_this_week: [] });
      
    } finally {
      console.log('Dashboard: Setting loading to false');
      setLoading(false);
    }
  };

  const startOrResumeSession = async () => {
    try {
      setLoading(true); // Show loading state during session check
      
      // First check if there's an active session for today
      const sessionStatusResponse = await axios.get(`${API}/sessions/current-status`);
      
      if (sessionStatusResponse.data.active_session) {
        // Resume existing session
        const existingSessionId = sessionStatusResponse.data.session_id;
        const progress = sessionStatusResponse.data.progress;
        
        setActiveSessionId(existingSessionId);
        
        // Optional: Show resumption message
        console.log(`Resuming session: Question ${progress.next_question} of ${progress.total}`);
        
        return true;
      } else {
        // No active session, create new one
        const response = await axios.post(`${API}/sessions/start`, {});
        setActiveSessionId(response.data.session_id);
        
        console.log('Started new session:', response.data.session_id);
        return true;
      }
    } catch (err) {
      console.error('Error starting/resuming session:', err);
      alert('Failed to start/resume session');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const handleSessionEnd = () => {
    setActiveSessionId(null);
    setCurrentView('dashboard');
    fetchDashboardData(); // Refresh dashboard data
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
  };

  const renderNavigation = () => {
    // Admin gets no navigation - direct admin panel only
    if (isAdmin()) {
      return (
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-24">
              <div className="flex items-center">
                <img 
                  src="/images/twelvr-logo.png" 
                  alt="Twelvr Logo" 
                  className="h-24 w-auto"
                  style={{backgroundColor: 'transparent'}}
                />
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-sm text-gray-700">
                  <span className="font-medium">{user.name}</span>
                  <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Admin
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="text-sm bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded transition-colors"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </nav>
      );
    }
    
    // Regular users get simplified navigation (no manual study plan selection)
    return (
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-24">
            <div className="flex items-center space-x-8">
              <div className="flex items-center">
                <img 
                  src="/images/twelvr-logo.png" 
                  alt="Twelvr Logo" 
                  className="h-24 w-auto"
                  style={{backgroundColor: 'transparent'}}
                />
              </div>
              <div className="flex space-x-8">
                <button
                  onClick={() => setCurrentView('dashboard')}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium border-b-2 ${
                    currentView === 'dashboard' 
                      ? 'text-blue-600 border-blue-500' 
                      : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">🏠</span>
                  Dashboard
                </button>
                <button
                  onClick={async () => {
                    const sessionStarted = await startOrResumeSession();
                    if (sessionStarted) {
                      setCurrentView('session');
                    }
                  }}
                  disabled={loading}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium border-b-2 ${
                    currentView === 'session'
                      ? 'text-green-600 border-green-500'
                      : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300'
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <span className="mr-2">🎯</span>
                  {loading ? 'Loading...' : "Today's Session"}
                </button>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-700">
                <span className="font-medium">{user.name}</span>
              </div>
              <button
                onClick={logout}
                className="text-sm bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>
    );
  };

  const renderDashboard = () => {
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
          {/* Welcome Section */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Welcome back, {user.name}!</h1>
            <p className="mt-2 text-gray-600">
              Track your CAT preparation progress with Twelvr's AI-powered platform
            </p>
          </div>

          {/* Progress Overview Cards */}
          {progressData && (
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="bg-white p-6 rounded-lg shadow">
                <div className="text-3xl font-bold text-blue-600">{progressData.total_sessions || 0}</div>
                <div className="text-sm text-gray-600">Study Sessions</div>
                <div className="text-xs text-gray-500 mt-1">
                  {progressData.total_minutes || 0} minutes practiced
                </div>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <div className="text-3xl font-bold text-green-600">{progressData.total_questions || 0}</div>
                <div className="text-sm text-gray-600">Questions Solved</div>
                <div className="text-xs text-gray-500 mt-1">
                  {progressData.accuracy || 0}% accuracy
                </div>
              </div>
            </div>
          )}

          {/* Category Progress Dashboard */}
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h3 className="text-xl font-semibold text-gray-900 mb-6">Category Progress</h3>
            
            {masteryData && masteryData.mastery_by_topic && masteryData.mastery_by_topic.length > 0 ? (
              <div className="space-y-6">
                {masteryData.mastery_by_topic.map((categoryData) => {
                  // Calculate progress percentage based on current day vs 90-day target
                  const currentDay = progressData?.current_day || 1;
                  const targetDay = 90;
                  const timeProgress = Math.min(100, (currentDay / targetDay) * 100);
                  const performanceProgress = categoryData.mastery_percentage || 0;
                  
                  // Overall progress combines time and performance
                  const overallProgress = Math.min(100, (timeProgress * 0.3) + (performanceProgress * 0.7));
                  
                  return (
                    <div key={categoryData.topic_name} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h4 className="font-semibold text-gray-900 text-lg">{categoryData.topic_name}</h4>
                          <p className="text-sm text-gray-600">
                            {categoryData.questions_attempted} questions • Last practiced: {categoryData.last_attempt_date ? formatDate(categoryData.last_attempt_date) : 'Not started'}
                          </p>
                        </div>
                        <div className="text-right">
                          <div className={`text-2xl font-bold ${
                            overallProgress > 80 ? 'text-green-600' :
                            overallProgress > 60 ? 'text-blue-600' :
                            overallProgress > 40 ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {Math.round(overallProgress)}%
                          </div>
                          <div className="text-xs text-gray-500">Progress</div>
                        </div>
                      </div>
                      
                      {/* Subcategories */}
                      {categoryData.subcategories && categoryData.subcategories.length > 0 && (
                        <div className="space-y-3">
                          <h5 className="text-sm font-medium text-gray-700">Subcategories:</h5>
                          {categoryData.subcategories.map((subcat, index) => {
                            const subcatProgress = Math.min(100, (subcat.mastery_percentage || 0));
                            return (
                              <div key={index} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
                                <span className="text-sm text-gray-800">{subcat.name}</span>
                                <div className="flex items-center space-x-2">
                                  <div className="w-24 bg-gray-200 rounded-full h-2">
                                    <div 
                                      className={`h-2 rounded-full transition-all duration-300 ${
                                        subcatProgress > 80 ? 'bg-green-500' :
                                        subcatProgress > 60 ? 'bg-blue-500' :
                                        subcatProgress > 40 ? 'bg-yellow-500' :
                                        'bg-red-500'
                                      }`}
                                      style={{ width: `${subcatProgress}%` }}
                                    ></div>
                                  </div>
                                  <span className="text-xs text-gray-600 w-10 text-right">{Math.round(subcatProgress)}%</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                      
                      {/* Overall Progress Bar */}
                      <div className="mt-4">
                        <div className="flex justify-between text-sm text-gray-600 mb-2">
                          <span>Overall Progress</span>
                          <span>{Math.round(overallProgress)}% Complete</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3">
                          <div 
                            className={`h-3 rounded-full transition-all duration-500 ${
                              overallProgress > 80 ? 'bg-green-500' :
                              overallProgress > 60 ? 'bg-blue-500' :
                              overallProgress > 40 ? 'bg-yellow-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${overallProgress}%` }}
                          ></div>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>Study Day {currentDay}</span>
                          <span>{Math.round(performanceProgress)}% Mastery</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>Start studying to see your category progress</p>
              </div>
            )}
          </div>

          {/* Comprehensive Progress Table - All Canonical Taxonomy */}
          {masteryData && masteryData.detailed_progress && masteryData.detailed_progress.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">Complete CAT Syllabus Progress</h3>
              <p className="text-sm text-gray-600 mb-4">Your progress across all canonical taxonomy categories and subcategories</p>
              
              <div className="overflow-x-auto">
                <table className="min-w-full table-auto">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subcategory</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Easy</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Medium</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Hard</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Total Solved</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Mastery Level</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {masteryData.detailed_progress.map((item, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getCategoryColor(item.category?.charAt(0))}`}>
                              {item.category}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-sm text-gray-900 max-w-xs">
                          <div className="truncate" title={item.subcategory}>
                            {item.subcategory}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <div className="text-sm">
                            <span className="text-green-600 font-medium">{item.difficulty_breakdown?.Easy?.solved || 0}</span>
                            <span className="text-xs text-gray-400">/{item.difficulty_breakdown?.Easy?.total || 0}</span>
                          </div>
                          {item.difficulty_breakdown?.Easy?.total > 0 && (
                            <div className="text-xs text-gray-500">
                              {Math.round((item.difficulty_breakdown.Easy.solved / item.difficulty_breakdown.Easy.total) * 100)}%
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <div className="text-sm">
                            <span className="text-yellow-600 font-medium">{item.difficulty_breakdown?.Medium?.solved || 0}</span>
                            <span className="text-xs text-gray-400">/{item.difficulty_breakdown?.Medium?.total || 0}</span>
                          </div>
                          {item.difficulty_breakdown?.Medium?.total > 0 && (
                            <div className="text-xs text-gray-500">
                              {Math.round((item.difficulty_breakdown.Medium.solved / item.difficulty_breakdown.Medium.total) * 100)}%
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <div className="text-sm">
                            <span className="text-red-600 font-medium">{item.difficulty_breakdown?.Hard?.solved || 0}</span>
                            <span className="text-xs text-gray-400">/{item.difficulty_breakdown?.Hard?.total || 0}</span>
                          </div>
                          {item.difficulty_breakdown?.Hard?.total > 0 && (
                            <div className="text-xs text-gray-500">
                              {Math.round((item.difficulty_breakdown.Hard.solved / item.difficulty_breakdown.Hard.total) * 100)}%
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <div className="text-sm font-medium text-gray-900">
                            {item.summary?.total_solved || 0}
                          </div>
                          <div className="text-xs text-gray-400">
                            /{item.summary?.total_questions || 0} questions
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <div className="flex flex-col items-center">
                            <div className="w-16 bg-gray-200 rounded-full h-2 mb-1">
                              <div 
                                className={`h-2 rounded-full ${getMasteryColor(item.summary?.mastery_percentage || 0)}`}
                                style={{ width: `${Math.min(item.summary?.mastery_percentage || 0, 100)}%` }}
                              ></div>
                            </div>
                            <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                              item.summary?.mastery_level === 'Mastered' ? 'bg-green-100 text-green-800' :
                              item.summary?.mastery_level === 'On Track' ? 'bg-blue-100 text-blue-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {item.summary?.mastery_level || 'Needs Focus'}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Comprehensive Summary Stats */}
              <div className="mt-6 grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600">
                    {masteryData.detailed_progress.reduce((sum, item) => sum + (item.difficulty_breakdown?.Easy?.solved || 0), 0)}
                  </div>
                  <div className="text-sm text-green-700">Easy Solved</div>
                  <div className="text-xs text-green-600 mt-1">
                    /{masteryData.detailed_progress.reduce((sum, item) => sum + (item.difficulty_breakdown?.Easy?.total || 0), 0)} available
                  </div>
                </div>
                <div className="bg-yellow-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-yellow-600">
                    {masteryData.detailed_progress.reduce((sum, item) => sum + (item.difficulty_breakdown?.Medium?.solved || 0), 0)}
                  </div>
                  <div className="text-sm text-yellow-700">Medium Solved</div>
                  <div className="text-xs text-yellow-600 mt-1">
                    /{masteryData.detailed_progress.reduce((sum, item) => sum + (item.difficulty_breakdown?.Medium?.total || 0), 0)} available
                  </div>
                </div>
                <div className="bg-red-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-red-600">
                    {masteryData.detailed_progress.reduce((sum, item) => sum + (item.difficulty_breakdown?.Hard?.solved || 0), 0)}
                  </div>
                  <div className="text-sm text-red-700">Hard Solved</div>
                  <div className="text-xs text-red-600 mt-1">
                    /{masteryData.detailed_progress.reduce((sum, item) => sum + (item.difficulty_breakdown?.Hard?.total || 0), 0)} available
                  </div>
                </div>
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {masteryData.detailed_progress.reduce((sum, item) => sum + (item.summary?.total_solved || 0), 0)}
                  </div>
                  <div className="text-sm text-blue-700">Total Solved</div>
                  <div className="text-xs text-blue-600 mt-1">
                    All Categories
                  </div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-purple-600">
                    {masteryData.detailed_progress.filter(item => item.summary?.mastery_level === 'Mastered').length}
                  </div>
                  <div className="text-sm text-purple-700">Mastered Topics</div>
                  <div className="text-xs text-purple-600 mt-1">
                    /{masteryData.detailed_progress.length} total
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Recent Activity */}
          {progressData && progressData.recent_sessions && progressData.recent_sessions.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">Recent Activity</h3>
              <div className="space-y-4">
                {progressData.recent_sessions.slice(0, 5).map((session, index) => (
                  <div key={index} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-b-0">
                    <div>
                      <div className="font-medium text-gray-900">
                        Practice Session • {session.questions_attempted} questions
                      </div>
                      <div className="text-sm text-gray-500">
                        {session.accuracy}% accuracy • {session.duration_minutes} minutes
                      </div>
                    </div>
                    <div className="text-sm text-gray-400">
                      {formatDate(session.session_date)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Render current view
  const renderContent = () => {
    // Admin always sees admin panel
    if (isAdmin()) {
      return <AdminPanel />;
    }
    
    // Regular users
    switch (currentView) {
      case 'study-plan':
        return <StudyPlanSystem />;
      case 'session':
        return <SessionSystem sessionId={activeSessionId} onSessionEnd={handleSessionEnd} />;
      default:
        return renderDashboard();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {renderNavigation()}
      {renderContent()}
    </div>
  );
};

// Admin Panel Component
const AdminPanel = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('pyq-upload');
  const [showQuestionForm, setShowQuestionForm] = useState(false);
  const [questionUploadType, setQuestionUploadType] = useState('single'); // 'single' or 'csv'
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [questionForm, setQuestionForm] = useState({
    stem: "",
    detailed_solution: "",
    hint_category: "",
    hint_subcategory: "",
    tags: [],
    // Image support fields
    has_image: false,
    image_url: "",
    image_alt_text: ""
  });
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imageUrlInput, setImageUrlInput] = useState('');
  const [imagePreviewLoading, setImagePreviewLoading] = useState(false);
  const [imagePreviewError, setImagePreviewError] = useState(false);
  const [questionPublishBlocked, setQuestionPublishBlocked] = useState(false);

  const validateAndPreviewImage = async (url) => {
    if (!url.trim()) {
      setImagePreview(null);
      setImagePreviewError(false);
      setQuestionPublishBlocked(false);
      setQuestionForm(prev => ({
        ...prev,
        has_image: false,
        image_url: "",
        image_alt_text: ""
      }));
      return;
    }

    setImagePreviewLoading(true);
    setImagePreviewError(false);
    
    try {
      // Create a promise to test image loading
      const imageLoadPromise = new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('Image failed to load'));
        img.src = url;
      });

      // Wait for image to load with timeout
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Image load timeout')), 10000)
      );

      await Promise.race([imageLoadPromise, timeoutPromise]);
      
      // Image loaded successfully
      setImagePreview(url);
      setImagePreviewError(false);
      setQuestionPublishBlocked(false);
      setQuestionForm(prev => ({
        ...prev,
        has_image: true,
        image_url: url,
        image_alt_text: prev.image_alt_text || 'Question diagram'
      }));
      
    } catch (error) {
      console.error('Image preview error:', error);
      setImagePreview(null);
      setImagePreviewError(true);
      setQuestionPublishBlocked(true);
      setQuestionForm(prev => ({
        ...prev,
        has_image: false,
        image_url: "",
        image_alt_text: ""
      }));
    } finally {
      setImagePreviewLoading(false);
    }
  };

  const handleImageUrlChange = (e) => {
    const url = e.target.value;
    setImageUrlInput(url);
    
    // Debounce the validation to avoid too many requests
    if (window.imageValidationTimeout) {
      clearTimeout(window.imageValidationTimeout);
    }
    
    window.imageValidationTimeout = setTimeout(() => {
      validateAndPreviewImage(url);
    }, 1000);
  };

  const handleImageUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      alert('Please select a valid image file (JPEG, PNG, GIF, BMP, WebP)');
      return;
    }

    // Validate file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      alert('Image file must be less than 10MB');
      return;
    }

    setUploadingImage(true);
    setSelectedImage(file);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target.result);
    };
    reader.readAsDataURL(file);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('alt_text', questionForm.image_alt_text || '');

      const response = await axios.post(`${API}/admin/image/upload`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`
        }
      });

      // Update form with image data
      setQuestionForm(prev => ({
        ...prev,
        has_image: true,
        image_url: response.data.image_url
      }));

      alert('Image uploaded successfully!');
    } catch (error) {
      console.error('Error uploading image:', error);
      alert('Error uploading image: ' + (error.response?.data?.detail || 'Unknown error'));
      setSelectedImage(null);
      setImagePreview(null);
      setQuestionForm(prev => ({
        ...prev,
        has_image: false,
        image_url: "",
        image_alt_text: ""
      }));
    } finally {
      setUploadingImage(false);
    }
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    setQuestionForm(prev => ({
      ...prev,
      has_image: false,
      image_url: "",
      image_alt_text: ""
    }));
  };

  const handlePYQUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Only accept CSV files now
    if (!file.name.endsWith('.csv')) {
      alert('Only CSV files are supported for PYQ upload. Please use the CSV format with columns: stem, year, image_url');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/admin/pyq/upload`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`
        }
      });
      
      // Show success message with details
      const questionsCreated = response.data?.questions_created || 0;
      const yearsProcessed = response.data?.years_processed || [];
      const imagesProcessed = response.data?.images_processed || 0;
      
      alert(`PYQ CSV uploaded successfully!\n\n` +
            `✅ ${questionsCreated} questions processed\n` +
            `📅 Years: ${yearsProcessed.join(', ')}\n` +
            `🖼️ ${imagesProcessed} images processed\n` +
            `🤖 Automatic LLM enrichment in progress...`);
      
      event.target.value = ''; // Reset file input
    } catch (error) {
      alert('Error uploading PYQ CSV: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  const handleCSVUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/admin/upload-questions-csv`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert('Questions CSV uploaded successfully!');
      event.target.value = ''; // Reset file input
    } catch (error) {
      alert('Error uploading CSV: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  const handleExportQuestions = async () => {
    try {
      const response = await axios.get(`${API}/admin/export-questions-csv`, {
        responseType: 'blob'
      });
      
      // Create blob and download
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `cat_questions_export_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      alert('Questions exported successfully!');
    } catch (error) {
      alert('Error exporting questions: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  const handleExportPYQ = async () => {
    try {
      const response = await axios.get(`${API}/admin/export-pyq-csv`, {
        responseType: 'blob'
      });
      
      // Create blob and download
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `pyq_database_export_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      alert('PYQ database exported successfully!');
    } catch (error) {
      alert('Error exporting PYQ database: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  const handleCheckQuestionQuality = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/admin/check-question-quality`);
      const data = response.data;
      
      const qualityReport = `
🔍 QUESTION QUALITY REPORT
========================

📊 Overall Quality Score: ${data.quality_score}%
📝 Total Questions: ${data.total_questions}
⚠️ Total Issues Found: ${data.total_issues}

📋 Issue Breakdown:
• Generic Solutions: ${data.issues.generic_solutions.length}
• Missing Answers: ${data.issues.missing_answers.length} 
• Solution Mismatches: ${data.issues.solution_mismatch.length}
• Short Solutions: ${data.issues.short_solutions.length}
• Generic Detailed Solutions: ${data.issues.generic_detailed_solutions.length}

💡 Recommendations:
${data.recommendations.immediate_action_needed ? '🚨 IMMEDIATE ACTION NEEDED - High number of quality issues detected!' : '✅ Quality levels are acceptable'}
${data.recommendations.needs_re_enrichment > 0 ? `\n🔧 ${data.recommendations.needs_re_enrichment} questions need re-enrichment` : ''}
${data.recommendations.critical_mismatches > 0 ? `\n⚠️ ${data.recommendations.critical_mismatches} critical solution mismatches found` : ''}

Use the "Fix Solutions" button to automatically resolve these issues.
      `;
      
      alert(qualityReport);
      setLoading(false);
    } catch (error) {
      setLoading(false);
      alert('Error checking question quality: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  const handleReEnrichQuestions = async () => {
    if (!confirm('⚠️ CRITICAL OPERATION\n\nThis will re-enrich ALL questions with generic/wrong solutions using LLM.\nThis process may take several minutes and cannot be undone.\n\nAre you sure you want to continue?')) {
      return;
    }
    
    try {
      setLoading(true);
      alert('🔧 Starting re-enrichment process...\nThis may take several minutes. Please wait for completion message.');
      
      const response = await axios.post(`${API}/admin/re-enrich-all-questions`);
      const data = response.data;
      
      const successReport = `
🎉 RE-ENRICHMENT COMPLETE!
========================

📊 Processing Results:
• Questions Processed: ${data.processed}
• Successfully Fixed: ${data.success}
• Failed to Fix: ${data.failed}
• Success Rate: ${((data.success / data.processed) * 100).toFixed(1)}%

${data.details}

${data.success > 0 ? '✅ Students will now see proper question-specific solutions!' : '❌ No questions were successfully re-enriched.'}
      `;
      
      alert(successReport);
      setLoading(false);
    } catch (error) {
      setLoading(false);
      alert('❌ Re-enrichment failed: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  const handleQuestionSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/questions`, questionForm);
      alert('Question created successfully!');
      setShowQuestionForm(false);
      setQuestionForm({
        stem: "",
        detailed_solution: "",
        hint_category: "",
        hint_subcategory: "",
        tags: [],
        has_image: false,
        image_url: "",
        image_alt_text: ""
      });
      setSelectedImage(null);
      setImagePreview(null);
      setImageUrlInput('');
      setImagePreviewError(false);
      setQuestionPublishBlocked(false);
    } catch (error) {
      alert('Error creating question: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg">
          {/* Tabs */}
          <div className="border-b">
            <nav className="flex space-x-8 px-6">
              <button
                onClick={() => setActiveTab('pyq-upload')}
                className={`py-4 text-lg font-medium ${
                  activeTab === 'pyq-upload' 
                    ? 'text-blue-600 border-b-2 border-blue-500' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                📄 PYQ Upload
              </button>
              <button
                onClick={() => setActiveTab('questions')}
                className={`py-4 text-lg font-medium ${
                  activeTab === 'questions' 
                    ? 'text-blue-600 border-b-2 border-blue-500' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                ❓ Question Upload
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-8">
            {activeTab === 'pyq-upload' && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-semibold text-gray-900">Upload PYQ Data</h2>
                  <div className="flex space-x-3">
                    <button
                      onClick={() => handleExportPYQ()}
                      className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium flex items-center"
                    >
                      📋 Export PYQ Database (CSV)
                    </button>
                    <button
                      onClick={() => handleCheckQuestionQuality()}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium flex items-center"
                    >
                      🔍 Check Quality
                    </button>
                    <button
                      onClick={() => handleReEnrichQuestions()}
                      className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg font-medium flex items-center"
                    >
                      🔧 Fix Solutions
                    </button>
                  </div>
                </div>

                {/* Uploaded Files Tracking Table */}
                <PYQFilesTable />

                <div className="max-w-3xl">

                {/* CSV Upload Only */}
                <div className="border-2 border-green-200 rounded-lg p-8 bg-green-50">
                  <h3 className="text-xl font-semibold text-green-900 mb-4">📊 CSV Upload with LLM Processing</h3>
                  <p className="text-green-700 mb-6">Upload PYQ questions with automatic classification and solution generation</p>
                  
                  {/* CSV Format Info */}
                  <div className="bg-green-100 border border-green-200 rounded-lg p-6 mb-6">
                    <h4 className="text-lg font-medium text-green-800 mb-3">📋 Required CSV Columns</h4>
                    <div className="text-sm text-green-700">
                      <ul className="list-disc list-inside space-y-2">
                        <li><strong>stem</strong> - Question text (Required)</li>
                        <li><strong>year</strong> - PYQ year (Required, e.g., 2024, 2023, 2022)</li>
                        <li><strong>image_url</strong> - Google Drive share link (Optional)</li>
                      </ul>
                      <div className="mt-4 p-3 bg-white rounded border border-green-300">
                        <p className="text-sm font-medium text-green-800 mb-2">Example CSV Format:</p>
                        <code className="text-xs text-green-600 font-mono">
                          stem,year,image_url<br/>
                          "A train travels 120 km in 2 hours. Find speed.",2024,"https://drive.google.com/file/d/FILE_ID/view"<br/>
                          "What is 15% of 200?",2023,""<br/>
                          "Find area of triangle with base 10cm, height 8cm.",2024,"https://drive.google.com/file/d/ANOTHER_ID/view"
                        </code>
                      </div>
                    </div>
                  </div>

                  {/* LLM Auto-Generation Info */}
                  <div className="bg-white border border-green-200 rounded-lg p-6 mb-8">
                    <div className="flex items-start">
                      <div className="flex-shrink-0">
                        <svg className="h-6 w-6 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <h4 className="text-lg font-medium text-green-800">🤖 Automatic LLM Processing</h4>
                        <div className="text-sm text-green-700 mt-2">
                          <p className="mb-3">Just provide question text and year - our AI automatically generates:</p>
                          <div className="grid md:grid-cols-2 gap-4">
                            <ul className="list-disc list-inside space-y-1">
                              <li><strong>Category & Subcategory</strong> - CAT taxonomy classification</li>
                              <li><strong>Question Type</strong> - Specific classification</li>
                            </ul>
                            <ul className="list-disc list-inside space-y-1">
                              <li><strong>Answer</strong> - Correct solution</li>
                              <li><strong>Solutions</strong> - Step-by-step explanations</li>
                            </ul>
                          </div>
                          <p className="mt-3 text-xs text-green-600 font-medium">
                            ✨ Supports multiple years in single CSV • Google Drive image processing • Bulk processing capability
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-center">
                    <label htmlFor="pyq-csv-upload" className="cursor-pointer">
                      <span className="bg-green-600 hover:bg-green-700 text-white px-8 py-4 rounded-lg text-lg font-medium inline-block shadow-lg hover:shadow-xl transition-all">
                        {uploading ? 'Uploading & Processing...' : '📤 Upload PYQ CSV'}
                      </span>
                      <input
                        id="pyq-csv-upload"
                        type="file"
                        accept=".csv"
                        onChange={handlePYQUpload}
                        disabled={uploading}
                        className="hidden"
                      />
                    </label>
                    <p className="text-sm text-green-600 mt-3">
                      Drag and drop CSV file or click to browse • Maximum file size: 10MB
                    </p>
                  </div>
                </div>
                </div>
              </div>
            )}

            {activeTab === 'questions' && (
              <div>
                <div className="flex justify-between items-center mb-8">
                  <h2 className="text-2xl font-semibold text-gray-900">Question Upload</h2>
                  <button
                    onClick={() => handleExportQuestions()}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg font-medium flex items-center"
                  >
                    📊 Export All Questions (CSV)
                  </button>
                </div>

                {/* Upload Type Selection */}
                <div className="mb-8">
                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Single Question */}
                    <div className="border-2 border-gray-200 rounded-lg p-6 text-center">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Single Question</h3>
                      <p className="text-gray-600 mb-6">Add one question at a time using the form</p>
                      <button
                        onClick={() => {
                          setQuestionUploadType('single');
                          setShowQuestionForm(true);
                        }}
                        className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium"
                      >
                        Add Question
                      </button>
                    </div>

                    {/* CSV Upload with Google Drive Images - Simplified Format */}
                    <div className="border-2 border-gray-200 rounded-lg p-6">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">CSV Upload - Simplified Format</h3>
                      <p className="text-gray-600 mb-4">Upload questions with minimal data - LLM generates everything else automatically</p>
                      
                      {/* LLM Auto-Generation Info */}
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                        <div className="flex items-start">
                          <div className="flex-shrink-0">
                            <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                          </div>
                          <div className="ml-3">
                            <h4 className="text-sm font-medium text-green-800">🤖 Complete LLM Auto-Generation</h4>
                            <div className="text-sm text-green-700 mt-1">
                              <p className="mb-2">Just provide the question text - LLM automatically generates:</p>
                              <ul className="list-disc list-inside space-y-1 text-xs">
                                <li><strong>Answer</strong> - Correct solution to the question</li>
                                <li><strong>Category & Subcategory</strong> - Proper CAT taxonomy classification</li>
                                <li><strong>Solutions</strong> - Step-by-step solution approach and detailed explanation</li>
                                <li><strong>Difficulty Analysis</strong> - AI-powered difficulty scoring and band classification</li>
                                <li><strong>Learning Metrics</strong> - Importance index, learning impact, frequency band</li>
                                <li><strong>Tags</strong> - Relevant topic tags for search and organization</li>
                              </ul>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      {/* CSV Format Info */}
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                        <div className="flex items-start">
                          <div className="flex-shrink-0">
                            <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                          </div>
                          <div className="ml-3">
                            <h4 className="text-sm font-medium text-blue-800">📋 Simplified CSV Format</h4>
                            <div className="text-sm text-blue-700 mt-1">
                              <p className="mb-2">CSV columns needed:</p>
                              <ul className="list-disc list-inside space-y-1 text-xs">
                                <li><strong>stem</strong> - Question text (Required)</li>
                                <li><strong>image_url</strong> - Google Drive share link (Optional)</li>
                              </ul>
                              <p className="mt-2 text-xs">Example: "A train travels 120 km in 2 hours. Find the speed.","https://drive.google.com/file/d/FILE_ID/view"</p>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-center">
                        <label htmlFor="csv-upload" className="cursor-pointer">
                          <span className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-medium inline-block">
                            {uploading ? 'Uploading & Processing...' : 'Upload CSV'}
                          </span>
                          <input
                            id="csv-upload"
                            type="file"
                            accept=".csv"
                            onChange={handleCSVUpload}
                            disabled={uploading}
                            className="hidden"
                          />
                        </label>
                        <div className="text-sm text-gray-500 mt-3 space-y-1">
                          <p><strong>Required:</strong> stem (question text)</p>
                          <p><strong>Optional:</strong> image_url (Google Drive link)</p>
                          <p className="text-xs text-gray-400">🤖 LLM generates: answers, categories, solutions, difficulty, tags</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Single Question Form */}
                {showQuestionForm && questionUploadType === 'single' && (
                  <div className="bg-gray-50 p-6 rounded-lg mb-8">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Add Single Question</h3>
                      <button
                        onClick={() => setShowQuestionForm(false)}
                        className="text-gray-500 hover:text-gray-700"
                      >
                        ✕ Cancel
                      </button>
                    </div>
                    
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                      <div className="flex items-start">
                        <div className="flex-shrink-0">
                          <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                          </svg>
                        </div>
                        <div className="ml-3">
                          <h4 className="text-sm font-medium text-blue-800">LLM Auto-Generation</h4>
                          <p className="text-sm text-blue-700 mt-1">
                            The LLM will automatically generate: <strong>Answer, Solution Approach, Source identification, Category/Subcategory classification, and Difficulty analysis</strong>. You only need to provide the question stem.
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    <form onSubmit={handleQuestionSubmit} className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Question Stem</label>
                        <textarea
                          value={questionForm.stem}
                          onChange={(e) => setQuestionForm({...questionForm, stem: e.target.value})}
                          className="mt-1 block w-full border border-gray-300 rounded-md p-3"
                          rows="4"
                          required
                          placeholder="Enter the question text here..."
                        />
                      </div>

                      {/* Image URL Input with Live Preview */}
                      <div className="border border-gray-200 rounded-lg p-4">
                        <label className="block text-sm font-medium text-gray-700 mb-3">Question Image (Optional)</label>
                        
                        <div className="space-y-4">
                          {/* URL Input Field */}
                          <div>
                            <label htmlFor="image-url" className="block text-xs font-medium text-gray-600 mb-1">
                              Google Drive Share Link or Direct Image URL
                            </label>
                            <input
                              id="image-url"
                              type="url"
                              value={imageUrlInput}
                              onChange={handleImageUrlChange}
                              className="w-full border border-gray-300 rounded-md p-3 text-sm"
                              placeholder="https://drive.google.com/file/d/FILE_ID/view or direct image URL"
                            />
                          </div>

                          {/* Image Preview Area */}
                          {imagePreviewLoading && (
                            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                              <div className="flex items-center justify-center">
                                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
                                <span className="ml-2 text-sm text-gray-600">Loading image preview...</span>
                              </div>
                            </div>
                          )}

                          {imagePreview && !imagePreviewLoading && (
                            <div className="space-y-3">
                              <div className="relative">
                                <img 
                                  src={imagePreview} 
                                  alt="Image preview" 
                                  className="max-w-full h-auto max-h-64 rounded-lg shadow-sm mx-auto border"
                                />
                                <div className="absolute top-2 right-2 bg-green-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs">
                                  ✓
                                </div>
                              </div>
                              <p className="text-xs text-green-600 text-center">✅ Image loaded successfully - Question can be published</p>
                            </div>
                          )}

                          {imagePreviewError && !imagePreviewLoading && (
                            <div className="border-2 border-dashed border-red-300 bg-red-50 rounded-lg p-6 text-center">
                              <div className="mb-2">
                                <svg className="mx-auto h-8 w-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L3.314 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                </svg>
                              </div>
                              <p className="text-sm text-red-600 font-medium">❌ Image Missing – Not Eligible for Serving</p>
                              <p className="text-xs text-red-500 mt-1">Please check the URL or use a different image</p>
                            </div>
                          )}

                          {!imageUrlInput && !imagePreviewLoading && (
                            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                              <svg className="mx-auto h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                              </svg>
                              <p className="text-sm text-gray-500 mt-2">Enter an image URL above to see preview</p>
                              <p className="text-xs text-gray-400 mt-1">Question will work without image</p>
                            </div>
                          )}
                        </div>
                      </div>



                      <button
                        type="submit"
                        disabled={questionPublishBlocked}
                        className={`px-8 py-3 rounded-lg font-medium text-lg ${
                          questionPublishBlocked 
                            ? 'bg-gray-400 cursor-not-allowed text-white' 
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                        }`}
                      >
                        {questionPublishBlocked 
                          ? '❌ Cannot Publish - Fix Image First' 
                          : 'Create Question (LLM will generate answer & solution)'
                        }
                      </button>
                      
                      {questionPublishBlocked && (
                        <p className="text-sm text-red-600 mt-2 text-center">
                          Question publishing is blocked until image loads successfully
                        </p>
                      )}
                    </form>
                  </div>
                )}

              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const PracticeSystem = () => {
  return <div className="p-8 text-center">Practice System - Will integrate with existing Practice component</div>;
};

export default Dashboard;