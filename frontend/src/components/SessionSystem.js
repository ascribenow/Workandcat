import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from './AuthProvider';

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

export const SessionSystem = ({ sessionId: propSessionId, sessionMetadata, onSessionEnd }) => {
  const { user } = useAuth();
  const [sessionId, setSessionId] = useState(propSessionId);
  const [sessionNumber, setSessionNumber] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [sessionProgress, setSessionProgress] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);
  const [answerSubmitted, setAnswerSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [imageZoomed, setImageZoomed] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (sessionId) {
      fetchNextQuestion();
    }
  }, [sessionId]);

  const handleImagePreload = async (imageUrl) => {
    if (!imageUrl) return true;
    
    return new Promise((resolve) => {
      setImageLoading(true);
      
      const img = new Image();
      
      img.onload = () => {
        setImageLoading(false);
        setImageLoadFailed(false);
        resolve(true);
      };
      
      img.onerror = async () => {
        if (retryCount < 1) {
          setRetryCount(prev => prev + 1);
          console.log(`Image load failed, retrying... (attempt ${retryCount + 2}/2)`);
          
          setTimeout(() => {
            const retryImg = new Image();
            retryImg.onload = () => {
              setImageLoading(false);
              setImageLoadFailed(false);
              resolve(true);
            };
            retryImg.onerror = () => {
              setImageLoading(false);
              setImageLoadFailed(true);
              blockQuestionFromSessions(currentQuestion?.id);
              resolve(false);
            };
            retryImg.src = imageUrl;
          }, 1000);
        } else {
          setImageLoading(false);
          setImageLoadFailed(true);
          blockQuestionFromSessions(currentQuestion?.id);
          resolve(false);
        }
      };
      
      img.src = imageUrl;
    });
  };

  const fetchSessionNumberFromDashboard = async () => {
    try {
      // Get total sessions from the dashboard API to calculate current session number
      const response = await axios.get(`${API}/dashboard/simple-taxonomy`);
      const totalSessions = response.data.total_sessions || 0;
      const currentSessionNumber = totalSessions + 1; // Current session is total + 1
      setSessionNumber(currentSessionNumber);
      console.log('Session number calculated from dashboard total:', currentSessionNumber);
    } catch (error) {
      console.error('Failed to get session number from dashboard:', error);
      // Ultimate fallback
      setSessionNumber(1);
    }
  };

  const blockQuestionFromSessions = async (questionId) => {
    try {
      // Using axios to leverage global authorization headers
      await axios.post(`${API}/sessions/report-broken-image`, {
        question_id: questionId
      });
      
      console.log(`Question ${questionId} blocked from future sessions`);
      await fetchNextQuestion();
      
    } catch (error) {
      console.error('Error blocking question:', error);
      await fetchNextQuestion();
    }
  };

  const fetchNextQuestion = async () => {
    setLoading(true);
    setError('');
    setUserAnswer('');
    setShowResult(false);
    setResult(null);
    setAnswerSubmitted(false);
    
    try {
      // Using global axios authorization header set by AuthProvider
      const response = await axios.get(`${API}/sessions/${sessionId}/next-question`);
      
      if (response.data.session_complete) {
        // Session completed, show summary
        if (onSessionEnd) {
          onSessionEnd({
            completed: true,
            questionsCompleted: response.data.questions_completed,
            totalQuestions: response.data.total_questions
          });
        }
        return;
      }
      
      if (response.data.question) {
        const question = response.data.question;
        const progress = response.data.session_progress;
        
        // Pre-load image if question has one
        if (question.has_image && question.image_url) {
          const imageLoaded = await handleImagePreload(question.image_url);
          if (!imageLoaded) {
            return; // Will retry with next question
          }
        }
        
        setCurrentQuestion(question);
        setSessionProgress(progress);
        
        // Debug: Log question structure to identify missing options issue
        console.log('Question loaded:', {
          id: question.id,
          stem: question.stem?.substring(0, 50) + '...',
          hasOptions: !!question.options,
          optionKeys: question.options ? Object.keys(question.options) : [],
          optionCount: question.options ? Object.keys(question.options).length : 0
        });
        
        // Set session number from metadata if not already set
        if (!sessionNumber) {
          if (sessionMetadata?.phase_info?.current_session) {
            // Use the correct session number from backend phase_info
            setSessionNumber(sessionMetadata.phase_info.current_session);
            console.log('Session number set from metadata:', sessionMetadata.phase_info.current_session);
          } else {
            // For resumed sessions or when metadata is not available,
            // get session count from dashboard API
            fetchSessionNumberFromDashboard();
          }
        }
        
        setImageLoading(false);
        setImageLoadFailed(false);
        setRetryCount(0);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        if (onSessionEnd) {
          onSessionEnd({ completed: true });
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
    setAnswerSubmitted(true);
    
    try {
      const response = await axios.post(`${API}/sessions/${sessionId}/submit-answer`, {
        question_id: currentQuestion.id,
        user_answer: userAnswer,
        context: 'session',
        hint_used: false
      });

      setResult(response.data);
      setShowResult(true);
      
    } catch (err) {
      setError('Failed to submit answer');
      console.error('Error submitting answer:', err);
      setAnswerSubmitted(false);
    } finally {
      setLoading(false);
    }
  };

  const handleNextQuestion = () => {
    fetchNextQuestion();
  };

  const handleOptionSelect = (option) => {
    if (!answerSubmitted) {
      setUserAnswer(option);
    }
  };

  if (loading && !currentQuestion) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your session...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-red-800 mb-2">Error</h3>
          <p className="text-red-600">{error}</p>
          <button 
            onClick={fetchNextQuestion}
            className="mt-4 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Session Progress Header */}
      {sessionProgress && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold text-blue-800">
                Session #{sessionNumber || '---'} • 12-Question Practice
              </h2>
              <div className="text-sm text-blue-600 mt-1">
                CAT Quantitative Aptitude Practice Session
              </div>
            </div>
            <div className="text-blue-600 font-medium">
              Question {sessionProgress.current_question} of {sessionProgress.total_questions}
            </div>
          </div>
          <div className="mt-2">
            <div className="w-full bg-blue-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(sessionProgress.current_question / sessionProgress.total_questions) * 100}%` }}
              ></div>
            </div>
          </div>
        </div>
      )}

      {currentQuestion && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
          {/* Question Header */}
          <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
            <div className="flex justify-between items-start">
              <div>
                <span className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-medium">
                  {currentQuestion.subcategory}
                </span>
                {currentQuestion.difficulty_band && (
                  <span className={`ml-2 inline-block px-2 py-1 rounded text-sm font-medium ${
                    currentQuestion.difficulty_band === 'Easy' ? 'bg-green-100 text-green-800' :
                    currentQuestion.difficulty_band === 'Hard' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {currentQuestion.difficulty_band}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Question Content */}
          <div className="p-6">
            {/* Image Display */}
            {currentQuestion.has_image && currentQuestion.image_url && (
              <div className="mb-6">
                {imageLoading && (
                  <div className="flex items-center justify-center h-48 bg-gray-100 rounded">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                    <span className="ml-2 text-gray-600">Loading image...</span>
                  </div>
                )}
                
                {imageLoadFailed && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                    <p className="text-red-600">Image failed to load. Getting next question...</p>
                  </div>
                )}
                
                {!imageLoading && !imageLoadFailed && (
                  <div className="relative">
                    <img
                      src={currentQuestion.image_url}
                      alt={currentQuestion.image_alt_text || "Question image"}
                      className={`max-w-full h-auto rounded cursor-pointer transition-transform ${
                        imageZoomed ? 'fixed inset-0 z-50 max-w-none max-h-none object-contain bg-black bg-opacity-90' : ''
                      }`}
                      onClick={() => setImageZoomed(!imageZoomed)}
                      style={imageZoomed ? { margin: 'auto' } : {}}
                    />
                    {imageZoomed && (
                      <button
                        onClick={() => setImageZoomed(false)}
                        className="fixed top-4 right-4 z-50 bg-white text-black px-4 py-2 rounded"
                      >
                        Close
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Question Stem */}
            <div className="prose max-w-none mb-6">
              <p className="text-lg leading-relaxed">{currentQuestion.stem}</p>
            </div>

            {/* MCQ Options */}
            {!showResult && (
              <div className="space-y-3 mb-6">
                {currentQuestion.options ? (
                  Object.entries(currentQuestion.options).map(([key, value]) => {
                    if (key === 'correct') return null;
                    return (
                      <button
                        key={key}
                        onClick={() => handleOptionSelect(value)}
                        disabled={answerSubmitted}
                        className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                          userAnswer === value
                            ? 'border-blue-500 bg-blue-50 text-blue-800'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        } ${answerSubmitted ? 'cursor-not-allowed opacity-75' : 'cursor-pointer'}`}
                      >
                        <span className="font-medium text-sm text-gray-500 mr-3">{key.toUpperCase()})</span>
                        <span>{value}</span>
                      </button>
                    );
                  })
                ) : (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                    <p className="text-gray-600">Loading answer options...</p>
                    <p className="text-xs text-gray-400 mt-1">If this persists, please refresh the page</p>
                  </div>
                )}
              </div>
            )}

            {/* Submit Answer Button */}
            {!showResult && (
              <button
                onClick={submitAnswer}
                disabled={!userAnswer || loading || answerSubmitted || !currentQuestion.options}
                className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Submitting...' : 
                 !currentQuestion.options ? 'Loading options...' :
                 'Submit Answer'}
              </button>
            )}

            {/* Answer Result and Solution */}
            {showResult && result && (
              <div className="mt-6">
                {/* Answer Status */}
                <div className={`p-4 rounded-lg mb-4 ${
                  result.correct ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-3 ${
                      result.correct ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
                    }`}>
                      {result.correct ? '✓' : '✗'}
                    </div>
                    <div>
                      <h3 className={`font-semibold ${
                        result.correct ? 'text-green-800' : 'text-red-800'
                      }`}>
                        {result.status === 'correct' ? 'Correct!' : 'Incorrect'}
                      </h3>
                      <p className={`text-sm ${
                        result.correct ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {result.message}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Answer Comparison */}
                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Your Answer:</p>
                      <p className="text-lg">{result.user_answer}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Correct Answer:</p>
                      <p className="text-lg font-semibold text-green-600">{result.correct_answer}</p>
                    </div>
                  </div>
                </div>

                {/* Solution Feedback */}
                {result.solution_feedback && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                    <h4 className="font-semibold text-blue-800 mb-3">Solution</h4>
                    
                    {/* Solution Approach */}
                    {result.solution_feedback.solution_approach && (
                      <div className="mb-4">
                        <h5 className="font-medium text-blue-700 mb-2">Approach:</h5>
                        <p className="text-blue-600 leading-relaxed">
                          {result.solution_feedback.solution_approach}
                        </p>
                      </div>
                    )}

                    {/* Detailed Solution */}
                    {result.solution_feedback.detailed_solution && (
                      <div className="mb-4">
                        <h5 className="font-medium text-blue-700 mb-2">Detailed Solution:</h5>
                        <div className="text-blue-600 leading-relaxed whitespace-pre-line">
                          {result.solution_feedback.detailed_solution}
                        </div>
                      </div>
                    )}

                    {/* Explanation */}
                    {result.solution_feedback.explanation && (
                      <div>
                        <h5 className="font-medium text-blue-700 mb-2">Explanation:</h5>
                        <p className="text-blue-600 leading-relaxed">
                          {result.solution_feedback.explanation}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Question Metadata */}
                {result.question_metadata && (
                  <div className="bg-gray-50 p-3 rounded text-sm text-gray-600 mb-4">
                    <span className="font-medium">Category:</span> {result.question_metadata.subcategory} 
                    {result.question_metadata.difficulty_band && (
                      <>
                        <span className="mx-2">•</span>
                        <span className="font-medium">Difficulty:</span> {result.question_metadata.difficulty_band}
                      </>
                    )}
                    {result.question_metadata.type_of_question && (
                      <>
                        <span className="mx-2">•</span>
                        <span className="font-medium">Type:</span> {result.question_metadata.type_of_question}
                      </>
                    )}
                  </div>
                )}

                {/* Next Question Button */}
                <button
                  onClick={handleNextQuestion}
                  className="w-full bg-green-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-green-700 transition-colors"
                >
                  {sessionProgress && sessionProgress.current_question >= sessionProgress.total_questions 
                    ? 'Complete Session' 
                    : 'Next Question'
                  }
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};