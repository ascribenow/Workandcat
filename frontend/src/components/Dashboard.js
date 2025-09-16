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
import SubscriptionManagement from './SubscriptionManagement';

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
  
  // Enrich Checker states
  const [enriching, setEnriching] = useState(false);
  const [enrichResults, setEnrichResults] = useState(null);

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
      console.log('Dashboard: User adaptive enabled:', user?.adaptive_enabled);
      console.log('Dashboard: Current sessionLimitStatus:', sessionLimitStatus);
      
      // First check session limit status
      if (!sessionLimitStatus) {
        console.log('Dashboard: Session limit status not loaded, fetching...');
        const limitResponse = await axios.get(`${API}/user/session-limit-status`);
        console.log('Dashboard: Session limit response:', limitResponse.data);
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
      
      // V2 HARDENING: Check for uncompleted adaptive sessions first
      if (user?.adaptive_enabled) {
        try {
          console.log('Dashboard: Checking for uncompleted adaptive sessions...');
          
          // Check for incomplete sessions using the new progress tracking system
          const incompleteSessionResponse = await axios.get(`${API}/session-progress/current/${user.id}`);
          
          if (incompleteSessionResponse.data.has_current_session) {
            const sessionData = incompleteSessionResponse.data;
            console.log(`Dashboard: Found incomplete session: ${sessionData.session_id} at Q${sessionData.current_question_index + 1}/${sessionData.total_questions}`);
            
            // Show resume session UI
            setActiveSessionId(sessionData.session_id);
            setSessionMetadata({
              resume_session: true,
              session_id: sessionData.session_id,
              current_question_index: sessionData.current_question_index,
              total_questions: sessionData.total_questions,
              last_question_id: sessionData.last_question_id,
              phase_info: {
                current_session: sessionData.current_question_index + 1
              }
            });
            setCurrentView('session');
            return true;
          }
          
          // Fallback: Check localStorage for any active session (legacy)
          const storedSessionId = localStorage.getItem('currentSessionId') || localStorage.getItem('nextSessionId');
          
          if (storedSessionId) {
            console.log('Dashboard: Found stored session ID, checking if pack exists:', storedSessionId);
            
            // V2 HARDENING: ONLY call GET /pack (never re-plan)
            const packResponse = await axios.get(`${API}/adapt/pack`, {
              params: {
                user_id: user.id,
                session_id: storedSessionId
              }
            });
            
            if (packResponse.status === 200 && packResponse.data.pack) {
              console.log('Dashboard: Uncompleted adaptive session found - showing RESUME option');
              
              // Show resume session UI instead of auto-starting
              setActiveSessionId(storedSessionId);
              setSessionMetadata({
                resume_session: true,
                session_id: storedSessionId,
                pack_available: true,
                questions_count: packResponse.data.pack.length
              });
              setCurrentView('session');
              return true;
            }
          }
          
        } catch (adaptiveCheckError) {
          console.log('Dashboard: No uncompleted adaptive session or pack not found, proceeding with new session');
          // Clear any stale session data
          localStorage.removeItem('currentSessionId');
          localStorage.removeItem('nextSessionId');
        }
      }
      
      // Check for existing legacy active session
      const sessionStatusResponse = await axios.get(`${API}/sessions/current-status`);
      console.log('Dashboard: Session status response:', sessionStatusResponse.data);
      
      if (sessionStatusResponse.data.active_session) {
        console.log('Dashboard: Active legacy session found, resuming...');
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
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-sm" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                <span className="font-medium">{user.name}</span>
              </div>
              
              {/* Upgrade - Moved next to and left of Logout */}
              <button 
                onClick={() => navigate('/pricing')} 
                className="px-4 py-2 text-sm font-medium text-[#9ac026] hover:text-[#8bb024] border border-[#9ac026] rounded-lg hover:bg-[#9ac026] hover:text-white transition-all"
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                ⭐ Upgrade
              </button>
              
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
  
  // Enrich Checker states
  const [enriching, setEnriching] = useState(false);
  const [enrichResults, setEnrichResults] = useState(null);

  // Referral Tracker states
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [searchCode, setSearchCode] = useState('');
  const [referralData, setReferralData] = useState(null);
  const [loadingReferrals, setLoadingReferrals] = useState(false);
  const [exportingReferrals, setExportingReferrals] = useState(false);

  // Referral Functions
  const loadFilteredReferrals = async () => {
    setLoadingReferrals(true);
    try {
      const token = localStorage.getItem('cat_prep_token');
      let url = `${API}/admin/referral-export?format=json`;
      
      // Add date filters if provided
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      if (params.toString()) {
        url += '&' + params.toString();
      }
      
      const response = await axios.get(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setReferralData(response.data.referral_data || []);
    } catch (error) {
      console.error('Error loading referral data:', error);
      alert('❌ Failed to load referral data');
    } finally {
      setLoadingReferrals(false);
    }
  };

  const searchReferralCode = async () => {
    if (!searchCode || searchCode.length !== 6) {
      alert('Please enter a valid 6-character referral code');
      return;
    }
    
    setLoadingReferrals(true);
    try {
      const token = localStorage.getItem('cat_prep_token');
      const response = await axios.get(`${API}/admin/referral-stats/${searchCode}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Convert the stats response to table format
      if (response.data.recent_usage) {
        const tableData = response.data.recent_usage.map(usage => ({
          date: usage.created_at,
          referral_code: searchCode,
          referrer_name: response.data.owner?.full_name || '',
          referrer_email: response.data.owner?.email || '',
          used_by_email: usage.email,
          usage_id: usage.user_id || 'N/A',
          subscription_type: usage.subscription_type,
          cashback_due: "₹500.00"
        }));
        setReferralData(tableData);
      } else {
        setReferralData([]);
      }
    } catch (error) {
      console.error('Error searching referral code:', error);
      alert('❌ Referral code not found or error occurred');
    } finally {
      setLoadingReferrals(false);
    }
  };

  const exportReferralData = async (format = 'csv') => {
    setExportingReferrals(true);
    try {
      const token = localStorage.getItem('cat_prep_token');
      const response = await axios.get(`${API}/admin/referral-export?format=${format}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: format === 'csv' ? 'blob' : 'json'
      });

      if (format === 'csv') {
        // Handle CSV download
        const blob = new Blob([response.data], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `referral_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        alert('✅ Referral data exported successfully!');
      } else {
        // Handle JSON export
        const jsonData = JSON.stringify(response.data, null, 2);
        const blob = new Blob([jsonData], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `referral_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        alert('✅ Referral data exported successfully!');
      }
    } catch (error) {
      console.error('Error exporting referral data:', error);
      alert('❌ Failed to export referral data');
    } finally {
      setExportingReferrals(false);
    }
  };

  // Load referral data when tab is selected
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'referral-tracker') {
      // Set default date range (last 30 days)
      const today = new Date();
      const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
      
      setEndDate(today.toISOString().split('T')[0]);
      setStartDate(thirtyDaysAgo.toISOString().split('T')[0]);
      
      // Load initial data
      loadFilteredReferrals();
    }
  };

  const handleCSVUpload = async (event) => {
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

      const response = await axios.post(`${API}/admin/questions/csv-upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 5 * 60 * 1000, // 5 minute timeout for large files
      });

      alert(`✅ CSV Upload Successful!
      
📊 Processing Summary:
• ${response.data.total_processed} questions processed
• ${response.data.successful_uploads} questions created successfully  
• ${response.data.failed_uploads} failed uploads
• ${response.data.duplicate_questions} duplicate questions skipped

${response.data.successful_uploads > 0 ? '🎉 New questions are now available for student practice!' : ''}
${response.data.failed_uploads > 0 ? '⚠️ Some questions failed to upload. Check question format and try again.' : ''}
${response.data.duplicate_questions > 0 ? 'ℹ️ Duplicate questions were automatically skipped.' : ''}`);

    } catch (error) {
      console.error('CSV upload error:', error);
      if (error.code === 'ECONNABORTED') {
        alert('❌ Upload timeout. Please try with a smaller file or check your connection.');
      } else if (error.response?.status === 413) {
        alert('❌ File too large. Please try with a smaller CSV file.');
      } else {
        const errorMessage = error.response?.data?.detail || error.message || 'Unknown error occurred';
        alert(`❌ CSV Upload failed: ${errorMessage}`);
      }
    } finally {
      setUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  // REMOVED: handleCheckQuestionQuality and handleReEnrichQuestions functions
  // These have been removed as per the new Question Upload & Enrichment Workflow requirements

  const handleExportQuestions = async () => {
    try {
      const response = await axios.get(`${API}/admin/questions/export`, {
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
      link.setAttribute('download', `twelvr_questions_database_${dateStr}.csv`);
      
      // Append to html link element page
      document.body.appendChild(link);
      
      // Start download
      link.click();
      
      // Clean up and remove the link
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      alert('✅ Questions database exported successfully!');
      
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

  const handleRecalculateFrequency = async () => {
    if (!window.confirm('🔢 Start PYQ Frequency Recalculation?\n\nThis will:\n• Recalculate pyq_frequency_score for ALL quality-verified questions\n• Use corrected logic (Easy ≤1.5 gets 0.5, Hard >1.5 uses LLM comparison)\n• Process in background with batch processing\n• Send email notification when complete\n• Estimated time: 15-30 minutes for ~370 questions\n\nProceed?')) {
      return;
    }

    try {
      setEnriching(true);
      setEnrichResults(null);

      const response = await axios.post(`${API}/admin/recalculate-frequency-background`);

      if (response.data.success) {
        const jobId = response.data.job_id;
        const adminEmail = response.data.admin_email;
        
        alert(`✅ PYQ Frequency Recalculation Job Started!

🚀 JOB DETAILS:
• Job ID: ${jobId}
• Processing: All quality-verified questions
• Method: Corrected difficulty filtering logic
• Background processing with batch commits
• No browser timeouts or blocking

📧 EMAIL NOTIFICATION:
You will receive a detailed email at ${adminEmail} when complete.

⏱️ ESTIMATED TIME: ${response.data.estimated_time}

🎯 BENEFITS:
• Accurate frequency scores using corrected logic
• Easy questions (≤1.5) get 0.5 immediately
• Hard questions (>1.5) use LLM comparison with category-matched PYQs
• Batch processing with progress tracking

You can continue using the dashboard while the job runs!`);
      }
    } catch (error) {
      console.error('Background Frequency Recalculation error:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error occurred';
      alert(`❌ Failed to start frequency recalculation: ${errorMessage}`);
    } finally {
      setEnriching(false);
    }
  };

  const handleEnrichPYQQuestions = async () => {
    if (!window.confirm('🔍 Start Background Enrichment for PYQ Questions?\n\nThis will:\n• Start enrichment job in background (no waiting/timeouts)\n• Process questions in batches with automatic retries\n• Send email notification when complete\n• Use intelligent GPT-4o/GPT-4o-mini switching\n\nProceed?')) {
      return;
    }

    try {
      setEnriching(true);
      setEnrichResults(null);

      const response = await axios.post(`${API}/admin/enrich-checker/pyq-questions-background`, {
        total_questions: null // Process all questions
      });

      if (response.data.success) {
        const jobId = response.data.job_id;
        const adminEmail = response.data.admin_email;
        
        alert(`✅ PYQ Questions Enrichment Job Started!

🚀 JOB DETAILS:
• Job ID: ${jobId}
• Processing: Background (no timeouts)
• Batch Size: 10 questions per batch
• Retries: Automatic for failed batches
• Model: Intelligent GPT-4o/GPT-4o-mini switching

📧 EMAIL NOTIFICATION:
You will receive a detailed email at ${adminEmail} when the enrichment is complete.

⏱️ ESTIMATED TIME: 5-15 minutes
(depending on question count and LLM processing)

🎯 BENEFITS:
• No browser timeouts
• Automatic retries
• 100% quality standards maintained
• Background processing with progress tracking

You can continue using the dashboard while the job runs in background!`);
      }
    } catch (error) {
      console.error('Background PYQ Questions Enrichment error:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error occurred';
      alert(`❌ Failed to start background enrichment: ${errorMessage}`);
    } finally {
      setEnriching(false);
    }
  };

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
    <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Lato, sans-serif' }}>
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="bg-white rounded-2xl shadow-lg">
          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              <button
                onClick={() => handleTabChange('pyq-upload')}
                className={`py-4 text-lg font-medium transition-colors ${
                  activeTab === 'pyq-upload' 
                    ? 'text-[#9ac026] border-b-2 border-[#9ac026]' 
                    : 'text-[#545454] hover:text-[#9ac026]'
                }`}
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                📄 PYQ Upload
              </button>
              <button
                onClick={() => handleTabChange('questions')}
                className={`py-4 text-lg font-medium transition-colors ${
                  activeTab === 'questions' 
                    ? 'text-[#9ac026] border-b-2 border-[#9ac026]' 
                    : 'text-[#545454] hover:text-[#9ac026]'
                }`}
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                ❓ Questions
              </button>
              <button
                onClick={() => handleTabChange('privileges')}
                className={`py-4 text-lg font-medium transition-colors ${
                  activeTab === 'privileges' 
                    ? 'text-[#9ac026] border-b-2 border-[#9ac026]' 
                    : 'text-[#545454] hover:text-[#9ac026]'
                }`}
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                🔐 Privileges
              </button>
              <button
                onClick={() => handleTabChange('referral-tracker')}
                className={`py-4 text-lg font-medium transition-colors ${
                  activeTab === 'referral-tracker' 
                    ? 'text-[#9ac026] border-b-2 border-[#9ac026]' 
                    : 'text-[#545454] hover:text-[#9ac026]'
                }`}
                style={{ fontFamily: 'Lato, sans-serif' }}
              >
                🎯 Referral Tracker
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-8">
            {activeTab === 'pyq-upload' && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-semibold text-gray-900" style={{ fontFamily: 'Lato, sans-serif' }}>Upload PYQ Data</h2>
                  <div className="flex space-x-3">
                    <button
                      onClick={() => handleExportPYQ()}
                      className="bg-[#9ac026] hover:bg-[#8bb024] text-white px-6 py-3 rounded-lg font-medium flex items-center"
                      style={{ fontFamily: 'Lato, sans-serif' }}
                    >
                      📋 Export PYQ Database (CSV)
                    </button>
                    <button
                      onClick={() => handleEnrichPYQQuestions()}
                      className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-medium flex items-center"
                      style={{ fontFamily: 'Lato, sans-serif' }}
                      disabled={enriching}
                    >
                      {enriching ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Enriching...
                        </>
                      ) : (
                        '🔍 Enrich PYQ'
                      )}
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
                        <li><strong>image_url</strong> - Google Drive URL (Optional)</li>
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
                          <p className="mb-3">Just provide question text - our AI automatically generates:</p>
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
                      <span className="bg-[#9ac026] hover:bg-[#8bb024] text-white px-8 py-4 rounded-lg text-lg font-medium inline-block shadow-lg hover:shadow-xl transition-all" style={{ fontFamily: 'Lato, sans-serif' }}>
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
                    <p className="text-sm text-[#545454] mt-3" style={{ fontFamily: 'Lato, sans-serif' }}>
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
                  <h2 className="text-2xl font-semibold text-gray-900" style={{ fontFamily: 'Lato, sans-serif' }}>Question Management</h2>
                  <div className="flex space-x-3">
                    <button
                      onClick={() => handleExportQuestions()}
                      className="bg-[#9ac026] hover:bg-[#8bb024] text-white px-6 py-3 rounded-lg font-medium flex items-center"
                      style={{ fontFamily: 'Lato, sans-serif' }}
                    >
                      📊 Export All Questions (CSV)
                    </button>
                    <button
                      onClick={() => handleRecalculateFrequency()}
                      className="bg-orange-600 hover:bg-orange-700 text-white px-6 py-3 rounded-lg font-medium flex items-center"
                      style={{ fontFamily: 'Lato, sans-serif' }}
                      disabled={enriching}
                    >
                      {enriching ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Calculating...
                        </>
                      ) : (
                        '🔢 Recalculate Frequency'
                      )}
                    </button>
                  </div>
                </div>

                {/* CSV Upload Only - Single Question Upload Removed */}
                <div className="mb-8">
                  <div className="max-w-2xl mx-auto">
                    <div className="border-2 border-gray-200 rounded-lg p-8 text-center">
                      <div className="mb-6">
                        <svg className="w-16 h-16 mx-auto text-[#9ac026] mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <h3 className="text-2xl font-semibold text-gray-900 mb-2" style={{ fontFamily: 'Lato, sans-serif' }}>CSV Questions Upload</h3>
                        <p className="text-[#545454] mb-4" style={{ fontFamily: 'Lato, sans-serif' }}>
                          Upload multiple questions from CSV file. Single question upload has been removed for streamlined workflow.
                        </p>
                      </div>
                      
                      <div className="mb-6">
                        <input
                          type="file"
                          accept=".csv"
                          onChange={handleCSVUpload}
                          className="hidden"
                          id="csv-upload"
                          disabled={uploading}
                        />
                        <label
                          htmlFor="csv-upload"
                          className={`cursor-pointer inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg text-white transition-colors ${
                            uploading 
                              ? 'bg-gray-400 cursor-not-allowed' 
                              : 'bg-[#9ac026] hover:bg-[#8bb024]'
                          }`}
                          style={{ fontFamily: 'Lato, sans-serif' }}
                        >
                          {uploading ? (
                            <>
                              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Processing...
                            </>
                          ) : (
                            <>
                              📄 Choose CSV File
                            </>
                          )}
                        </label>
                      </div>

                      <div className="text-sm text-[#545454] space-y-2" style={{ fontFamily: 'Lato, sans-serif' }}>
                        <p>📋 <strong>CSV Format Required:</strong> stem, answer, solution_approach, detailed_solution, principle_to_remember, snap_read, image_url, mcq_options</p>
                        <p>📝 <strong>Field Descriptions:</strong> stem=question text, answer=canonical answer, solution_approach=approach, detailed_solution=full solution, principle_to_remember=key principle, snap_read=quick overview, image_url=image link, mcq_options=JSON options</p>
                        <p>📊 <strong>File Size Limit:</strong> 10MB maximum</p>
                        <p>🎯 <strong>Processing:</strong> Questions are immediately enriched with LLM-generated fields (category, subcategory, type, difficulty, right_answer)</p>
                        <p>🔒 <strong>Admin Fields Protected:</strong> Your uploaded content (stem, answer, solution_approach, detailed_solution, principle_to_remember, snap_read, image_url, mcq_options) is stored directly and not modified</p>
                        <p>✅ <strong>Quality Control:</strong> Questions are activated only if admin answer matches LLM-generated answer</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Upload Progress and Results */}
                {uploading && (
                  <div className="mb-8">
                    <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                      <div className="flex items-center mb-4">
                        <svg className="animate-spin h-6 w-6 text-[#9ac026] mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <h3 className="text-lg font-semibold text-green-900" style={{ fontFamily: 'Lato, sans-serif' }}>Processing CSV Upload...</h3>
                      </div>
                      <p className="text-green-800" style={{ fontFamily: 'Lato, sans-serif' }}>
                        Please wait while we process your questions. This may take several minutes for large files.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'privileges' && (
              <Privileges />
            )}

            {activeTab === 'referral-tracker' && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-semibold text-gray-900" style={{ fontFamily: 'Lato, sans-serif' }}>
                    Referral Tracker
                  </h2>
                  <button
                    onClick={() => exportReferralData('csv')}
                    disabled={exportingReferrals}
                    className="bg-[#9ac026] hover:bg-[#8bb024] text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50"
                    style={{ fontFamily: 'Lato, sans-serif' }}
                  >
                    {exportingReferrals ? 'Exporting...' : 'Export CSV'}
                  </button>
                </div>

                {/* Date Filter */}
                <div className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
                  <div className="flex items-center space-x-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                      <input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        className="border border-gray-300 rounded px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                      <input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="border border-gray-300 rounded px-3 py-2 text-sm"
                      />
                    </div>
                    <div className="pt-6">
                      <button
                        onClick={loadFilteredReferrals}
                        disabled={loadingReferrals}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
                      >
                        {loadingReferrals ? 'Loading...' : 'Filter'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Referral Code Search */}
                <div className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
                  <div className="flex items-center space-x-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Search Referral Code</label>
                      <div className="flex">
                        <input
                          type="text"
                          value={searchCode}
                          onChange={(e) => setSearchCode(e.target.value.toUpperCase())}
                          placeholder="Enter referral code (e.g., XTJC41)"
                          className="flex-1 border border-gray-300 rounded-l px-3 py-2 text-sm"
                          maxLength={6}
                        />
                        <button
                          onClick={searchReferralCode}
                          disabled={loadingReferrals}
                          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-r text-sm disabled:opacity-50"
                        >
                          Search
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Results Table */}
                {referralData && referralData.length > 0 && (
                  <div className="bg-white rounded-lg border border-gray-200">
                    <div className="p-4 border-b border-gray-200">
                      <h3 className="text-lg font-medium text-gray-900">
                        Referral Usage ({referralData.length} records)
                      </h3>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="min-w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Referral Code</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Referrer</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Used By (Email)</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Used By (User ID)</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cashback Due</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {referralData.map((record, index) => (
                            <tr key={index} className="hover:bg-gray-50">
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {record.date}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-medium">
                                  {record.referral_code}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <div className="text-gray-900 font-medium">{record.referrer_name}</div>
                                <div className="text-gray-500">{record.referrer_email}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {record.used_by_email}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {record.usage_id}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {record.subscription_type}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-600">
                                {record.cashback_due}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {loadingReferrals && (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#9ac026] mx-auto mb-2"></div>
                    <p className="text-gray-600">Loading...</p>
                  </div>
                )}

                {!loadingReferrals && (!referralData || referralData.length === 0) && (
                  <div className="text-center py-8">
                    <p className="text-gray-500">No referral data found. Use the filters above or search for a specific referral code.</p>
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