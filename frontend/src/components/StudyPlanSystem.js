import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth, API } from './AuthProvider';

export const StudyPlanSystem = () => {
  const { user } = useAuth();
  const [studyPlan, setStudyPlan] = useState(null);
  const [todaysPlan, setTodaysPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [activeSession, setActiveSession] = useState(null);

  useEffect(() => {
    fetchStudyPlan();
    fetchTodaysPlan();
  }, []);

  const fetchStudyPlan = async () => {
    try {
      const response = await axios.get(`${API}/study-plan`);
      if (response.data.study_plans && response.data.study_plans.length > 0) {
        setStudyPlan(response.data.study_plans[0]);
      }
    } catch (err) {
      console.error('Error fetching study plan:', err);
    }
  };

  const fetchTodaysPlan = async () => {
    try {
      const response = await axios.get(`${API}/study-plan/today`);
      setTodaysPlan(response.data);
    } catch (err) {
      console.error('Error fetching today\'s plan:', err);
    } finally {
      setLoading(false);
    }
  };

  const generateStudyPlan = async (trackType = 'beginner') => {
    setGenerating(true);
    setError('');
    try {
      const response = await axios.post(`${API}/study-plan`, {
        target_track: trackType,
        target_days: 90,
        daily_minutes: 60
      });
      
      setStudyPlan(response.data);
      await fetchTodaysPlan(); // Refresh today's plan
      alert('Your personalized 90-day study plan has been created!');
    } catch (err) {
      setError('Failed to generate study plan. Please try again.');
      console.error('Study plan generation error:', err);
    } finally {
      setGenerating(false);
    }
  };

  const startSession = async (targetMinutes = 30) => {
    try {
      const response = await axios.post(`${API}/session/start`, {
        target_minutes: targetMinutes
      });
      
      setActiveSession(response.data);
      return response.data.session_id;
    } catch (err) {
      console.error('Error starting session:', err);
      alert('Failed to start study session');
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your study plan...</p>
        </div>
      </div>
    );
  }

  // No study plan exists
  if (!studyPlan) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-8">
            <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
              <svg className="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">Create Your 90-Day Study Plan</h1>
            <p className="text-lg text-gray-600 mb-8">
              Get a personalized study plan based on your target preparation level and available time
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div className="bg-green-50 p-6 rounded-lg text-center">
              <h3 className="text-xl font-semibold text-green-900 mb-3">🟢 Beginner Track</h3>
              <ul className="text-sm text-green-800 space-y-2 mb-4">
                <li>• Foundation building approach</li>
                <li>• 45-60 minutes per session</li>
                <li>• Concept clarity focus</li>
                <li>• Gradual difficulty progression</li>
              </ul>
              <button
                onClick={() => generateStudyPlan('beginner')}
                disabled={generating}
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white px-4 py-2 rounded-lg font-medium"
              >
                {generating ? 'Creating...' : 'Choose Beginner'}
              </button>
            </div>

            <div className="bg-yellow-50 p-6 rounded-lg text-center">
              <h3 className="text-xl font-semibold text-yellow-900 mb-3">🟡 Intermediate Track</h3>
              <ul className="text-sm text-yellow-800 space-y-2 mb-4">
                <li>• Balanced approach</li>
                <li>• 60-75 minutes per session</li>
                <li>• Speed & accuracy focus</li>
                <li>• Mixed difficulty levels</li>
              </ul>
              <button
                onClick={() => generateStudyPlan('intermediate')}
                disabled={generating}
                className="w-full bg-yellow-600 hover:bg-yellow-700 disabled:bg-yellow-400 text-white px-4 py-2 rounded-lg font-medium"
              >
                {generating ? 'Creating...' : 'Choose Intermediate'}
              </button>
            </div>

            <div className="bg-red-50 p-6 rounded-lg text-center">
              <h3 className="text-xl font-semibold text-red-900 mb-3">🔴 Advanced Track</h3>
              <ul className="text-sm text-red-800 space-y-2 mb-4">
                <li>• Intensive preparation</li>
                <li>• 75-90 minutes per session</li>
                <li>• High difficulty focus</li>
                <li>• Time optimization</li>
              </ul>
              <button
                onClick={() => generateStudyPlan('good')}
                disabled={generating}
                className="w-full bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white px-4 py-2 rounded-lg font-medium"
              >
                {generating ? 'Creating...' : 'Choose Advanced'}
              </button>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          <div className="text-center">
            <p className="text-sm text-gray-500">
              Tip: Choose your track based on your current preparation level and available study time
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Study plan exists - show dashboard
  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      {/* Plan Overview */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Your 90-Day Study Plan</h1>
            <p className="text-gray-600">Track: {studyPlan.target_track?.toUpperCase() || 'CUSTOM'} | Status: {studyPlan.status?.toUpperCase() || 'ACTIVE'}</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">{studyPlan.progress_percentage || 0}%</div>
            <div className="text-sm text-gray-500">Complete</div>
          </div>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
          <div 
            className="bg-blue-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${studyPlan.progress_percentage || 0}%` }}
          ></div>
        </div>

        <div className="grid md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-xl font-bold text-green-600">{studyPlan.days_completed || 0}</div>
            <div className="text-sm text-gray-600">Days Completed</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-blue-600">{studyPlan.total_days || 90}</div>
            <div className="text-sm text-gray-600">Total Days</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-purple-600">{studyPlan.questions_solved || 0}</div>
            <div className="text-sm text-gray-600">Questions Solved</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-yellow-600">{studyPlan.current_streak || 0}</div>
            <div className="text-sm text-gray-600">Day Streak</div>
          </div>
        </div>
      </div>

      {/* Today's Plan */}
      {todaysPlan && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-gray-900">Today's Study Plan</h2>
            <div className="text-sm text-gray-500">
              {new Date().toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </div>
          </div>

          {todaysPlan.plan_units && todaysPlan.plan_units.length > 0 ? (
            <div className="space-y-4">
              {todaysPlan.plan_units.map((unit, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900">{unit.topic_name}</h3>
                      <p className="text-sm text-gray-600">{unit.subcategory}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-blue-600">
                        {unit.target_minutes} min | {unit.target_questions} questions
                      </div>
                      <div className="text-xs text-gray-500">
                        Difficulty: {unit.difficulty_focus}
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-600">
                      Progress: {unit.completed_questions || 0}/{unit.target_questions}
                    </div>
                    
                    {!activeSession ? (
                      <button
                        onClick={() => startSession(unit.target_minutes)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                      >
                        Start Session
                      </button>
                    ) : (
                      <div className="text-sm text-green-600 font-medium">
                        Session Active
                      </div>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-3">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-green-500 h-2 rounded-full transition-all duration-300"
                        style={{ 
                          width: `${Math.min(100, ((unit.completed_questions || 0) / unit.target_questions) * 100)}%` 
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Quick Actions */}
              <div className="flex gap-4 pt-4 border-t">
                <button
                  onClick={() => startSession(30)}
                  disabled={!!activeSession}
                  className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white py-3 rounded-lg font-medium"
                >
                  {activeSession ? 'Session Active' : 'Quick 30min Session'}
                </button>
                <button
                  onClick={() => startSession(60)}
                  disabled={!!activeSession}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white py-3 rounded-lg font-medium"
                >
                  {activeSession ? 'Session Active' : 'Full 60min Session'}
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="text-gray-500 mb-4">No study units scheduled for today</div>
              <button
                onClick={() => startSession(30)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium"
              >
                Start Free Practice Session
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};