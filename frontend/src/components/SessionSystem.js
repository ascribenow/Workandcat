import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth, API } from './AuthProvider';
import MathRenderer from './MathRenderer';
import { ADAPTIVE_GLOBAL } from '../config';
import { useRouteTrace, setupGlobalErrorMonitoring } from '../utils/sessionMonitoring';
import SessionErrorBoundary from './SessionErrorBoundary';
import { recordPackWrite } from '../utils/packHistoryRecorder';

export const SessionSystem = ({ sessionId: propSessionId, sessionMetadata, onSessionEnd }) => {
  const { user } = useAuth();
  
  // DIAGNOSTIC: Generate unique request ID for this session instance
  const diagnosticRequestId = useRef(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  
  // DIAGNOSTIC: Route monitoring with session tag
  useRouteTrace('SESSION');
  
  // DIAGNOSTIC: Setup global error monitoring
  useEffect(() => {
    setupGlobalErrorMonitoring(diagnosticRequestId.current);
    console.log(`[DIAGNOSTIC] Session instance started with request_id: ${diagnosticRequestId.current}`);
    
    return () => {
      console.log(`[DIAGNOSTIC] Session instance cleanup for request_id: ${diagnosticRequestId.current}`);
    };
  }, []);
  
  // Feature flag check
  const adaptiveEnabled = ADAPTIVE_GLOBAL && !!user?.adaptive_enabled;
  
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

  // Adaptive session state  
  const [currentPack, setCurrentPack] = useState([]);
  
  // CRITICAL DEBUG: Monitor pack changes
  useEffect(() => {
    const requestId = diagnosticRequestId.current;
    console.log(`[PACK_MONITOR] ${requestId}: Pack changed - length: ${currentPack.length}`, {
      packLength: currentPack.length,
      packFirstItem: currentPack[0]?.item_id || 'none',
      timestamp: new Date().toISOString()
    });
    
    if (currentPack.length === 0) {
      console.warn(`[PACK_MONITOR] ${requestId}: CRITICAL - Pack is empty! This will cause session completion.`);
      console.trace('Pack emptied stack trace');
    }
  }, [currentPack]);
  
  // SURGICAL FIX: Protected pack setter to prevent accidental clearing
  const setCurrentPackSafe = (newPack) => {
    const requestId = diagnosticRequestId.current;
    
    // MICRO-INSTRUMENTATION: Record all pack writes
    recordPackWrite(newPack, `setCurrentPackSafe-${requestId}`);
    
    if (!newPack || newPack.length === 0) {
      console.error(`[PACK_MONITOR] ${requestId}: BLOCKED attempt to set empty pack!`, {
        newPack,
        currentPackLength: currentPack.length,
        stackTrace: new Error().stack
      });
      // Don't allow pack to be set to empty unless explicitly clearing
      return;
    }
    
    console.log(`[PACK_MONITOR] ${requestId}: Setting pack safely - ${newPack.length} items`);
    setCurrentPack(newPack);
  };
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [nextSessionId, setNextSessionId] = useState(null);
  const [isPlanning, setIsPlanning] = useState(false);

  // Add adaptive flag logging
  useEffect(() => {
    console.log('🏁 Adaptive Feature Status:', {
      ADAPTIVE_GLOBAL,
      userAdaptiveEnabled: user?.adaptive_enabled,
      effectiveAdaptive: adaptiveEnabled
    });
  }, [user, adaptiveEnabled]);

  // V2 HARDENING: Check for uncompleted sessions on mount
  useEffect(() => {
    if (propSessionId && !sessionId) {
      setSessionId(propSessionId);
    }
    
    // V2 HARDENING: Handle session resume from localStorage
    if (!propSessionId && !sessionId && user?.adaptive_enabled) {
      const storedSessionId = localStorage.getItem('currentSessionId');
      if (storedSessionId) {
        console.log('[HARDENING] Checking for uncompleted session on mount:', storedSessionId);
        // Don't auto-resume - let Dashboard handle it
      }
    }
  }, [propSessionId, sessionId, user]);

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
      const totalSessions = response.data.total_sessions || 0;
      const currentSessionNumber = totalSessions + 1; // Current session is total completed + 1
      setSessionNumber(currentSessionNumber);
      console.log('Session number calculated from completed sessions:', currentSessionNumber);
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
    const requestId = diagnosticRequestId.current;
    console.log(`[DIAGNOSTIC] ${requestId}: fetchNextQuestion called`);
    
    // Check if we have a valid session ID
    if (!sessionId) {
      console.error(`[DIAGNOSTIC] ${requestId}: No session ID - setting error`);
      setError('No active session found. Please start a new session from the dashboard.');
      setLoading(false);
      return;
    }

    // DIAGNOSTIC: Dump state before fetch
    console.log(`[STATE_DUMP] ${requestId}: Pre-fetch state`, {
      sessionId,
      adaptiveEnabled,
      currentPackLength: currentPack.length,
      currentQuestionIndex,
      nextSessionId,
      isPlanning,
      loading,
      hasCurrentQuestion: !!currentQuestion
    });

    setLoading(true);
    setError('');
    setUserAnswer('');
    setShowResult(false);
    setResult(null);
    setAnswerSubmitted(false);
    
    try {
      if (adaptiveEnabled) {
        console.log(`[DIAGNOSTIC] ${requestId}: Using ADAPTIVE flow`);
        // ADAPTIVE FLOW: Use local pack
        await handleAdaptiveQuestionFlow();
      } else {
        console.log(`[DIAGNOSTIC] ${requestId}: Using LEGACY flow`);
        // LEGACY FLOW: Server-driven next-question
        await handleLegacyQuestionFlow();
      }
    } catch (err) {
      console.error(`[DIAGNOSTIC] ${requestId}: Question flow ERROR:`, {
        error: err.message,
        stack: err.stack,
        adaptiveEnabled,
        currentFlow: adaptiveEnabled ? 'adaptive' : 'legacy'
      });
      setError('Failed to load question');
      setLoading(false);
    }
    
    // DIAGNOSTIC: Verify final state
    setTimeout(() => {
      console.log(`[STATE_VERIFY] ${requestId}: Post-fetch final state`, {
        hasCurrentQuestion: !!currentQuestion,
        questionId: currentQuestion?.id,
        sessionId,
        loadingCleared: !loading,
        hasError: !!error,
        currentUrl: window.location.href
      });
    }, 500);
  };

  const handleAdaptiveQuestionFlow = async () => {
    // If we have a pack but need to start/continue from it
    if (currentPack.length > 0) {
      // Serve from current pack
      serveQuestionFromPack(currentQuestionIndex);
    } else if (nextSessionId) {
      // Fetch planned pack and start serving
      await startNextAdaptiveSession(nextSessionId);
    } else {
      // No pack or planned session - trigger auto-plan guard
      await startNextAdaptiveSessionWithAutoPlanning();
    }
  };

  const startNextAdaptiveSession = async (sessionId) => {
    try {
      console.log('🎯 Starting adaptive session:', sessionId);
      const pack = await fetchAdaptivePack(sessionId);
      
      if (!pack || pack.length === 0) {
        throw new Error('Empty or invalid pack received');
      }
      
      console.log('✅ Pack received, setting up session state...');
      setCurrentPackSafe(pack);
      setCurrentQuestionIndex(0);
      setSessionId(sessionId);
      
      // Mark as served after we start rendering
      await markPackServed(sessionId);
      
      console.log('✅ Serving first question from pack...');
      
      // SURGICAL FIX: Wait for state update before serving question
      setTimeout(() => {
        console.log('✅ State settled, serving question with delay...');
        serveQuestionFromPack(0);
      }, 100);
      
      console.log('✅ Adaptive session started successfully');
    } catch (error) {
      console.error('❌ Adaptive session failed:', error);
      // V2 CRITICAL FIX: Don't fall back to legacy - it triggers dashboard redirect
      // Instead, show error and let user retry
      setError(`Adaptive session failed: ${error.message}. Please refresh to try again.`);
      setLoading(false);
      setIsPlanning(false);
    }
  };

  // Add session creation lock to prevent multiple simultaneous attempts  
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  // SURGICAL FIX: Add loading and session progress tracking
  const [isLoadingPack, setIsLoadingPack] = useState(false);
  
  // SURGICAL FIX: Helper to determine if session is in progress
  const inProgressSession = sessionId && sessionProgress && !result?.session_complete;

  const startNextAdaptiveSessionWithAutoPlanning = async () => {
    // Prevent multiple simultaneous session creation
    if (isCreatingSession) {
      console.log('⚠️ Session creation already in progress, skipping...');
      return;
    }
    
    setIsCreatingSession(true);
    setIsPlanning(true);  // Set planning state
    setError('');         // Clear any errors
    setLoading(true);     // Ensure loading is set
    
    try {
      console.log('🎯 Auto-planning session (no pre-planned pack available)...');
      
      // Get last completed session
      const lastSessionId = await getLastCompletedSessionId(user.id);
      const cached = loadNext(user.id);
      const nextSessionId = cached?.nextSessionId || generateSessionId();
      
      console.log('📋 Auto-planning with session ID:', nextSessionId);

      // Generate headers for planning
      const planHeaders = {
        'Idempotency-Key': `${user.id}:${lastSessionId}:${nextSessionId}`,  // V2 FIX: Proper idempotency format
        'X-Request-Id': nextSessionId
      };

      // First try to get existing pack
      let pack = await tryFetchPack(user.id, nextSessionId);
      
      if (!pack) {
        console.log('📋 No existing pack, triggering planning...');
        
        // Plan session with proper headers
        try {
          console.log('🚀 Calling plan-next with headers:', planHeaders);
          const planResponse = await axios.post(`${API}/adapt/plan-next`, {
            user_id: user.id,
            last_session_id: lastSessionId,
            next_session_id: nextSessionId
          }, { 
            headers: planHeaders,
            timeout: 25000  // V2 FIX: Reduced timeout since backend is now fast
          });
          
          console.log('✅ Planning completed:', planResponse.status, planResponse.data);
          
        } catch (error) {
          console.log('First planning attempt failed, retrying...', error.message);
          
          // Silent retry with jitter  
          await new Promise(r => setTimeout(r, 400 + Math.random() * 400));
          
          try {
            const retryResponse = await axios.post(`${API}/adapt/plan-next`, {
              user_id: user.id,
              last_session_id: lastSessionId,
              next_session_id: nextSessionId
            }, { 
              headers: planHeaders,
              timeout: 25000  // V2 FIX: Reduced timeout
            });
            
            console.log('✅ Planning retry completed:', retryResponse.status);
            
          } catch (retryError) {
            console.error('❌ Auto-plan guard failed after retry');
            // V2 CRITICAL FIX: Don't use legacy fallback - it causes dashboard redirect
            setError('Adaptive planning failed. Please refresh the page to try again.');
            return;  // V2 FIX: Early return to prevent state issues
          }
        }
        
        // V2 FIX: Wait a moment for backend to persist the pack
        console.log('⏳ Waiting for pack persistence...');
        await new Promise(r => setTimeout(r, 1000));
        
        // Fetch pack after planning with retries
        for (let attempt = 1; attempt <= 3; attempt++) {
          console.log(`📦 Pack fetch attempt ${attempt}/3...`);
          pack = await tryFetchPack(user.id, nextSessionId);
          
          if (pack && pack.length > 0) {
            console.log(`✅ Pack fetch successful on attempt ${attempt}: ${pack.length} questions`);
            break;
          } else {
            console.log(`⚠️ Pack fetch attempt ${attempt} failed, waiting...`);
            if (attempt < 3) {
              await new Promise(r => setTimeout(r, 2000 * attempt));  // Exponential backoff
            }
          }
        }
        
        if (!pack || pack.length === 0) {
          console.error('❌ Pack still not available after planning');
          // V2 CRITICAL FIX: Don't use legacy fallback - show error instead
          setError('Session planning completed but pack not ready. Please refresh to try again.');
          return;  // V2 FIX: Early return to prevent state issues
        }
      }
      
      // Success - serve adaptive pack
      console.log('✅ Pack available, setting up adaptive session...');
      console.log('📊 Pack preview:', pack.slice(0, 1));  // Log first item for debugging
      
      setCurrentPackSafe(pack);
      setCurrentQuestionIndex(0);
      setSessionId(nextSessionId);
      setNextSessionId(nextSessionId);
      
      // Clear localStorage and mark served
      clearNext(user.id);
      
      try {
        await markPackServed(nextSessionId);
        console.log('✅ Pack marked as served');
      } catch (markError) {
        console.warn('⚠️ Mark served failed, but continuing:', markError.message);
      }
      
      console.log('✅ About to serve first question from pack...');
      
      // SURGICAL FIX: Wait for React state updates before serving
      setTimeout(() => {
        console.log('✅ State settled, serving first question...');
        serveQuestionFromPack(0);
      }, 100);
      
      console.log('✅ Auto-plan guard successful, serving adaptive pack');
      
    } catch (error) {
      console.error('❌ Auto-plan guard failed:', error);
      // V2 CRITICAL FIX: Don't use legacy fallback - it causes dashboard redirect
      setError('Session creation failed. Please refresh the page to try again.');
      // Don't call handleLegacyQuestionFlow - it triggers session completion
    } finally {
      // V2 FIX: Always clear planning state
      console.log('🔧 V2 FIX: Clearing isPlanning state in finally block');
      setIsPlanning(false);
      setLoading(false);
      setIsCreatingSession(false);  // V2 FIX: Clear session creation lock
    }
  };

  const serveQuestionFromPack = (questionIndex) => {
    const requestId = diagnosticRequestId.current;
    console.log(`[DIAGNOSTIC] ${requestId}: Serving question ${questionIndex + 1} of ${currentPack.length}`);
    
    // DIAGNOSTIC: Dump critical state before serving
    console.log(`[STATE_DUMP] ${requestId}`, {
      questionIndex,
      packLength: currentPack.length,
      sessionId,
      currentQuestionId: currentQuestion?.id,
      sessionProgress,
      isLoading: loading,
      isPlanning,
      localStorage_keys: Object.keys(localStorage),
      sessionStorage_keys: Object.keys(sessionStorage)
    });
    
    // CRITICAL FIX: Validate pack exists before checking completion
    if (!currentPack || currentPack.length === 0) {
      console.error(`[DIAGNOSTIC] ${requestId}: CRITICAL - Pack is empty! Cannot serve question.`);
      setError('Session pack is empty. Please refresh to restart.');
      return;
    }
    
    if (questionIndex >= currentPack.length) {
      console.log(`[DIAGNOSTIC] ${requestId}: Session completion triggered - ${questionIndex} >= ${currentPack.length}`);
      // Session completed - trigger adaptive planning for next session
      handleAdaptiveSessionCompletion();
      return;
    }

    const packItem = currentPack[questionIndex];
    console.log(`[DIAGNOSTIC] ${requestId}: Pack item keys:`, Object.keys(packItem));
    
    // V2 FIX: Use actual question data from V2 pack structure
    const question = {
      id: packItem.item_id,
      stem: packItem.why || 'Question content unavailable',  // V2: Use actual stem
      options: {
        a: packItem.option_a || 'Option A',  // V2: Use real options
        b: packItem.option_b || 'Option B',
        c: packItem.option_c || 'Option C', 
        d: packItem.option_d || 'Option D'
      },
      has_image: false,
      subcategory: packItem.subcategory || packItem.pair?.split(':')[0] || 'Unknown',
      difficulty_band: packItem.difficulty_band || packItem.bucket || 'Medium',
      right_answer: packItem.right_answer || ''
    };

    console.log(`[DIAGNOSTIC] ${requestId}: Question prepared:`, {
      id: question.id,
      stem_length: question.stem?.length,
      options_keys: Object.keys(question.options),
      real_options: Object.values(question.options).filter(opt => !opt.startsWith('Option '))
    });

    setCurrentQuestion(question);
    setSessionProgress({
      current_question: questionIndex + 1,
      total_questions: currentPack.length
    });
    
    // CRITICAL: Explicitly clear loading states  
    setLoading(false);
    setIsPlanning(false);  // V2 FIX: Ensure planning state is cleared
    setError('');          // V2 FIX: Clear any error states
    
    console.log(`[DIAGNOSTIC] ${requestId}: V2 Adaptive question served successfully: ${question.id} (${questionIndex + 1}/${currentPack.length})`);
    
    // DIAGNOSTIC: Verify state was set correctly
    setTimeout(() => {
      console.log(`[STATE_VERIFY] ${requestId}: Post-serve state check`, {
        currentQuestionSet: !!currentQuestion,
        questionId: currentQuestion?.id,
        progressSet: !!sessionProgress,
        loadingCleared: !loading,
        planningCleared: !isPlanning,
        errorCleared: !error
      });
    }, 100);
  };

  const handleSessionCompletionWithHandshake = async (completionData) => {
    try {
      console.log('🎯 Session completed, triggering end-of-session handshake...');
      
      // NEW: Mark session as completed (sets completed_at timestamp)
      try {
        await axios.post(`${API}/sessions/mark-completed`, {
          session_id: sessionId
        });
        console.log('🏁 session completed:', sessionId);
      } catch (completionError) {
        console.warn('⚠️ Session completion timestamp failed:', completionError);
        // Don't fail the flow
      }
      
      // End-of-session handshake: plan next session if adaptive enabled
      if (adaptiveEnabled) {
        const lastSessionId = sessionId;
        const cached = loadNext(user.id);
        const nextSessionId = cached?.nextSessionId || generateSessionId();
        
        try {
          await axios.post(`${API}/adapt/plan-next`, {
            user_id: user.id,
            last_session_id: lastSessionId,
            next_session_id: nextSessionId
          }, {
            headers: {
              'Idempotency-Key': `${user.id}:${lastSessionId}:${nextSessionId}`
            }
          });
          
          // Persist for next session start
          persistNext(user.id, lastSessionId, nextSessionId);
          setNextSessionId(nextSessionId);
          
          console.log('✅ End-of-session handshake successful:', nextSessionId);
          
        } catch (error) {
          console.error('❌ End-of-session planning failed:', error);
          // Continue with session end even if planning fails
        }
      }
      
      // Call original session end handler
      if (onSessionEnd) {
        onSessionEnd(completionData);
      }
      
    } catch (error) {
      console.error('❌ Session completion handshake failed:', error);
      // Still call session end
      if (onSessionEnd) {
        onSessionEnd(completionData);
      }
    }
  };

  const handleAdaptiveSessionCompletion = async () => {
    await handleSessionCompletionWithHandshake({
      completed: true,
      questionsCompleted: currentPack.length || 12,
      totalQuestions: currentPack.length || 12
    });
  };

  const handleLegacyQuestionFlow = async () => {
    
    try {
      // Using global axios authorization header set by AuthProvider
      const response = await axios.get(`${API}/sessions/${sessionId}/next-question`);
      
      if (response.data.session_complete) {
        // Session completed - trigger end-of-session handshake
        await handleSessionCompletionWithHandshake({
          completed: true,
          questionsCompleted: response.data.questions_completed,
          totalQuestions: response.data.total_questions
        });
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
        // V2 FIX: Don't trigger session completion for adaptive sessions
        if (adaptiveEnabled && currentPack.length > 0) {
          console.log('⚠️ 404 in adaptive session - ignoring (using pack-based serving)');
          setError('Using adaptive pack mode - no legacy endpoint needed');
        } else {
          // Only complete session for legacy flows
          await handleSessionCompletionWithHandshake({ completed: true });
        }
      } else {
        setError('Failed to load next question');
        console.error('Error fetching next question:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  // SURGICAL FIX: Safe JSON parsing to prevent React crashes
  const safeJson = async (res) => {
    const txt = await res.text().catch(() => "");
    if (!txt) return null;
    try { return JSON.parse(txt); } catch { return null; }
  };

  const submitAnswer = async () => {
    const requestId = diagnosticRequestId.current;
    console.log(`[CRITICAL_DEBUG] ${requestId}: Submit answer initiated`);
    
    if (!userAnswer.trim()) {
      console.log(`[CRITICAL_DEBUG] ${requestId}: No answer selected`);
      alert('Please select an answer');
      return;
    }

    if (!sessionId) {
      console.error(`[CRITICAL_DEBUG] ${requestId}: No active session found`);
      setError('No active session found. Cannot submit answer.');
      return;
    }

    // SURGICAL FIX: Robust submit with no redirects/crashes
    setLoading(true);
    setAnswerSubmitted(true);
    
    try {
      console.log(`[CRITICAL_DEBUG] ${requestId}: Making submit request...`);
      
      // Use fetch for better error control than axios
      const res = await fetch(`${API}/log/question-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`,
          'X-Request-Id': requestId
        },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: currentQuestion.id,
          action: 'submit',
          data: {
            user_answer: userAnswer,
            session_type: adaptiveEnabled ? 'adaptive' : 'legacy'
          },
          timestamp: new Date().toISOString()
        })
      });
      
      console.log(`[CRITICAL_DEBUG] ${requestId}: Submit response status: ${res.status}`);
      
      if (res.status === 401) {
        // SURGICAL FIX: Auth drift - keep session state, show login modal (do NOT navigate)
        console.warn(`[CRITICAL_DEBUG] ${requestId}: Auth expired - keeping session state`);
        setError('Session expired. Please refresh to re-login.');
        return;
      }
      
      if (!res.ok) {
        const msg = await res.text().catch(() => '');
        console.error(`[CRITICAL_DEBUG] ${requestId}: Submit failed: ${res.status} ${msg}`);
        setError(`Submit failed (${res.status}). Please try again.`);
        return; // SURGICAL FIX: Stay on question, no state wipe
      }

      // SURGICAL FIX: Safe JSON parsing
      const responseData = await safeJson(res);
      console.log(`[CRITICAL_DEBUG] ${requestId}: Submit successful, response:`, responseData);
      
      // Create adaptive result for display
      const result = {
        correct: userAnswer.toLowerCase() === (currentQuestion.right_answer?.toLowerCase() || 'unknown'),
        correct_answer: currentQuestion.right_answer || 'Not specified',
        explanation: 'Answer logged successfully'
      };
      
      setResult(result);
      setShowResult(true);
      
      console.log(`[CRITICAL_DEBUG] ${requestId}: Result set, showResult=true`);
      
    } catch (err) {
      console.error(`[CRITICAL_DEBUG] ${requestId}: Submit CATCH error:`, err.message);
      // SURGICAL FIX: Robust error handling - keep session alive
      setError('Could not save your answer. Please retry.');
      setAnswerSubmitted(false);
      
    } finally {
      setLoading(false);
      console.log(`[CRITICAL_DEBUG] ${requestId}: Submit finally block - loading cleared`);
      
      // SURGICAL FIX: Never clear pack/session state on submit
      // SURGICAL FIX: Don't auto-advance - let user click Next
    }
  };

  const skipQuestion = async () => {
    if (!sessionId || !currentQuestion) {
      setError('No active session or question found.');
      return;
    }

    setLoading(true);
    
    try {
      // Log the skip action
      await logQuestionAction('skip', {});
      
      // Move to next question (adaptive or legacy)
      handleNextQuestion();
      
    } catch (err) {
      setError('Failed to skip question');
      console.error('Error skipping question:', err);
    } finally {
      setLoading(false);
    }
  };

  const logQuestionAction = async (action, data = {}) => {
    try {
      await axios.post(`${API}/log/question-action`, {
        session_id: sessionId,
        question_id: currentQuestion.id,
        action: action,
        data: data,
        timestamp: new Date().toISOString()
      });
    } catch (err) {
      console.error('Failed to log question action:', err);
      // Don't throw error - logging should not break the flow
    }
  };

  const handleNextQuestion = () => {
    const requestId = diagnosticRequestId.current;
    console.log(`[CRITICAL_DEBUG] ${requestId}: handleNextQuestion called`);
    
    if (adaptiveEnabled && currentPack.length > 0) {
      // Adaptive flow: advance to next question in pack
      const nextIndex = currentQuestionIndex + 1;
      console.log(`[CRITICAL_DEBUG] ${requestId}: Advancing to question ${nextIndex + 1} of ${currentPack.length}`);
      
      // SURGICAL FIX: Validate before advancing
      if (nextIndex >= currentPack.length) {
        console.log(`[CRITICAL_DEBUG] ${requestId}: Reached end of pack (${nextIndex} >= ${currentPack.length}) - completing session`);
        handleAdaptiveSessionCompletion();
        return;
      }
      
      setCurrentQuestionIndex(nextIndex);
      serveQuestionFromPack(nextIndex);
    } else {
      console.log(`[CRITICAL_DEBUG] ${requestId}: Using legacy flow for next question`);
      // Legacy flow: fetch from server
      fetchNextQuestion();
    }
  };

  const handleOptionSelect = (option) => {
    if (!answerSubmitted) {
      setUserAnswer(option);
    }
  };

  // Adaptive session helper functions
  const generateSessionId = () => {
    // Generate UUID (simple version for client-side) 
    if (crypto?.randomUUID) {
      return crypto.randomUUID();
    }
    return 'session_' + Math.random().toString(36).substring(2) + Date.now().toString(36);
  };

  const getLastCompletedSessionId = async (userId) => {
    try {
      const response = await axios.get(`${API}/sessions/last-completed-id`, {
        params: { user_id: userId }
      });
      return response.data?.session_id ?? 'S0';
    } catch (error) {
      console.log('No completed sessions found, using S0 for cold-start');
      return 'S0';
    }
  };

  const persistNext = (userId, lastSessionId, nextSessionId) => {
    localStorage.setItem(`twelvr:adapt:next:${userId}`, JSON.stringify({
      lastSessionId,
      nextSessionId, 
      at: Date.now()
    }));
  };

  const loadNext = (userId) => {
    try {
      const stored = localStorage.getItem(`twelvr:adapt:next:${userId}`);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  };

  const clearNext = (userId) => {
    localStorage.removeItem(`twelvr:adapt:next:${userId}`);
  };

  const tryFetchPack = async (userId, sessionId) => {
    try {
      console.log(`📦 Attempting to fetch pack for session: ${sessionId}`);
      const pack = await fetchAdaptivePack(sessionId);
      console.log(`✅ Pack fetch successful: ${pack ? pack.length : 0} questions`);
      return pack;
    } catch (error) {
      console.log(`❌ Pack fetch failed for ${sessionId}:`, error.response?.status, error.message);
      return null;
    }
  };

  const planNextAdaptiveSession = async (currentSessionId) => {
    try {
      setIsPlanning(true);
      console.log('🎯 Planning next adaptive session...');
      
      const nextSessId = generateSessionId();
      
      const response = await axios.post(`${API}/adapt/plan-next`, {
        user_id: user.id,
        last_session_id: currentSessionId,
        next_session_id: nextSessId
      }, {
        headers: {
          'Idempotency-Key': generateSessionId() // Use for idempotency
        }
      });
      
      setNextSessionId(nextSessId);
      console.log('✅ Adaptive session planned:', nextSessId);
      return response.data;
      
    } catch (error) {
      console.error('❌ Adaptive planning failed:', error);
      throw error;
    } finally {
      setIsPlanning(false);
    }
  };

  const fetchAdaptivePack = async (sessionId) => {
    try {
      console.log('📦 Fetching adaptive pack for session:', sessionId);
      
      const response = await axios.get(`${API}/adapt/pack`, {
        params: {
          user_id: user.id,
          session_id: sessionId
        }
      });
      
      const pack = response.data.pack || [];
      console.log('✅ Adaptive pack fetched:', pack.length, 'questions');
      return pack;
      
    } catch (error) {
      console.error('❌ Adaptive pack fetch failed:', error);
      throw error;
    }
  };

  const markPackServed = async (sessionId) => {
    const requestId = diagnosticRequestId.current;
    
    // V2 HARDENING: Only mark served once per session
    if (packMarkedServed) {
      console.log(`[DIAGNOSTIC] ${requestId}: Pack already marked served, skipping`);
      return;
    }
    
    try {
      await axios.post(`${API}/adapt/mark-served`, {
        user_id: user.id,
        session_id: sessionId
      });
      console.log(`[DIAGNOSTIC] ${requestId}: Pack marked as served:`, sessionId);
      setPackMarkedServed(true);  // V2 HARDENING: Set flag to prevent duplicates
      
      // NEW: Mark session as started (first question render)
      try {
        await axios.post(`${API}/sessions/mark-started`, {
          session_id: sessionId
        });
        console.log(`[DIAGNOSTIC] ${requestId}: Session marked as started`);
      } catch (startError) {
        console.warn(`[DIAGNOSTIC] ${requestId}: Mark started failed (non-critical):`, startError.message);
      }
      
    } catch (error) {
      console.error(`[DIAGNOSTIC] ${requestId}: Mark served failed:`, error.message);
      // V2 HARDENING: Don't throw - marking served failure shouldn't break session
      console.warn(`[DIAGNOSTIC] ${requestId}: Continuing session despite mark-served failure`);
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
          <h3 className="text-lg font-semibold mb-4" style={{ color: '#545454' }}>You, compounded.</h3>
          <p className="text-base mb-6" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            Twelvr is compiling your perfect session.
          </p>
        </div>
      </div>
    );
  }

  if (loading && !currentQuestion || isPlanning) {
    return (
      <div className="flex items-center justify-center min-h-screen" style={{ fontFamily: 'Manrope, sans-serif' }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 mx-auto" style={{ borderColor: '#9ac026' }}></div>
          <p className="mt-4" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>
            {isPlanning ? 'Preparing next session...' : 'Loading your session...'}
          </p>
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
    <SessionErrorBoundary>
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
              <MathRenderer 
                content={currentQuestion.stem}
                className="text-lg leading-relaxed"
                style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}
              />
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
                        <MathRenderer 
                          content={value}
                          style={{ fontFamily: 'Lato, sans-serif' }}
                        />
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

            {/* Action Buttons */}
            {!showResult && (
              <div className="space-y-3">
                {/* Submit Answer Button */}
                <button
                  onClick={async () => {
                    const requestId = diagnosticRequestId.current;
                    console.log(`[CRITICAL_DEBUG] ${requestId}: Submit button clicked - starting submission`);
                    
                    try {
                      console.log(`[CRITICAL_DEBUG] ${requestId}: About to call submitAnswer function`);
                      await submitAnswer();
                      console.log(`[CRITICAL_DEBUG] ${requestId}: submitAnswer function completed successfully`);
                    } catch (submitError) {
                      console.error(`[CRITICAL_DEBUG] ${requestId}: SUBMIT BUTTON ERROR:`, {
                        error: submitError.message,
                        stack: submitError.stack,
                        timestamp: new Date().toISOString()
                      });
                      
                      // Try to keep session alive even if submit fails
                      setError(`Submit failed: ${submitError.message}`);
                      setLoading(false);
                      setAnswerSubmitted(false);
                    }
                  }}
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

                {/* Skip Question Button */}
                <button
                  onClick={skipQuestion}
                  disabled={loading || answerSubmitted || !currentQuestion.options}
                  className="w-full py-2 px-6 rounded-lg font-medium transition-colors disabled:cursor-not-allowed border-2"
                  style={{
                    backgroundColor: 'transparent',
                    color: (loading || answerSubmitted || !currentQuestion.options) ? '#cccccc' : '#ff6d4d',
                    borderColor: (loading || answerSubmitted || !currentQuestion.options) ? '#cccccc' : '#ff6d4d',
                    fontFamily: 'Lato, sans-serif'
                  }}
                  onMouseOver={(e) => {
                    if (!e.target.disabled) {
                      e.target.style.backgroundColor = '#fff5f3';
                      e.target.style.borderColor = '#e55a3c';
                      e.target.style.color = '#e55a3c';
                    }
                  }}
                  onMouseOut={(e) => {
                    if (!e.target.disabled) {
                      e.target.style.backgroundColor = 'transparent';
                      e.target.style.borderColor = '#ff6d4d';
                      e.target.style.color = '#ff6d4d';
                    }
                  }}
                >
                  {loading ? 'Skipping...' : 'Skip Question →'}
                </button>
              </div>
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
                      <MathRenderer 
                        content={result.user_answer}
                        className="text-lg"
                        style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}
                      />
                    </div>
                    <div>
                      <p className="text-sm font-medium mb-1" style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}>Correct Answer:</p>
                      <MathRenderer 
                        content={result.correct_answer}
                        className="text-lg font-semibold"
                        style={{ color: '#9ac026', fontFamily: 'Lato, sans-serif' }}
                      />
                    </div>
                  </div>
                </div>

                {/* Solution Feedback */}
                {result.solution_feedback && (
                  <div className="border rounded-lg p-4 mb-4" style={{ backgroundColor: '#f7fdf0', borderColor: '#9ac026' }}>
                    <h4 className="font-semibold mb-3" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>Solution</h4>
                    
                    {/* Snap Read - NEW: Display above solution_approach */}
                    {result.solution_feedback.snap_read && (
                      <div className="mb-6">
                        <h5 className="font-semibold mb-3 text-lg" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>⚡ Quick Read:</h5>
                        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg border" style={{ borderColor: '#e0e7ff' }}>
                          <MathRenderer 
                            content={result.solution_feedback.snap_read}
                            className="leading-relaxed text-base font-medium"
                            style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}
                          />
                        </div>
                      </div>
                    )}
                    
                    {/* Solution Approach */}
                    {result.solution_feedback.solution_approach && (
                      <div className="mb-6">
                        <h5 className="font-semibold mb-3 text-lg" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>📋 Approach:</h5>
                        <div className="bg-white p-4 rounded-lg border" style={{ borderColor: '#e8f5e8' }}>
                          <MathRenderer 
                            content={result.solution_feedback.solution_approach}
                            className="leading-relaxed text-base"
                            style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Detailed Solution */}
                    {result.solution_feedback.detailed_solution && (
                      <div className="mb-6">
                        <h5 className="font-semibold mb-3 text-lg" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>📖 Detailed Solution:</h5>
                        <div className="bg-white p-6 rounded-lg border" style={{ borderColor: '#e8f5e8' }}>
                          <MathRenderer 
                            content={result.solution_feedback.detailed_solution}
                            className="leading-relaxed text-base"
                            style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Principle to remember */}
                    {result.solution_feedback.principle_to_remember && (
                      <div>
                        <h5 className="font-semibold mb-3 text-lg" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>💡 Principle to remember:</h5>
                        <div className="bg-white p-4 rounded-lg border" style={{ borderColor: '#e8f5e8' }}>
                          <MathRenderer 
                            content={result.solution_feedback.principle_to_remember}
                            className="leading-relaxed"
                            style={{ color: '#545454', fontFamily: 'Lato, sans-serif' }}
                          />
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
    </SessionErrorBoundary>
  );
};

export default SessionSystem;