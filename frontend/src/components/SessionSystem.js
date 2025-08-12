import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from './AuthProvider';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const SessionSystem = ({ sessionId: propSessionId, onSessionEnd }) => {
  const { user } = useAuth();
  const [sessionId, setSessionId] = useState(propSessionId);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);
  const [sessionStats, setSessionStats] = useState({
    questions_attempted: 0,
    accuracy: 0,
    total_time: 0
  });
  const [timeLeft, setTimeLeft] = useState(0);
  const [questionStartTime, setQuestionStartTime] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [imageZoomed, setImageZoomed] = useState(false);
  const [imageError, setImageError] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (sessionId) {
      fetchNextQuestion();
      // Remove fetchSessionStats() call since the endpoint doesn't exist
    }
  }, [sessionId]);

  useEffect(() => {
    if (questionStartTime && !showResult) {
      timerRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - questionStartTime) / 1000);
        const remaining = Math.max(0, (currentQuestion?.expected_time_sec || 120) - elapsed);
        setTimeLeft(remaining);
        
        if (remaining === 0) {
          handleTimeUp();
        }
      }, 1000);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [questionStartTime, showResult, currentQuestion]);

  const fetchNextQuestion = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API}/session/${sessionId}/next-question`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}` }
      });
      setCurrentQuestion(response.data.question);
      setQuestionStartTime(Date.now());
      setUserAnswer('');
      setShowResult(false);
      setResult(null);
      
      if (response.data.question?.expected_time_sec) {
        setTimeLeft(response.data.question.expected_time_sec);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        // Session ended
        if (onSessionEnd) {
          onSessionEnd();
        }
      } else {
        setError('Failed to load next question');
        console.error('Error fetching next question:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!userAnswer.trim()) {
      alert('Please select an answer');
      return;
    }

    setLoading(true);
    try {
      const timeSpent = questionStartTime ? Math.floor((Date.now() - questionStartTime) / 1000) : 0;
      
      const response = await axios.post(`${API}/session/${sessionId}/submit-answer`, {
        question_id: currentQuestion.id,
        user_answer: userAnswer,
        time_sec: timeSpent,
        context: 'daily',
        hint_used: false
      }, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}` }
      });

      setResult(response.data);
      setShowResult(true);
      
      // Update local session stats
      setSessionStats(prev => ({
        questions_attempted: prev.questions_attempted + 1,
        accuracy: response.data.correct ? 
          Math.round(((prev.accuracy * prev.questions_attempted) + 100) / (prev.questions_attempted + 1)) :
          Math.round((prev.accuracy * prev.questions_attempted) / (prev.questions_attempted + 1)),
        total_time: prev.total_time + (timeSpent / 60) // Convert to minutes
      }));
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    } catch (err) {
      setError('Failed to submit answer');
      console.error('Answer submission error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTimeUp = () => {
    if (!showResult && currentQuestion) {
      submitAnswer();
    }
  };

  const nextQuestion = () => {
    fetchNextQuestion();
  };

  const endSession = () => {
    if (onSessionEnd) {
      onSessionEnd();
    }
  };

  if (loading && !currentQuestion) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your practice session...</p>
        </div>
      </div>
    );
  }

  if (error && !currentQuestion) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="text-red-600 mb-4">{error}</div>
          <button
            onClick={() => fetchNextQuestion()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Session Complete!</h2>
          <p className="text-gray-600 mb-6">Great job on completing your practice session.</p>
          
          {sessionStats && (
            <div className="grid md:grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{sessionStats.questions_attempted || 0}</div>
                <div className="text-sm text-blue-600">Questions Attempted</div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{sessionStats.accuracy || 0}%</div>
                <div className="text-sm text-green-600">Accuracy</div>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{sessionStats.total_time || 0}min</div>
                <div className="text-sm text-purple-600">Time Spent</div>
              </div>
            </div>
          )}
          
          <button
            onClick={endSession}
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg text-lg font-semibold"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="bg-white rounded-lg shadow-lg p-8">
        {/* Session Header */}
        <div className="flex justify-between items-center mb-6 pb-4 border-b">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-900">Practice Session</h1>
            {sessionStats.questions_attempted !== undefined && (
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                Question #{sessionStats.questions_attempted + 1}
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-4">
            {/* Timer */}
            <div className={`text-lg font-mono ${timeLeft < 30 ? 'text-red-600' : 'text-gray-700'}`}>
              {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
            </div>
            
            <button
              onClick={endSession}
              className="text-sm bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded transition-colors"
            >
              End Session
            </button>
          </div>
        </div>

        {/* Question */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
              {currentQuestion.category}
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
              {currentQuestion.subcategory}
            </span>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              currentQuestion.difficulty_band === 'Easy' ? 'bg-green-100 text-green-800' :
              currentQuestion.difficulty_band === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-800'
            }`}>
              {currentQuestion.difficulty_band}
            </span>
          </div>

          <h2 className="text-xl font-medium text-gray-900 mb-6 leading-relaxed">
            {currentQuestion.stem}
          </h2>

          {/* Question Image */}
          {currentQuestion.has_image && currentQuestion.image_url && (
            <div className="mb-6">
              <div className="bg-gray-50 rounded-lg p-4 inline-block max-w-full">
                <img 
                  src={currentQuestion.image_url} 
                  alt={currentQuestion.image_alt_text || "Question diagram"}
                  className="max-w-full h-auto max-h-96 rounded-lg shadow-sm cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => setImageZoomed(true)}
                />
                {currentQuestion.image_alt_text && (
                  <p className="text-xs text-gray-500 mt-2 text-center italic">
                    {currentQuestion.image_alt_text}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Image Zoom Modal */}
          {imageZoomed && (
            <div 
              className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
              onClick={() => setImageZoomed(false)}
            >
              <div className="relative max-w-full max-h-full">
                <img 
                  src={currentQuestion.image_url} 
                  alt={currentQuestion.image_alt_text || "Question diagram (enlarged)"}
                  className="max-w-full max-h-full object-contain"
                />
                <button
                  onClick={() => setImageZoomed(false)}
                  className="absolute top-4 right-4 bg-black bg-opacity-50 text-white rounded-full w-10 h-10 flex items-center justify-center hover:bg-opacity-75 transition-opacity"
                >
                  ×
                </button>
                {currentQuestion.image_alt_text && (
                  <div className="absolute bottom-4 left-4 right-4 bg-black bg-opacity-50 text-white text-sm p-2 rounded">
                    {currentQuestion.image_alt_text}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* MCQ Options */}
          {currentQuestion.options && (
            <div className="space-y-3 mb-6">
              {Object.entries(currentQuestion.options).filter(([key]) => key !== 'correct').map(([key, value]) => (
                <button
                  key={key}
                  onClick={() => setUserAnswer(key)}
                  disabled={showResult}
                  className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                    showResult 
                      ? (key === currentQuestion.options.correct 
                          ? 'border-green-500 bg-green-50' 
                          : (key === userAnswer 
                              ? 'border-red-500 bg-red-50' 
                              : 'border-gray-200 bg-gray-50'))
                      : (userAnswer === key
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50')
                  } ${showResult ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <div className="flex items-start">
                    <span className={`font-semibold mr-3 ${
                      showResult 
                        ? (key === currentQuestion.options.correct ? 'text-green-600' : 
                           (key === userAnswer ? 'text-red-600' : 'text-gray-600'))
                        : 'text-blue-600'
                    }`}>
                      {key}.
                    </span>
                    <span className="text-gray-900">{value}</span>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Text Input for NAT questions */}
          {!currentQuestion.options && (
            <div className="mb-6">
              <input
                type="text"
                placeholder="Enter your answer"
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                disabled={showResult}
                className="w-full border-2 border-gray-200 rounded-lg px-4 py-3 text-lg focus:border-blue-500 focus:outline-none disabled:bg-gray-50"
              />
            </div>
          )}
        </div>

        {/* Results */}
        {showResult && result && (
          <div className={`p-6 rounded-lg mb-6 ${result.correct ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            <div className="flex items-start gap-4">
              <div className={`p-2 rounded-full ${result.correct ? 'bg-green-200' : 'bg-red-200'}`}>
                {result.correct ? (
                  <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
              </div>
              
              <div className="flex-1">
                <div className={`font-semibold text-lg ${result.correct ? 'text-green-800' : 'text-red-800'}`}>
                  {result.correct ? 'Correct!' : 'Incorrect'}
                </div>
                
                {result.solution_approach && (
                  <div className="mt-2">
                    <strong>Approach:</strong> {result.solution_approach}
                  </div>
                )}
                
                {result.detailed_solution && (
                  <div className="mt-2">
                    <strong>Solution:</strong> {result.detailed_solution}
                  </div>
                )}
                
                {result.next_retry_in_days && (
                  <div className="mt-2 text-sm text-gray-600">
                    This question will appear again in {result.next_retry_in_days} days for review
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between items-center pt-6 border-t">
          <div className="text-sm text-gray-500">
            {sessionStats.questions_attempted !== undefined && sessionStats.accuracy !== undefined && (
              <span>Session: {sessionStats.questions_attempted} questions • {sessionStats.accuracy}% accuracy</span>
            )}
          </div>
          
          <div className="flex gap-3">
            {!showResult ? (
              <button
                onClick={submitAnswer}
                disabled={!userAnswer.trim() || loading}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              >
                {loading ? 'Submitting...' : 'Submit Answer'}
              </button>
            ) : (
              <button
                onClick={nextQuestion}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              >
                Next Question
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};