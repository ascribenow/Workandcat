import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth, API } from './AuthProvider';
import { StudyPlanSystem } from './StudyPlanSystem';
import { SessionSystem } from './SessionSystem';
import { SimpleDashboard } from './SimpleDashboard';
import PYQFilesTable from './PYQFilesTable';
import UpgradeModal from './UpgradeModal';
import Privileges from './Privileges';

export const Dashboard = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  // Default view: admins go to dashboard, regular users go to session (immediately start active session)
  const [currentView, setCurrentView] = useState(isAdmin() ? 'dashboard' : 'session');
  const [dashboardData, setDashboardData] = useState(null);
  const [masteryData, setMasteryData] = useState(null);
  const [progressData, setProgressData] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sessionMetadata, setSessionMetadata] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Session limit state
  const [sessionLimitStatus, setSessionLimitStatus] = useState(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  useEffect(() => {
    const loadDashboard = async () => {
      if (currentView === 'dashboard') {
        // Show dashboard for admin users or when explicitly navigated to dashboard
        fetchDashboardData();
      } else if (currentView === 'session' && !activeSessionId && !isAdmin()) {
        // Auto-start session for regular users when they first log in (immediately jump to questions)
        const sessionStarted = await startOrResumeSession();
        if (!sessionStarted) {
          // If session failed to start, redirect to dashboard
          setCurrentView('dashboard');
          fetchDashboardData();
        }
      }
    };
    
    loadDashboard();
  }, [currentView]);

  const getCategoryColor = (category) => {
    const colors = {
      'A': 'bg-[#f7fdf0] text-[#9ac026]',
      'B': 'bg-[#f7fdf0] text-[#9ac026]', 
      'C': 'bg-[#fff5f3] text-[#ff6d4d]',
      'D': 'bg-[#f5f5f5] text-[#545454]',
      'E': 'bg-[#fff5f3] text-[#ff6d4d]'
    };
    return colors[category] || 'bg-[#f5f5f5] text-[#545454]';
  };

  const getMasteryColor = (percentage) => {
    if (percentage >= 85) return 'bg-[#9ac026]';
    if (percentage >= 60) return 'bg-[#9ac026]';
    if (percentage >= 40) return 'bg-[#ff6d4d]';
    return 'bg-[#ff6d4d]';
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

      // Fetch session limit status
      console.log('Dashboard: Fetching session limit status...');
      const limitResponse = await axios.get(`${API}/user/session-limit-status`);
      console.log('Dashboard: Session limit status received:', limitResponse.data);
      setSessionLimitStatus(limitResponse.data);
      
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
      console.log('Dashboard: Checking for active sessions or starting new session...');
      
      // First check session limit status
      if (!sessionLimitStatus) {
        console.log('Dashboard: Session limit status not loaded, fetching...');
        const limitResponse = await axios.get(`${API}/user/session-limit-status`);
        setSessionLimitStatus(limitResponse.data);
        
        // If limit reached, show upgrade modal and prevent session start
        if (limitResponse.data.limit_reached) {
          console.log('Dashboard: Session limit reached, showing upgrade modal');
          setShowUpgradeModal(true);
          setCurrentView('dashboard');
          return false;
        }
      } else if (sessionLimitStatus.limit_reached) {
        console.log('Dashboard: Session limit already reached, showing upgrade modal');
        setShowUpgradeModal(true);
        setCurrentView('dashboard');
        return false;
      }
      
      // Check for existing active session
      const sessionStatusResponse = await axios.get(`${API}/sessions/status`);
      console.log('Dashboard: Session status response:', sessionStatusResponse.data);
      
      if (sessionStatusResponse.data.active_session) {
        console.log('Dashboard: Active session found, resuming...');
        const existingSessionId = sessionStatusResponse.data.session_id;
        const progress = sessionStatusResponse.data.progress;
        
        setActiveSessionId(existingSessionId);
        
        // For resumed sessions, create a minimal metadata object with session number calculation
        try {
          const dashboardResponse = await axios.get(`${API}/dashboard/simple-taxonomy`);
          const totalSessions = dashboardResponse.data.total_sessions || 0;
          const currentSession = totalSessions + 1; // Current session number is completed sessions + 1
          
          setSessionMetadata({
            phase_info: {
              current_session: currentSession
            }
          });
          console.log(`Resuming session #${currentSession}: Question ${progress.next_question} of ${progress.total}`);
        } catch (error) {
          console.error('Failed to get session metadata for resumed session:', error);
          setSessionMetadata(null);
        }
        
        return true;
      } else {
        console.log('Dashboard: No active session found, starting new session...');
        const startResponse = await axios.post(`${API}/sessions/start`, {});
        console.log('Dashboard: New session started:', startResponse.data);
        
        setActiveSessionId(startResponse.data.session_id);
        
        // For new sessions, use provided metadata
        if (startResponse.data.metadata) {
          setSessionMetadata(startResponse.data.metadata);
        }
        
        return true;
      }
      
    } catch (error) {
      console.error('Dashboard: Error starting/resuming session:', error);
      if (error.response?.status === 401) {
        // Handle authentication error
        logout();
        return false;
      }
      // For other errors, redirect to dashboard
      setCurrentView('dashboard');
      return false;
    }
  };

  const handleSessionEnd = () => {
    setActiveSessionId(null);
    setSessionMetadata(null);
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
        <nav className="bg-white shadow-sm border-b" style={{ borderColor: '#f5f5f5' }}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <img 
                  src="https://customer-assets.emergentagent.com/job_adaptive-cat/artifacts/vv2teh18_Twelver%20edited.png" 
                  alt="Twelvr" 
                  className="h-8 sm:h-10 w-auto"
                />
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-sm" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  <span className="font-medium">{user.name}</span>
                  <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ 
                    backgroundColor: '#f7fdf0', 
                    color: '#9ac026',
                    fontFamily: 'Lato, sans-serif'
                  }}>
                    Admin
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="text-sm px-3 py-1 rounded transition-colors"
                  style={{ 
                    backgroundColor: '#f5f5f5', 
                    color: '#545454',
                    fontFamily: 'Lato, sans-serif'
                  }}
                  onMouseOver={(e) => {
                    e.target.style.backgroundColor = '#ff6d4d';
                    e.target.style.color = 'white';
                  }}
                  onMouseOut={(e) => {
                    e.target.style.backgroundColor = '#f5f5f5';
                    e.target.style.color = '#545454';
                  }}
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
      <nav className="bg-white shadow-sm border-b" style={{ borderColor: '#f5f5f5' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-8">
              <div className="flex items-center">
                <img 
                  src="https://customer-assets.emergentagent.com/job_adaptive-cat/artifacts/vv2teh18_Twelver%20edited.png" 
                  alt="Twelvr" 
                  className="h-8 sm:h-10 w-auto"
                />
              </div>
              <div className="flex space-x-8">
                <button
                  onClick={() => setCurrentView('dashboard')}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium border-b-2 transition-colors ${
                    currentView === 'dashboard' 
                      ? 'border-[#9ac026] text-[#545454]' 
                      : 'text-[#545454] border-transparent hover:text-[#ff6d4d] hover:border-[#ff6d4d]'
                  }`}
                  style={{ fontFamily: 'Lato, sans-serif' }}
                >
                  <span className="mr-2">🏠</span>
                  Dashboard
                </button>
                <button
                  onClick={async () => {
                    // Check session limit before starting session
                    if (sessionLimitStatus?.limit_reached) {
                      setShowUpgradeModal(true);
                    } else {
                      const sessionStarted = await startOrResumeSession();
                      if (sessionStarted) {
                        setCurrentView('session');
                      }
                    }
                  }}
                  disabled={loading}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium border-b-2 transition-colors ${
                    currentView === 'session'
                      ? 'border-[#9ac026] text-[#545454]'
                      : 'text-[#545454] border-transparent hover:text-[#ff6d4d] hover:border-[#ff6d4d]'
                  } ${loading ? 'opacity-50 cursor-not-allowed' : ''} ${sessionLimitStatus?.limit_reached ? 'opacity-50' : ''}`}
                  style={{ fontFamily: 'Lato, sans-serif' }}
                  title={sessionLimitStatus?.limit_reached ? 'Session limit reached - upgrade to continue' : ''}
                >
                  <span className="mr-2">🎯</span>
                  {loading ? 'Loading...' : "Today's Session"}
                </button>

                {/* Upgrade - Always visible */}
                <button 
                  onClick={() => navigate('/pricing')} 
                  className="px-4 py-2 text-sm font-medium text-[#9ac026] hover:text-[#8bb024] border border-[#9ac026] rounded-lg hover:bg-[#9ac026] hover:text-white transition-all"
                  style={{ fontFamily: 'Lato, sans-serif' }}
                >
                  ⭐ Upgrade
                </button>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-sm" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                <span className="font-medium">{user.name}</span>
              </div>
              <button
                onClick={logout}
                className="text-sm px-3 py-1 rounded transition-colors"
                style={{ 
                  backgroundColor: '#f5f5f5', 
                  color: '#545454',
                  fontFamily: 'Lato, sans-serif'
                }}
                onMouseOver={(e) => {
                  e.target.style.backgroundColor = '#ff6d4d';
                  e.target.style.color = 'white';
                }}
                onMouseOut={(e) => {
                  e.target.style.backgroundColor = '#f5f5f5';
                  e.target.style.color = '#545454';
                }}
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
    // Use the new simplified dashboard
    return <SimpleDashboard />;
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
        return <SessionSystem sessionId={activeSessionId} sessionMetadata={sessionMetadata} onSessionEnd={handleSessionEnd} />;
      default:
        return renderDashboard();
    }
  };

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
      {renderNavigation()}
      {renderContent()}
      
      {/* Upgrade Modal */}
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => setShowUpgradeModal(false)} 
        completedSessions={sessionLimitStatus?.completed_sessions || 15}
      />
    </div>
  );
};

