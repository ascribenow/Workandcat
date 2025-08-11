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
    const checkDiagnosticAndLoadDashboard = async () => {
      if (currentView === 'dashboard') {
        // Check if user has completed diagnostic
        const diagnosticResponse = await axios.get(`${API}/user/diagnostic-status`);
        const hasCompletedDiagnostic = diagnosticResponse.data.has_completed;
        
        if (hasCompletedDiagnostic) {
          // User has completed diagnostic, show regular dashboard
          fetchDashboardData();
        } else {
          // New user, show diagnostic first
          setCurrentView('diagnostic');
        }
      }
    };
    
    checkDiagnosticAndLoadDashboard();
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
          <div className="grid md:grid-cols-2 gap-4 mb-8">
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

// Admin Panel Component
const AdminPanel = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('pyq-upload');
  const [questions, setQuestions] = useState([]);
  const [showQuestionForm, setShowQuestionForm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [questionForm, setQuestionForm] = useState({
    stem: "",
    answer: "",
    solution_approach: "",
    detailed_solution: "",
    hint_category: "",
    hint_subcategory: "",
    tags: [],
    source: ""
  });

  useEffect(() => {
    if (activeTab === 'questions') {
      fetchQuestions();
    }
  }, [activeTab]);

  const fetchQuestions = async () => {
    try {
      const response = await axios.get(`${API}/questions`);
      setQuestions(response.data.questions || []);
    } catch (err) {
      console.error('Error fetching questions:', err);
    }
  };

  const handlePYQUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('year', '2024');

    try {
      const response = await axios.post(`${API}/admin/upload-pyq`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert('PYQ uploaded successfully!');
      event.target.value = ''; // Reset file input
    } catch (error) {
      alert('Error uploading PYQ: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setUploading(false);
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
        answer: "",
        solution_approach: "",
        detailed_solution: "",
        hint_category: "",
        hint_subcategory: "",
        tags: [],
        source: ""
      });
      fetchQuestions();
    } catch (error) {
      alert('Error creating question: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="border-b px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
          <p className="text-sm text-gray-600">Welcome, {user.name} (Admin)</p>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <nav className="flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('pyq-upload')}
              className={`py-4 text-sm font-medium ${
                activeTab === 'pyq-upload' 
                  ? 'text-blue-600 border-b-2 border-blue-500' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              📄 PYQ Upload
            </button>
            <button
              onClick={() => setActiveTab('questions')}
              className={`py-4 text-sm font-medium ${
                activeTab === 'questions' 
                  ? 'text-blue-600 border-b-2 border-blue-500' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              ❓ Question Management
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'pyq-upload' && (
            <div className="max-w-2xl">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload PYQ Files</h2>
              <p className="text-gray-600 mb-6">
                Upload previous year question papers in Word document format (.docx, .doc)
              </p>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <div className="mb-4">
                  <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                    <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
                <div className="mb-4">
                  <label htmlFor="pyq-upload" className="cursor-pointer">
                    <span className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium">
                      {uploading ? 'Uploading...' : 'Select PYQ File'}
                    </span>
                    <input
                      id="pyq-upload"
                      type="file"
                      accept=".docx,.doc"
                      onChange={handlePYQUpload}
                      disabled={uploading}
                      className="hidden"
                    />
                  </label>
                </div>
                <p className="text-sm text-gray-500">
                  Supported formats: .docx, .doc
                </p>
              </div>
            </div>
          )}

          {activeTab === 'questions' && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Question Management</h2>
                <button
                  onClick={() => setShowQuestionForm(!showQuestionForm)}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium"
                >
                  {showQuestionForm ? 'Cancel' : 'Add Question'}
                </button>
              </div>

              {showQuestionForm && (
                <div className="bg-gray-50 p-6 rounded-lg mb-6">
                  <form onSubmit={handleQuestionSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Question Stem</label>
                      <textarea
                        value={questionForm.stem}
                        onChange={(e) => setQuestionForm({...questionForm, stem: e.target.value})}
                        className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                        rows="4"
                        required
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Answer</label>
                        <input
                          type="text"
                          value={questionForm.answer}
                          onChange={(e) => setQuestionForm({...questionForm, answer: e.target.value})}
                          className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Source</label>
                        <input
                          type="text"
                          value={questionForm.source}
                          onChange={(e) => setQuestionForm({...questionForm, source: e.target.value})}
                          className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                          placeholder="e.g., CAT 2023, Mock Test"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">Solution Approach</label>
                      <textarea
                        value={questionForm.solution_approach}
                        onChange={(e) => setQuestionForm({...questionForm, solution_approach: e.target.value})}
                        className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                        rows="2"
                      />
                    </div>

                    <button
                      type="submit"
                      className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium"
                    >
                      Create Question
                    </button>
                  </form>
                </div>
              )}

              {/* Questions List */}
              <div className="bg-white border rounded-lg">
                <div className="px-4 py-3 border-b bg-gray-50">
                  <h3 className="font-medium text-gray-900">
                    Questions ({questions.length})
                  </h3>
                </div>
                <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                  {questions.map((question, index) => (
                    <div key={question.id} className="px-4 py-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-sm text-gray-900 mb-2">{question.stem}</p>
                          <div className="flex items-center space-x-2">
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              {question.subcategory}
                            </span>
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              {question.difficulty_band || 'Unrated'}
                            </span>
                            <span className="text-xs text-gray-500">
                              Answer: {question.answer}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const PracticeSystem = () => {
  return <div className="p-8 text-center">Practice System - Will integrate with existing Practice component</div>;
};