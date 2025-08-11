import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './AuthProvider';
import { DiagnosticSystem } from './DiagnosticSystem';
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
    if (currentView === 'dashboard') {
      fetchDashboardData();
    }
  }, [currentView]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Fetch mastery dashboard
      const masteryResponse = await axios.get(`${API}/dashboard/mastery`);
      setMasteryData(masteryResponse.data);

      // Fetch progress dashboard
      const progressResponse = await axios.get(`${API}/dashboard/progress`);
      setProgressData(progressResponse.data);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const startQuickSession = async (minutes = 30) => {
    try {
      const response = await axios.post(`${API}/session/start`, {
        target_minutes: minutes
      });
      setActiveSessionId(response.data.session_id);
      setCurrentView('session');
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

  const renderNavigation = () => (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex space-x-8">
            {[
              { key: 'dashboard', label: 'Dashboard', icon: '🏠' },
              { key: 'diagnostic', label: 'Diagnostic', icon: '🎯' },
              { key: 'study-plan', label: 'Study Plan', icon: '📅' },
              { key: 'practice', label: 'Practice', icon: '📝' },
              ...(isAdmin() ? [{ key: 'admin', label: 'Admin', icon: '⚙️' }] : [])
            ].map((item) => (
              <button
                key={item.key}
                onClick={() => setCurrentView(item.key)}
                className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                  currentView === item.key 
                    ? "text-blue-600 border-b-2 border-blue-500" 
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <span className="mr-2">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-700">
              <span className="font-medium">{user.name}</span>
              {isAdmin() && (
                <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Admin
                </span>
              )}
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

  const renderDashboard = () => {
    if (loading) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading dashboard...</p>
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
              Continue your CAT preparation journey. Track your progress and stay consistent.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="grid md:grid-cols-4 gap-4 mb-8">
            <button
              onClick={() => setCurrentView('diagnostic')}
              className="bg-blue-600 hover:bg-blue-700 text-white p-6 rounded-lg text-center transition-colors"
            >
              <div className="text-2xl mb-2">🎯</div>
              <div className="font-semibold">Take Diagnostic</div>
              <div className="text-sm opacity-80">Assess your level</div>
            </button>
            
            <button
              onClick={() => startQuickSession(30)}
              className="bg-green-600 hover:bg-green-700 text-white p-6 rounded-lg text-center transition-colors"
            >
              <div className="text-2xl mb-2">⚡</div>
              <div className="font-semibold">Quick Practice</div>
              <div className="text-sm opacity-80">30 minutes</div>
            </button>
            
            <button
              onClick={() => setCurrentView('study-plan')}
              className="bg-purple-600 hover:bg-purple-700 text-white p-6 rounded-lg text-center transition-colors"
            >
              <div className="text-2xl mb-2">📅</div>
              <div className="font-semibold">Study Plan</div>
              <div className="text-sm opacity-80">90-day journey</div>
            </button>
            
            <button
              onClick={() => startQuickSession(60)}
              className="bg-orange-600 hover:bg-orange-700 text-white p-6 rounded-lg text-center transition-colors"
            >
              <div className="text-2xl mb-2">🔥</div>
              <div className="font-semibold">Deep Practice</div>
              <div className="text-sm opacity-80">60 minutes</div>
            </button>
          </div>

          {/* Progress Overview */}
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
                <div className="text-3xl font-bold text-yellow-600">{progressData.avg_session_time || 0}min</div>
                <div className="text-sm text-gray-600">Avg Session</div>
                <div className="text-xs text-gray-500 mt-1">
                  Last: {progressData.last_session_date ? formatDate(progressData.last_session_date) : 'Never'}
                </div>
              </div>
            </div>
          )}

          {/* Mastery Progress */}
          {masteryData && masteryData.mastery_by_topic && masteryData.mastery_by_topic.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">Mastery Progress by Topic</h3>
              <div className="space-y-4">
                {masteryData.mastery_by_topic.map((topic) => (
                  <div key={topic.topic_name} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium text-gray-900">{topic.topic_name}</span>
                        <span className={`text-sm font-semibold ${
                          topic.mastery_percentage > 80 ? 'text-green-600' :
                          topic.mastery_percentage > 60 ? 'text-yellow-600' :
                          'text-red-600'
                        }`}>
                          {Math.round(topic.mastery_percentage)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                          className={`h-3 rounded-full transition-all duration-300 ${
                            topic.mastery_percentage > 80 ? 'bg-green-500' :
                            topic.mastery_percentage > 60 ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${Math.max(5, topic.mastery_percentage)}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>{topic.questions_attempted} questions attempted</span>
                        <span>Last practiced: {topic.last_attempt_date ? formatDate(topic.last_attempt_date) : 'Never'}</span>
                      </div>
                    </div>
                  </div>
                ))}
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
    switch (currentView) {
      case 'diagnostic':
        return <DiagnosticSystem />;
      case 'study-plan':
        return <StudyPlanSystem />;
      case 'session':
        return <SessionSystem sessionId={activeSessionId} onSessionEnd={handleSessionEnd} />;
      case 'admin':
        if (isAdmin()) {
          return <AdminPanel />;
        }
        return renderDashboard();
      case 'practice':
        return <PracticeSystem />;
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

// Placeholder components that will use existing implementations
const AdminPanel = () => {
  return <div className="p-8 text-center">Admin Panel - Will integrate with existing AdminPanel component</div>;
};

const PracticeSystem = () => {
  return <div className="p-8 text-center">Practice System - Will integrate with existing Practice component</div>;
};