// Admin Panel Component
const AdminPanel = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('pyq-upload');
  
  // PYQ Upload states
  const [uploading, setUploading] = useState(false);

  const handlePYQUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.csv')) {
      alert('Please select a CSV file');
      return;
    }

    // Validate file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
      alert('File size must be less than 10MB');
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API}/admin/pyq/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 5 * 60 * 1000, // 5 minute timeout for large files
      });

      alert(`✅ Upload successful! 
      
📊 Summary:
• ${response.data.processed} questions processed
• ${response.data.success} questions created successfully
• ${response.data.errors} errors encountered

${response.data.success > 0 ? '🎉 Questions are now available for student sessions!' : ''}
${response.data.errors > 0 ? '⚠️ Check the logs for error details.' : ''}`);

    } catch (error) {
      console.error('Upload error:', error);
      if (error.code === 'ECONNABORTED') {
        alert('❌ Upload timeout. Please try with a smaller file or check your connection.');
      } else if (error.response?.status === 413) {
        alert('❌ File too large. Please try with a smaller CSV file.');
      } else {
        const errorMessage = error.response?.data?.detail || error.message || 'Unknown error occurred';
        alert(`❌ Upload failed: ${errorMessage}`);
      }
    } finally {
      setUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const handleExportPYQ = async () => {
    try {
      const response = await axios.get(`${API}/admin/pyq/export`, {
        responseType: 'blob', // Important for file download
        timeout: 2 * 60 * 1000, // 2 minute timeout
      });

      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Generate filename with current date
      const now = new Date();
      const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD format
      link.setAttribute('download', `twelvr_pyq_database_${dateStr}.csv`);
      
      // Append to html link element page
      document.body.appendChild(link);
      
      // Start download
      link.click();
      
      // Clean up and remove the link
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      alert('✅ PYQ database exported successfully!');
      
    } catch (error) {
      console.error('Export error:', error);
      if (error.code === 'ECONNABORTED') {
        alert('❌ Export timeout. The database might be too large. Please try again or contact support.');
      } else {
        const errorMessage = error.response?.data?.detail || error.message || 'Unknown error occurred';
        alert(`❌ Export failed: ${errorMessage}`);
      }
    }
  };

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg">
          {/* Tabs */}
          <div className="border-b">
            <nav className="flex space-x-8 px-6">
              <button
                onClick={() => setActiveTab('pyq-upload')}
                className={`py-4 text-lg font-medium transition-colors ${
                  activeTab === 'pyq-upload' 
                    ? 'border-b-2' 
                    : 'hover:text-[#ff6d4d]'
                }`}
                style={{ 
                  color: activeTab === 'pyq-upload' ? '#9ac026' : '#545454',
                  borderColor: activeTab === 'pyq-upload' ? '#9ac026' : 'transparent',
                  fontFamily: 'Lato, sans-serif'
                }}
              >
                📄 PYQ Upload
              </button>
              <button
                onClick={() => setActiveTab('questions')}
                className={`py-4 text-lg font-medium transition-colors ${
                  activeTab === 'questions' 
                    ? 'border-b-2' 
                    : 'hover:text-[#ff6d4d]'
                }`}
                style={{ 
                  color: activeTab === 'questions' ? '#9ac026' : '#545454',
                  borderColor: activeTab === 'questions' ? '#9ac026' : 'transparent',
                  fontFamily: 'Lato, sans-serif'
                }}
              >
                ❓ Questions
              </button>
              <button
                onClick={() => setActiveTab('privileges')}
                className={`py-4 text-lg font-medium transition-colors ${
                  activeTab === 'privileges' 
                    ? 'border-b-2' 
                    : 'hover:text-[#ff6d4d]'
                }`}
                style={{ 
                  color: activeTab === 'privileges' ? '#9ac026' : '#545454',
                  borderColor: activeTab === 'privileges' ? '#9ac026' : 'transparent',
                  fontFamily: 'Lato, sans-serif'
                }}
              >
                🔐 Privileges
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-8">
            {activeTab === 'pyq-upload' && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-semibold text-gray-900">Upload PYQ Data</h2>
                  <button
                    onClick={() => handleExportPYQ()}
                    className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium flex items-center"
                  >
                    📋 Export PYQ Database (CSV)
                  </button>
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

            {activeTab === 'privileges' && (
              <Privileges />
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