import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth, API } from './AuthProvider';

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
  
  // Doubt conversation states
  const [showDoubtModal, setShowDoubtModal] = useState(false);
  const [doubtMessage, setDoubtMessage] = useState('');
  const [doubtHistory, setDoubtHistory] = useState([]);
  const [doubtLoading, setDoubtLoading] = useState(false);
  const [messageCount, setMessageCount] = useState(0);
  const [remainingMessages, setRemainingMessages] = useState(10);
  const [conversationLocked, setConversationLocked] = useState(false);

  // Handle case where no session ID is provided
  useEffect(() => {
    if (!propSessionId && !sessionId) {
      setError('No active session found. Please start a new session.');
      setLoading(false);
    } else if (propSessionId && propSessionId !== sessionId) {
      setSessionId(propSessionId);
    }
  }, [propSessionId, sessionId]);

  useEffect(() => {
    if (sessionId) {
      fetchNextQuestion();
      
      // Set session number immediately if not available from metadata
      if (!sessionNumber) {
        if (sessionMetadata?.phase_info?.current_session) {
          setSessionNumber(sessionMetadata.phase_info.current_session);
          console.log('Session number set from useEffect metadata:', sessionMetadata.phase_info.current_session);
        } else {
          console.log('Session metadata not available, fetching from dashboard...');
          fetchSessionNumberFromDashboard();
        }
      }
    }
  }, [sessionId, sessionMetadata]);

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
      const totalSessionsStarted = response.data.total_sessions_started || 0;
      const currentSessionNumber = totalSessionsStarted; // Current session is the count of all sessions started
      setSessionNumber(currentSessionNumber);
      console.log('Session number calculated from total sessions started:', currentSessionNumber);
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
    // Check if we have a valid session ID
    if (!sessionId) {
      setError('No active session found. Please start a new session from the dashboard.');
      setLoading(false);
      return;
    }

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
        
        // Session number is now handled in useEffect to avoid race conditions
        
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

    if (!sessionId) {
      setError('No active session found. Cannot submit answer.');
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

  // Doubt conversation functions - Twelvr New Version
  const handleAskDoubt = async () => {
    if (!doubtMessage.trim() || conversationLocked) return;

    // Open modal and load conversation history first
    setShowDoubtModal(true);
    await loadDoubtHistory();

    // Then send the doubt
    setDoubtLoading(true);
    try {
      const response = await axios.post(`${API}/doubts/ask`, {
        question_id: currentQuestion.id,
        session_id: sessionId,
        message: doubtMessage.trim()
      });

      if (response.data.success) {
        // Update local state
        setMessageCount(response.data.message_count);
        setRemainingMessages(response.data.remaining_messages);
        setConversationLocked(response.data.is_locked);
        setDoubtMessage('');
        
        // Reload conversation history to show new message
        await loadDoubtHistory();
      } else {
        alert(response.data.error || 'Failed to send doubt');
      }
    } catch (error) {
      console.error('Error sending doubt:', error);
      alert('Failed to send your doubt. Please try again.');
    } finally {
      setDoubtLoading(false);
    }
  };

  const loadDoubtHistory = async () => {
    if (!currentQuestion?.id) return;
    
    try {
      const response = await axios.get(`${API}/doubts/${currentQuestion.id}/history`);
      setDoubtHistory(response.data.messages || []);
      setMessageCount(response.data.message_count || 0);
      setRemainingMessages(response.data.remaining_messages || 10);
      setConversationLocked(response.data.is_locked || false);
    } catch (error) {
      console.error('Error loading doubt history:', error);
      setDoubtHistory([]);
    }
  };

  const closeDoubtModal = () => {
    setShowDoubtModal(false);
  };

  if (!sessionId && !loading) {
    return (
      <div className="max-w-4xl mx-auto p-6" style={{ fontFamily: 'Manrope, sans-serif' }}>
        <div className="border border-gray-200 rounded-lg p-6 text-center" style={{ backgroundColor: '#fff5f3' }}>
          <h3 className="text-lg font-semibold mb-4" style={{ color: '#545454' }}>Consistency, Compounded.</h3>
          <p className="text-base mb-6" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            Twelvr is compiling your perfect session.
          </p>
        </div>
      </div>
    );
  }

  if (loading && !currentQuestion) {
    return (
      <div className="flex items-center justify-center min-h-screen" style={{ fontFamily: 'Manrope, sans-serif' }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 mx-auto" style={{ borderColor: '#9ac026' }}></div>
          <p className="mt-4" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>Loading your session...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6" style={{ fontFamily: 'Manrope, sans-serif' }}>
        <div className="border rounded-lg p-6" style={{ backgroundColor: '#fff5f3', borderColor: '#ff6d4d' }}>
          <h3 className="text-lg font-semibold mb-2" style={{ color: '#ff6d4d' }}>Session Error</h3>
          <p className="mb-4" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>{error}</p>
          <button 
            onClick={fetchNextQuestion}
            className="px-4 py-2 text-white rounded transition-colors"
            style={{ backgroundColor: '#ff6d4d', fontFamily: 'Lato, sans-serif' }}
            onMouseOver={(e) => e.target.style.backgroundColor = '#e55a3c'}
            onMouseOut={(e) => e.target.style.backgroundColor = '#ff6d4d'}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6" style={{ fontFamily: 'Manrope, sans-serif' }}>
      {/* Session Progress Header */}
      {sessionProgress && (
        <div className="border rounded-lg p-4 mb-6" style={{ backgroundColor: '#f7fdf0', borderColor: '#9ac026' }}>
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>
                Session #{sessionNumber || '---'} • 12-Question Practice
              </h2>
              <div className="text-sm mt-1" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                CAT Quantitative Aptitude Practice Session
              </div>
            </div>
            <div className="font-medium" style={{ color: '#9ac026', fontFamily: 'Lato, sans-serif' }}>
              Question {sessionProgress.current_question} of {sessionProgress.total_questions}
            </div>
          </div>
          <div className="mt-2">
            <div className="w-full rounded-full h-2" style={{ backgroundColor: '#e8f5e8' }}>
              <div 
                className="h-2 rounded-full transition-all duration-300"
                style={{ 
                  width: `${(sessionProgress.current_question / sessionProgress.total_questions) * 100}%`,
                  backgroundColor: '#9ac026'
                }}
              ></div>
            </div>
          </div>
        </div>
      )}

      {currentQuestion && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
          {/* Question Header */}
          <div className="px-6 py-4 border-b border-gray-200" style={{ backgroundColor: '#fafafa' }}>
            <div className="flex justify-between items-start">
              <div>
                <span className="inline-block px-2 py-1 rounded text-sm font-medium" style={{ 
                  backgroundColor: '#f7fdf0', 
                  color: '#9ac026',
                  fontFamily: 'Lato, sans-serif'
                }}>
                  {currentQuestion.subcategory}
                </span>
                {currentQuestion.difficulty_band && (
                  <span className="ml-2 inline-block px-2 py-1 rounded text-sm font-medium" style={{
                    backgroundColor: 
                      currentQuestion.difficulty_band === 'Easy' ? '#f7fdf0' :
                      currentQuestion.difficulty_band === 'Hard' ? '#fff5f3' :
                      '#fff5f3',
                    color:
                      currentQuestion.difficulty_band === 'Easy' ? '#9ac026' :
                      currentQuestion.difficulty_band === 'Hard' ? '#ff6d4d' :
                      '#ff6d4d',
                    fontFamily: 'Lato, sans-serif'
                  }}>
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
                  <div className="flex items-center justify-center h-48 rounded" style={{ backgroundColor: '#fafafa' }}>
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderBottomColor: '#9ac026' }}></div>
                    <span className="ml-2" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>Loading image...</span>
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
              <p className="text-lg leading-relaxed" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                {currentQuestion.stem}
              </p>
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
                        className="w-full text-left p-4 rounded-lg border-2 transition-all"
                        style={{
                          borderColor: userAnswer === value ? '#9ac026' : '#e5e7eb',
                          backgroundColor: userAnswer === value ? '#f7fdf0' : '#ffffff',
                          color: '#545454',
                          fontFamily: 'Lato, sans-serif'
                        }}
                        onMouseOver={(e) => {
                          if (userAnswer !== value && !answerSubmitted) {
                            e.target.style.borderColor = '#ff6d4d';
                            e.target.style.backgroundColor = '#fff5f3';
                          }
                        }}
                        onMouseOut={(e) => {
                          if (userAnswer !== value) {
                            e.target.style.borderColor = '#e5e7eb';
                            e.target.style.backgroundColor = '#ffffff';
                          }
                        }}
                        disabled={answerSubmitted}
                      >
                        <span className="font-medium text-sm mr-3" style={{ color: '#9ac026', fontFamily: 'Lato, sans-serif' }}>
                          {key.toUpperCase()})
                        </span>
                        <span style={{ fontFamily: 'Lato, sans-serif' }}>{value}</span>
                      </button>
                    );
                  })
                ) : (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 mx-auto mb-2" style={{ borderBottomColor: '#9ac026' }}></div>
                    <p style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>Loading answer options...</p>
                    <p className="text-xs mt-1" style={{ color: '#999999', fontFamily: 'Lato, sans-serif' }}>If this persists, please refresh the page</p>
                  </div>
                )}
              </div>
            )}

            {/* Submit Answer Button */}
            {!showResult && (
              <button
                onClick={submitAnswer}
                disabled={!userAnswer || loading || answerSubmitted || !currentQuestion.options}
                className="w-full py-3 px-6 rounded-lg font-semibold transition-colors disabled:cursor-not-allowed"
                style={{
                  backgroundColor: (!userAnswer || loading || answerSubmitted || !currentQuestion.options) ? '#cccccc' : '#9ac026',
                  color: 'white',
                  fontFamily: 'Lato, sans-serif'
                }}
                onMouseOver={(e) => {
                  if (!e.target.disabled) {
                    e.target.style.backgroundColor = '#8bb024';
                  }
                }}
                onMouseOut={(e) => {
                  if (!e.target.disabled) {
                    e.target.style.backgroundColor = '#9ac026';
                  }
                }}
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
                <div className="p-4 rounded-lg mb-4 border" style={{
                  backgroundColor: result.correct ? '#f7fdf0' : '#fff5f3',
                  borderColor: result.correct ? '#9ac026' : '#ff6d4d'
                }}>
                  <div className="flex items-center">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center mr-3 text-white" style={{
                      backgroundColor: result.correct ? '#9ac026' : '#ff6d4d'
                    }}>
                      {result.correct ? '✓' : '✗'}
                    </div>
                    <div>
                      <h3 className="font-semibold" style={{
                        color: result.correct ? '#9ac026' : '#ff6d4d',
                        fontFamily: 'Manrope, sans-serif'
                      }}>
                        {result.status === 'correct' ? 'Correct!' : 'Incorrect'}
                      </h3>
                      <p className="text-sm" style={{
                        color: result.correct ? '#9ac026' : '#ff6d4d',
                        fontFamily: 'Lato, sans-serif'
                      }}>
                        {result.message}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Answer Comparison */}
                <div className="p-4 rounded-lg mb-4" style={{ backgroundColor: '#fafafa' }}>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium mb-1" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>Your Answer:</p>
                      <p className="text-lg" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>{result.user_answer}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium mb-1" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>Correct Answer:</p>
                      <p className="text-lg font-semibold" style={{ color: '#9ac026', fontFamily: 'Lato, sans-serif' }}>{result.correct_answer}</p>
                    </div>
                  </div>
                </div>

                {/* Solution Feedback */}
                {result.solution_feedback && (
                  <div className="border rounded-lg p-4 mb-4" style={{ backgroundColor: '#f7fdf0', borderColor: '#9ac026' }}>
                    <h4 className="font-semibold mb-3" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>Solution</h4>
                    
                    {/* Solution Approach */}
                    {result.solution_feedback.solution_approach && (
                      <div className="mb-6">
                        <h5 className="font-semibold mb-3 text-lg" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>📋 Approach:</h5>
                        <div className="bg-white p-4 rounded-lg border" style={{ borderColor: '#e8f5e8' }}>
                          <div className="leading-relaxed text-base" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                            {result.solution_feedback.solution_approach}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Detailed Solution */}
                    {result.solution_feedback.detailed_solution && (
                      <div className="mb-6">
                        <h5 className="font-semibold mb-3 text-lg" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>📖 Detailed Solution:</h5>
                        <div className="bg-white p-6 rounded-lg border" style={{ borderColor: '#e8f5e8' }}>
                          <div className="leading-relaxed whitespace-pre-line text-base" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                            {result.solution_feedback.detailed_solution}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Principle to remember */}
                    {result.solution_feedback.principle_to_remember && (
                      <div>
                        <h5 className="font-semibold mb-3 text-lg" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>💡 Principle to remember:</h5>
                        <div className="bg-white p-4 rounded-lg border" style={{ borderColor: '#e8f5e8' }}>
                          <div className="leading-relaxed" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                            {result.solution_feedback.principle_to_remember}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Ask Any Doubt Section - Twelvr New Version */}
                {result.solution_feedback && currentQuestion && (
                  <div className="border border-gray-200 rounded-lg p-4 mb-4" style={{ backgroundColor: '#f7fdf0' }}>
                    <h4 className="font-semibold mb-3" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>💬 Have a doubt about this solution?</h4>
                    <div className="space-y-3">
                      <textarea
                        value={doubtMessage}
                        onChange={(e) => setDoubtMessage(e.target.value)}
                        placeholder="Ask your doubt about this question or solution..."
                        className="w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 resize-none"
                        style={{ 
                          borderColor: '#9ac026',
                          fontFamily: 'Lato, sans-serif'
                        }}
                        onFocus={(e) => {
                          e.target.style.ringColor = '#9ac026';
                          e.target.style.borderColor = '#9ac026';
                        }}
                        rows="3"
                        maxLength="500"
                        disabled={conversationLocked}
                      />
                      <div className="flex justify-between items-center">
                        <div className="text-sm" style={{ color: '#9ac026', fontFamily: 'Lato, sans-serif' }}>
                          {conversationLocked ? (
                            <span style={{ color: '#ff6d4d' }} className="font-medium">❌ Conversation limit reached (10/10)</span>
                          ) : (
                            <span>💬 Messages used: {messageCount}/10</span>
                          )}
                        </div>
                        <button
                          onClick={() => handleAskDoubt()}
                          disabled={!doubtMessage.trim() || doubtLoading || conversationLocked}
                          className="px-4 py-2 text-white rounded-md focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          style={{ 
                            backgroundColor: '#9ac026',
                            fontFamily: 'Lato, sans-serif'
                          }}
                          onMouseOver={(e) => {
                            if (!e.target.disabled) {
                              e.target.style.backgroundColor = '#8bb024';
                            }
                          }}
                          onMouseOut={(e) => {
                            if (!e.target.disabled) {
                              e.target.style.backgroundColor = '#9ac026';
                            }
                          }}
                        >
                          {doubtLoading ? "Asking..." : "🤔 Ask Twelvr"}
                        </button>
                      </div>
                    </div>
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
                  className="w-full py-3 px-6 rounded-lg font-semibold transition-colors text-white"
                  style={{ 
                    backgroundColor: '#9ac026',
                    fontFamily: 'Lato, sans-serif'
                  }}
                  onMouseOver={(e) => e.target.style.backgroundColor = '#8bb024'}
                  onMouseOut={(e) => e.target.style.backgroundColor = '#9ac026'}
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

      {/* Doubt Conversation Modal - ChatGPT Style */}
      {showDoubtModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex justify-between items-center p-4 border-b" style={{ borderColor: '#f5f5f5' }}>
              <h3 className="text-lg font-semibold" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>💬 Chat with Twelvr</h3>
              <div className="flex items-center space-x-4">
                <span className="text-sm" style={{ color: '#9ac026', fontFamily: 'Lato, sans-serif' }}>
                  {conversationLocked ? (
                    <span style={{ color: '#ff6d4d' }} className="font-medium">❌ Limit reached (10/10)</span>
                  ) : (
                    <span>💬 {messageCount}/10 messages used</span>
                  )}
                </span>
                <button
                  onClick={closeDoubtModal}
                  className="focus:outline-none transition-colors"
                  style={{ color: '#545454' }}
                  onMouseOver={(e) => e.target.style.color = '#ff6d4d'}
                  onMouseOut={(e) => e.target.style.color = '#545454'}
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>
            </div>

            {/* Conversation History */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ backgroundColor: '#fafafa' }}>
              {doubtHistory.length === 0 ? (
                <div className="text-center py-8" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  <p>👋 Hi! I'm Twelvr, your friendly tutor.</p>
                  <p className="mt-2">Ask me anything about this question or solution!</p>
                </div>
              ) : (
                doubtHistory.map((message, index) => (
                  <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-lg p-3 ${
                      message.role === 'user'
                        ? 'text-white'
                        : 'bg-white border border-gray-200 shadow-sm'
                    }`}
                    style={message.role === 'user' ? { backgroundColor: '#9ac026' } : {}}
                    >
                      {message.role === 'assistant' && (
                        <div className="text-sm font-medium mb-1" style={{ color: '#9ac026', fontFamily: 'Lato, sans-serif' }}>🤖 Twelvr says:</div>
                      )}
                      <div className={`whitespace-pre-wrap`} style={{ 
                        color: message.role === 'user' ? 'white' : '#545454',
                        fontFamily: 'Lato, sans-serif' 
                      }}>
                        {message.message}
                      </div>
                      <div className={`text-xs mt-2`} style={{
                        color: message.role === 'user' ? 'rgba(255,255,255,0.8)' : '#999999',
                        fontFamily: 'Lato, sans-serif'
                      }}>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}
              {doubtLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 shadow-sm rounded-lg p-3 max-w-[80%]">
                    <div className="text-sm font-medium mb-1" style={{ color: '#9ac026', fontFamily: 'Lato, sans-serif' }}>🤖 Twelvr says:</div>
                    <div className="flex items-center space-x-2">
                      <div className="animate-pulse flex space-x-1">
                        <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#9ac026' }}></div>
                        <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#9ac026', animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#9ac026', animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-sm" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Message Input */}
            {!conversationLocked && (
              <div className="border-t p-4 bg-white" style={{ borderColor: '#f5f5f5' }}>
                <div className="flex space-x-3">
                  <textarea
                    value={doubtMessage}
                    onChange={(e) => setDoubtMessage(e.target.value)}
                    placeholder="Type your doubt or question here..."
                    className="flex-1 px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 resize-none"
                    style={{ 
                      borderColor: '#9ac026',
                      fontFamily: 'Lato, sans-serif',
                      focusRingColor: '#9ac026'
                    }}
                    rows="2"
                    maxLength="500"
                    disabled={doubtLoading}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleAskDoubt();
                      }
                    }}
                  />
                  <button
                    onClick={handleAskDoubt}
                    disabled={!doubtMessage.trim() || doubtLoading}
                    className="px-4 py-2 text-white rounded-md focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed self-end transition-colors"
                    style={{ 
                      backgroundColor: '#9ac026',
                      fontFamily: 'Lato, sans-serif'
                    }}
                    onMouseOver={(e) => {
                      if (!e.target.disabled) {
                        e.target.style.backgroundColor = '#8bb024';
                      }
                    }}
                    onMouseOut={(e) => {
                      if (!e.target.disabled) {
                        e.target.style.backgroundColor = '#9ac026';
                      }
                    }}
                  >
                    {doubtLoading ? "..." : "Send"}
                  </button>
                </div>
                <div className="text-xs mt-2" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
                  Press Enter to send, Shift+Enter for new line
                </div>
              </div>
            )}

            {conversationLocked && (
              <div className="border-t p-4" style={{ borderColor: '#f5f5f5', backgroundColor: '#fff5f3' }}>
                <div className="text-center" style={{ color: '#ff6d4d' }}>
                  <p className="font-medium">❌ Conversation Limit Reached</p>
                  <p className="text-sm mt-1" style={{ fontFamily: 'Lato, sans-serif' }}>You have used all 10 messages for this question.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};