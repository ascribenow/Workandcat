import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './AuthProvider';
import { StudyPlanSystem } from './StudyPlanSystem';
import { SessionSystem } from './SessionSystem';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
      
      // Fetch mastery data with detailed progress
      const masteryResponse = await axios.get(`${API}/dashboard/mastery`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}` }
      });
      setMasteryData(masteryResponse.data);

      // Fetch overall progress data
      const progressResponse = await axios.get(`${API}/dashboard/progress`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}` }
      });
      setProgressData(progressResponse.data);
      
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const startQuickSession = async (minutes = 30) => {
    try {
      const response = await axios.post(`${API}/session/start`, {
        target_minutes: minutes
      }, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}` }
      });
      setActiveSessionId(response.data.session_id);
      // Don't set view here - let the button handler do it after session is started
    } catch (err) {
      console.error('Error starting session:', err);
      alert('Failed to start session');
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
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">CAT Prep Admin Panel</h1>
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
          <div className="flex justify-between h-16">
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
                  await startQuickSession(30); // Start a 30-minute session and wait
                  setCurrentView('session'); // Then change view
                }}
                className={`inline-flex items-center px-1 pt-1 text-sm font-medium border-b-2 ${
                  currentView === 'session' 
                    ? 'text-blue-600 border-blue-500' 
                    : 'text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">📝</span>
                Practice Session
              </button>
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
              Track your CAT preparation progress across all categories
            </p>
          </div>

          {/* Progress Overview Cards */}
          {progressData && (
            <div className="grid md:grid-cols-4 gap-6 mb-8">
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
              
              <div className="bg-white p-6 rounded-lg shadow">
                <div className="text-3xl font-bold text-purple-600">{progressData.current_streak || 0}</div>
                <div className="text-sm text-gray-600">Day Streak</div>
                <div className="text-xs text-gray-500 mt-1">
                  {progressData.longest_streak || 0} longest streak
                </div>
              </div>
              
              <div className="bg-white p-6 rounded-lg shadow">
                <div className="text-3xl font-bold text-yellow-600">{Math.round(progressData.days_remaining || 90)}</div>
                <div className="text-sm text-gray-600">Days Remaining</div>
                <div className="text-xs text-gray-500 mt-1">
                  Out of 90-day plan
                </div>
              </div>
            </div>
          )}

          {/* Category Progress Dashboard */}
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h3 className="text-xl font-semibold text-gray-900 mb-6">Category Progress (90-Day Plan)</h3>
            
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
                          <span>Day {currentDay} of 90</span>
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

          {/* Detailed Progress Table */}
          {masteryData && masteryData.detailed_progress && masteryData.detailed_progress.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">Detailed Progress Breakdown</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full table-auto">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subcategory</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Question Type</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Easy</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Medium</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Hard</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Mastery</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {masteryData.detailed_progress.map((item, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getCategoryColor(item.category)}`}>
                              {item.category}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{item.subcategory}</td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-600">{item.question_type || 'General'}</td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <span className="text-sm text-green-600 font-medium">{item.easy_solved || 0}</span>
                          <span className="text-xs text-gray-400">/{item.easy_total || 0}</span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <span className="text-sm text-yellow-600 font-medium">{item.medium_solved || 0}</span>
                          <span className="text-xs text-gray-400">/{item.medium_total || 0}</span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <span className="text-sm text-red-600 font-medium">{item.hard_solved || 0}</span>
                          <span className="text-xs text-gray-400">/{item.hard_total || 0}</span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <span className="text-sm font-medium text-gray-900">
                            {(item.easy_solved || 0) + (item.medium_solved || 0) + (item.hard_solved || 0)}
                          </span>
                          <span className="text-xs text-gray-400">
                            /{(item.easy_total || 0) + (item.medium_total || 0) + (item.hard_total || 0)}
                          </span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <div className="flex items-center justify-center">
                            <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                              <div 
                                className={`h-2 rounded-full ${getMasteryColor(item.mastery_percentage)}`}
                                style={{ width: `${Math.min(item.mastery_percentage || 0, 100)}%` }}
                              ></div>
                            </div>
                            <span className="text-sm font-medium text-gray-900">
                              {Math.round(item.mastery_percentage || 0)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Summary Stats */}
              <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600">
                    {masteryData.detailed_progress.reduce((sum, item) => sum + (item.easy_solved || 0), 0)}
                  </div>
                  <div className="text-sm text-green-700">Easy Questions Solved</div>
                </div>
                <div className="bg-yellow-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-yellow-600">
                    {masteryData.detailed_progress.reduce((sum, item) => sum + (item.medium_solved || 0), 0)}
                  </div>
                  <div className="text-sm text-yellow-700">Medium Questions Solved</div>
                </div>
                <div className="bg-red-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-red-600">
                    {masteryData.detailed_progress.reduce((sum, item) => sum + (item.hard_solved || 0), 0)}
                  </div>
                  <div className="text-sm text-red-700">Hard Questions Solved</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-2xl font-bold text-blue-600">
                    {masteryData.detailed_progress.reduce((sum, item) => sum + (item.easy_solved || 0) + (item.medium_solved || 0) + (item.hard_solved || 0), 0)}
                  </div>
                  <div className="text-sm text-blue-700">Total Questions Solved</div>
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

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('year', '2024');

    try {
      const response = await axios.post(`${API}/admin/pyq/upload`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`
        }
      });
      alert('PYQ uploaded successfully!');
      event.target.value = ''; // Reset file input
    } catch (error) {
      alert('Error uploading PYQ: ' + (error.response?.data?.detail || 'Unknown error'));
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
              <div className="max-w-3xl">
                <h2 className="text-2xl font-semibold text-gray-900 mb-6">Upload PYQ Files</h2>
                
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                  <div className="mb-6">
                    <svg className="mx-auto h-16 w-16 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                      <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <div className="mb-6">
                    <label htmlFor="pyq-upload" className="cursor-pointer">
                      <span className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-lg text-lg font-medium">
                        {uploading ? 'Uploading...' : 'Select PYQ File'}
                      </span>
                      <input
                        id="pyq-upload"
                        type="file"
                        accept=".docx,.doc,.pdf"
                        onChange={handlePYQUpload}
                        disabled={uploading}
                        className="hidden"
                      />
                    </label>
                  </div>
                  <p className="text-gray-600">
                    Upload previous year question papers in Word or PDF format
                  </p>
                  <p className="text-sm text-gray-500 mt-2">
                    Supported formats: .docx, .doc, .pdf
                  </p>
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

                      {/* Image Upload Section */}
                      <div className="border border-gray-200 rounded-lg p-4">
                        <label className="block text-sm font-medium text-gray-700 mb-3">Question Image (Optional)</label>
                        
                        {!imagePreview ? (
                          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                            <div className="mb-4">
                              <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            </div>
                            <div className="mb-4">
                              <label htmlFor="image-upload" className="cursor-pointer">
                                <span className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium">
                                  {uploadingImage ? 'Uploading...' : 'Upload Image'}
                                </span>
                                <input
                                  id="image-upload"
                                  type="file"
                                  accept="image/*"
                                  onChange={handleImageUpload}
                                  disabled={uploadingImage}
                                  className="hidden"
                                />
                              </label>
                            </div>
                            <p className="text-xs text-gray-500">
                              Support: JPEG, PNG, GIF, BMP, WebP • Max size: 10MB
                            </p>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            <div className="relative">
                              <img 
                                src={imagePreview} 
                                alt="Question image preview" 
                                className="max-w-full h-auto max-h-64 rounded-lg shadow-sm mx-auto"
                              />
                              <button
                                type="button"
                                onClick={handleRemoveImage}
                                className="absolute top-2 right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm"
                              >
                                ×
                              </button>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700">Alt Text for Accessibility</label>
                              <input
                                type="text"
                                value={questionForm.image_alt_text}
                                onChange={(e) => setQuestionForm({...questionForm, image_alt_text: e.target.value})}
                                className="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm"
                                placeholder="Describe the image for screen readers"
                              />
                            </div>
                          </div>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700">Detailed Solution (Optional)</label>
                        <textarea
                          value={questionForm.detailed_solution}
                          onChange={(e) => setQuestionForm({...questionForm, detailed_solution: e.target.value})}
                          className="mt-1 block w-full border border-gray-300 rounded-md p-3"
                          rows="4"
                          placeholder="Detailed step-by-step solution (optional - can be generated by LLM)"
                        />
                      </div>

                      <button
                        type="submit"
                        className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-medium text-lg"
                      >
                        Create Question (LLM will generate answer & solution)
                      </button>
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