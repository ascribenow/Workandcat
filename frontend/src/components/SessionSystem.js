import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth, API } from './AuthProvider';
import MathRenderer from './MathRenderer';
// REMOVED: ADAPTIVE_GLOBAL import - system is now adaptive-only
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
  
  // BLUEPRINT-ONLY: System is now purely Blueprint session platform
  const blueprintEnabled = true; // Always Blueprint
  
  const [sessionId, setSessionId] = useState(propSessionId);
  const [sessionNumber, setSessionNumber] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [sessionProgress, setSessionProgress] = useState(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);
  const [answerSubmitted, setAnswerSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState('');
  const [imageZoomed, setImageZoomed] = useState(false);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  
  // Doubt conversation states
  const [showDoubtModal, setShowDoubtModal] = useState(false);
  const [doubtMessage, setDoubtMessage] = useState('');
  
  // Pre-session insight states
  const [preSessionInsight, setPreSessionInsight] = useState(null);
  const [showPreSessionModal, setShowPreSessionModal] = useState(false);

  // Function to fetch pre-session insights
  const fetchPreSessionInsight = async () => {
    try {
      const token = localStorage.getItem('cat_prep_token');
      const response = await axios.get(`${API}/session/pre-session-insight`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        params: {
          session_id: sessionId
        },
        timeout: 10000  // 10 second timeout
      });
      
      if (response.data) {
        setPreSessionInsight(response.data);
        setShowPreSessionModal(true);
        console.log('Pre-session insight loaded:', response.data);
      }
    } catch (error) {
      console.error('Error fetching pre-session insight:', error);
      // Don't block session start if insights fail to load
    }
  };
  const [doubtHistory, setDoubtHistory] = useState([]);
  const [doubtLoading, setDoubtLoading] = useState(false);
  const [messageCount, setMessageCount] = useState(0);
  const [remainingMessages, setRemainingMessages] = useState(10);
  const [conversationLocked, setConversationLocked] = useState(false);

  // Adaptive session state  
  const [currentPack, setCurrentPack] = useState([]);
  
  // SURGICAL FIX: Add ref for latest pack to avoid stale closures
  const currentPackRef = useRef(currentPack);
  useEffect(() => { currentPackRef.current = currentPack; }, [currentPack]);
  
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
  
  // CRITICAL DEBUG: Monitor currentQuestion state changes
  useEffect(() => {
    console.log(`[CURRENT_QUESTION_DEBUG] State changed:`, {
      hasCurrentQuestion: !!currentQuestion,
      questionId: currentQuestion?.id?.substring(0, 8),
      questionStem: currentQuestion?.stem?.substring(0, 50),
      timestamp: new Date().toISOString()
    });
  }, [currentQuestion]);
  
  // V2 HARDENING: Track mark-served state to prevent duplicate calls
  const [packMarkedServed, setPackMarkedServed] = useState(false);

  // SURGICAL FIX: Atomic pack fetch with loading awareness
  const packEpochRef = useRef(0);
  
  const setCurrentPackSafe = (nextPack, reason) => {
    // Record history
    recordPackWrite(nextPack, reason);
    
    // SURGICAL FIX: While session is in progress, never accept null/empty pack writes
    if (inProgressSession && (!nextPack || nextPack.length === 0)) {
      console.warn('[PACK-GUARD] ignored empty pack write while in-progress', { reason, inProgressSession });
      return;
    }
    
    console.log(`[PACK-SAFE] Setting pack: ${Array.isArray(nextPack) ? nextPack.length : 'null'} items (${reason})`);
    setCurrentPack(nextPack || []);
  };
  
  // SURGICAL FIX: Dedicated clear function for explicit pack clearing
  // Blueprint Session Functions (New System) - PERFORMANCE OPTIMIZED
  const fetchBlueprintSession = async (sessionId) => {
    console.log(`[BLUEPRINT] 🔍 Starting optimized fetchBlueprintSession for ${sessionId.substring(0, 8)}`);
    
    try {
      // Use new bulk endpoint to get all questions at once
      console.log(`[BLUEPRINT] 🚀 Fetching all questions via bulk endpoint: ${API}/session/questions/${sessionId}`);
      
      const response = await axios.get(`${API}/session/questions/${sessionId}`, {
        timeout: 10000,  // 10 second timeout
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log(`[BLUEPRINT] ✅ Bulk questions response:`, response.data);
      
      const questions = response.data.questions || [];
      
      if (questions.length === 0) {
        console.error(`[BLUEPRINT] ❌ CRITICAL: No questions returned from bulk endpoint!`);
        throw new Error(`No questions found for session ${sessionId}`);
      }
      
      // VALIDATION: Log question consistency data for debugging
      console.log(`[BLUEPRINT] 🔍 Question validation check:`, {
        total_questions: questions.length,
        first_question_meta: questions[0]?._display_meta,
        position_sequence: questions.map(q => q.position).slice(0, 5),
        question_ids: questions.map(q => q.id?.substring(0, 8)).slice(0, 5)
      });
      
      // Convert Blueprint questions to pack format for compatibility with existing UI
      const pack = questions.map((question) => ({
        id: question.id,
        stem: question.stem,
        option_a: question.option_a,
        option_b: question.option_b,
        option_c: question.option_c,
        option_d: question.option_d,
        difficulty_band: question.difficulty_band,
        subcategory: question.subcategory,
        type_of_question: question.type_of_question,
        position: question.position,
        session_type: 'blueprint',
        answer: question.answer || '',
        // Preserve validation metadata for debugging
        _display_meta: question._display_meta
      }));
      
      // Sort pack by position to ensure correct order
      pack.sort((a, b) => a.position - b.position);
      
      console.log(`[BLUEPRINT] 🎉 Optimized pack creation successful - ${pack.length} questions`);
      console.log(`[BLUEPRINT] 📋 Pack sample:`, {
        firstQuestion: {
          id: pack[0].id.substring(0, 8),
          position: pack[0].position,
          stemLength: pack[0].stem.length,
          hasOptions: !!(pack[0].option_a && pack[0].option_b),
          difficulty: pack[0].difficulty_band
        }
      });
      
      console.log(`[BLUEPRINT] 📦 fetchBlueprintSession completed successfully, returning pack`);
      return pack;
      
    } catch (error) {
      console.error('[BLUEPRINT] ❌ Error in optimized fetchBlueprintSession:', error);
      console.error('[BLUEPRINT] ❌ Error details:', {
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data
      });
      console.error('[BLUEPRINT] ❌ Error stack:', error.stack);
      throw error;
    }
  };

  const submitBlueprintAnswer = async (sessionId, position, answer) => {
    try {
      console.log(`[BLUEPRINT] Submitting answer for position ${position}:`, answer);
      
      const response = await axios.post(`${API}/session/submit`, {
        session_id: sessionId,
        position: position,
        answer: answer
      });
      
      console.log(`[BLUEPRINT] Answer submitted successfully:`, response.data);
      console.log(`[SOLUTION_FEEDBACK_DEBUG] Backend response solution_feedback:`, {
        hasSolutionFeedback: !!response.data.solution_feedback,
        snapRead: response.data.solution_feedback?.snap_read?.substring(0, 100),
        approach: response.data.solution_feedback?.solution_approach?.substring(0, 100),
        detailedSolution: response.data.solution_feedback?.detailed_solution?.substring(0, 100),
        principle: response.data.solution_feedback?.principle_to_remember?.substring(0, 100)
      });
      
      // VALIDATION: Cross-check answer consistency with current question
      console.log(`[BLUEPRINT] 🔍 Answer consistency check:`, {
        submitted_to_position: position,
        current_question_id: currentQuestion?.id?.substring(0, 8),
        backend_correct_answer: response.data.correct_answer,
        user_answer: userAnswer,
        is_correct: response.data.is_correct
      });
      
      return {
        success: response.data.success,
        is_correct: response.data.is_correct,
        correct_answer: response.data.correct_answer,
        explanation: response.data.explanation,
        solution_feedback: response.data.solution_feedback,
        is_complete: response.data.is_complete
      };
      
    } catch (error) {
      console.error('[BLUEPRINT] Error submitting answer:', error);
      throw error;
    }
  };

  const completeBlueprintSession = async (sessionId) => {
    try {
      console.log(`[BLUEPRINT] Completing session ${sessionId.substring(0, 8)}`);
      
      const response = await axios.post(`${API}/session/complete`, {
        session_id: sessionId
      });
      
      console.log(`[BLUEPRINT] Session completed:`, response.data);
      return response.data.summary;
      
    } catch (error) {
      console.error('[BLUEPRINT] Error completing session:', error);
      throw error;
    }
  };

  const clearPack = () => {
    recordPackWrite([], 'explicit-clear-pack');
    setCurrentPack([]); // Only this path may set empty
  };
  
  const fetchPackSafe = async (userId, sessionId, retryCount = 0) => {
    const epoch = ++packEpochRef.current;
    setIsLoadingPack(true);
    
    try {
      console.log(`[PACK-FETCH] Starting fetch epoch ${epoch} for session ${sessionId.substring(0, 8)} (attempt ${retryCount + 1})`);
      
      const res = await fetch(`${API}/adapt/pack?user_id=${userId}&session_id=${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!res.ok) {
        console.warn(`[PACK-FETCH] Non-OK response: ${res.status} (attempt ${retryCount + 1})`);
        
        // RACE CONDITION FIX: Retry pack fetch for 404 errors (pack not persisted yet)
        if (res.status === 404 && retryCount < 3) {
          console.log(`[PACK-FETCH] Pack not ready yet, retrying in ${(retryCount + 1) * 1000}ms...`);
          await new Promise(resolve => setTimeout(resolve, (retryCount + 1) * 1000)); // 1s, 2s, 3s delays
          return await fetchPackSafe(userId, sessionId, retryCount + 1);
        }
        
        // SURGICAL FIX: Don't zero pack on error - keep current pack
        setError(`Pack fetch failed (${res.status}) after ${retryCount + 1} attempts. Current session preserved.`);
        return null;
      }
      
      const data = await res.json();
      
      // SURGICAL FIX: Ignore stale responses
      if (packEpochRef.current === epoch) {
        const pack = data?.pack || [];
        setCurrentPackSafe(pack, `fetch-pack-success-epoch-${epoch}`);
        console.log(`[PACK-FETCH] Success epoch ${epoch}: ${pack.length} items`);
        return pack;
      } else {
        console.warn(`[PACK-FETCH] Stale response ignored: epoch ${epoch} vs current ${packEpochRef.current}`);
        return null;
      }
      
    } catch (e) {
      console.error('[PACK-FETCH] Error:', e.message);
      // SURGICAL FIX: Keep old pack, don't write []
      setError('Network error while fetching pack. Current session preserved.');
      return null;
    } finally {
      if (packEpochRef.current === epoch) {
        setIsLoadingPack(false);
      }
    }
  };
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [nextSessionId, setNextSessionId] = useState(null);
  const [isPlanning, setIsPlanning] = useState(false);

  // Add adaptive flag logging
  useEffect(() => {
    console.log('🏁 Blueprint Feature Status: SYSTEM IS BLUEPRINT-ONLY', {
      blueprintEnabled: true,
      userAdaptiveEnabled: user?.adaptive_enabled,
      effectiveBlueprint: blueprintEnabled
    });
  }, [user, blueprintEnabled]);

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
      // First check if this session has existing progress for resumption
      checkAndResumeSession();
      
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

  // Session Resumption Logic - Updated for Blueprint Sessions
  const checkAndResumeSession = async () => {
    if (!sessionId) return;
    
    try {
      console.log(`[RESUME] Checking session type for: ${sessionId.substring(0, 8)}`);
      console.log(`[RESUME] SessionMetadata available:`, !!sessionMetadata);
      console.log(`[RESUME] SessionMetadata content:`, sessionMetadata);
      
      // Check if this is a Blueprint session by looking at sessionMetadata
      const hasSessionType = sessionMetadata?.session_type === 'blueprint';
      const hasQuestions = sessionMetadata?.questions?.length > 0;
      const isBlueprintSession = hasSessionType || hasQuestions;
      
      console.log(`[RESUME] Blueprint session detection:`, {
        hasSessionType,
        hasQuestions,
        sessionType: sessionMetadata?.session_type,
        questionsLength: sessionMetadata?.questions?.length,
        isBlueprintSession
      });
      
      if (isBlueprintSession) {
        console.log(`[RESUME] ✅ Detected Blueprint session, loading directly from metadata`);
        
        // For Blueprint sessions, use the questions from metadata
        const questions = sessionMetadata.questions || [];
        if (questions.length > 0) {
          console.log(`[BLUEPRINT] ✅ Loading ${questions.length} questions from metadata`);
          
          // Convert Blueprint questions to pack format for compatibility with existing UI
          const pack = questions.map((question, index) => ({
            id: question.id,
            stem: question.stem,
            option_a: question.option_a,
            option_b: question.option_b,
            option_c: question.option_c,
            option_d: question.option_d,
            difficulty_band: question.difficulty_band,
            subcategory: question.subcategory,
            type_of_question: question.type_of_question,
            position: question.position || (index + 1),
            session_type: 'blueprint',
            answer: question.answer || ''
          }));
          
          console.log(`[BLUEPRINT] ✅ Converted ${pack.length} questions to pack format`);
          console.log(`[BLUEPRINT] Sample question:`, pack[0]);
          
          // Fetch pre-session insights before starting
          await fetchPreSessionInsight();
          
          setCurrentPackSafe(pack, 'blueprint-session-load');
          
          // CRITICAL FIX: Clear planning state to allow first question serving
          setIsPlanning(false);
          setLoading(false);
          
          // Set up session progress
          const currentPosition = sessionMetadata.current_position || 1;
          setCurrentQuestionIndex(currentPosition - 1); // Convert to 0-based index
          
          console.log(`[BLUEPRINT] ✅ Session ready with ${pack.length} questions, starting at position ${currentPosition}`);
          console.log(`[BLUEPRINT] ✅ Current question index set to: ${currentPosition - 1}`);
        } else {
          // Fetch Blueprint session data if no questions in metadata (resumed sessions)
          console.log(`[BLUEPRINT] ⚠️ No questions in metadata, fetching from API for resumed session`);
          
          try {
            console.log(`[BLUEPRINT] 🚀 Calling fetchBlueprintSession...`);
            const pack = await fetchBlueprintSession(sessionId);
            
            console.log(`[BLUEPRINT] 📦 fetchBlueprintSession returned:`, {
              packExists: !!pack,
              packLength: pack ? pack.length : 0,
              packType: typeof pack
            });
            
            if (pack && pack.length > 0) {
              console.log(`[BLUEPRINT] ✅ Pack validation successful - ${pack.length} questions`);
              console.log(`[BLUEPRINT] 📋 Sample question:`, {
                id: pack[0].id?.substring(0, 8),
                stemLength: pack[0].stem?.length,
                hasOptions: !!(pack[0].option_a && pack[0].option_b)
              });
              
              console.log(`[BLUEPRINT] 🔧 Calling setCurrentPackSafe...`);
              setCurrentPackSafe(pack, 'blueprint-api-load');
              
              console.log(`[BLUEPRINT] ⚡ setCurrentPackSafe called successfully`);
              
              // CRITICAL FIX: Clear planning state to allow first question serving
              setIsPlanning(false);
              setLoading(false);
              
              // For resumed sessions, set position based on current_position from backend
              const currentPosition = sessionMetadata.current_position || ((sessionMetadata.answered_count || 0) + 1);
              const questionIndex = currentPosition - 1; // Convert to 0-based index for question array
              setCurrentQuestionIndex(questionIndex);
              console.log(`[BLUEPRINT] ✅ Resumed session at position ${currentPosition} (question index ${questionIndex})`);
              console.log(`[BLUEPRINT] 📊 Session progress: ${sessionMetadata.answered_count || 0} answered, resuming at position ${currentPosition}`);
              
            } else {
              console.error(`[BLUEPRINT] ❌ Invalid pack returned:`, pack);
            }
          } catch (fetchError) {
            console.error(`[BLUEPRINT] ❌ fetchBlueprintSession failed:`, fetchError);
            console.error(`[BLUEPRINT] ❌ Full error:`, fetchError.stack);
          }
        }
        return;
      }
      
      // Legacy adaptive session logic
      console.log(`[RESUME] Not a Blueprint session, checking for legacy adaptive session`);
      
      const progress = await getSessionProgress(sessionId);
      
      if (progress && progress.current_question_index > 0) {
        console.log(`[RESUME] Found existing progress: Q${progress.current_question_index + 1}/${progress.total_questions}`);
        
        // Resume from where user left off
        setCurrentQuestionIndex(progress.current_question_index);
        
        // Don't fetch next question - we'll use the pack-based serving
        return; // Skip fetchNextQuestion call
      }
      
      // No existing progress, start fresh
      console.log(`[RESUME] No existing progress found, starting fresh session`);
      fetchNextQuestion();
      
    } catch (error) {
      console.warn('[RESUME] Error checking session progress, starting fresh:', error.message);
      console.error('[RESUME] Full error details:', error);
      fetchNextQuestion();
    }
  };

  // SURGICAL FIX: State-driven first question serving when pack becomes ready
  const firstServeDoneRef = useRef(false);
  useEffect(() => {
    const packLength = currentPackRef.current?.length || 0;
    const hasCurrentQuestion = !!currentQuestion;
    const hasSessionId = !!sessionId;
    const notPlanning = !isPlanning;
    const notServedYet = !firstServeDoneRef.current;
    
    console.log(`[BOOT_DEBUG] Question serving state check:`, {
      packLength,
      hasCurrentQuestion,
      hasSessionId,
      notPlanning,
      notServedYet,
      sessionType: sessionMetadata?.session_type,
      firstServeDone: firstServeDoneRef.current
    });
    
    if (
      currentPackRef.current?.length > 0 &&
      !currentQuestion &&
      sessionId &&
      !isPlanning &&
      !firstServeDoneRef.current
    ) {
      console.log('[BOOT] ✅ All conditions met - Pack ready & no currentQuestion; serving Q1');
      console.log('[BOOT] Pack sample:', currentPackRef.current[0]);
      firstServeDoneRef.current = true;
      serveQuestionFromPack(0);
    } else {
      console.log(`[BOOT_DEBUG] ❌ Conditions not met: pack=${packLength > 0}, noQuestion=${!hasCurrentQuestion}, session=${hasSessionId}, notPlanning=${notPlanning}, notServed=${notServedYet}`);
    }
  }, [currentQuestion, sessionId, isPlanning, currentPack]);

  // SURGICAL FIX: Reset first serve flag when session changes
  useEffect(() => {
    firstServeDoneRef.current = false;
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

  // ASYNC POLLING: Poll for pack readiness (202 → 200 pattern) with SmartPoller
  const pollForPackReadiness = async (sessionId) => {
    const { SmartPoller } = await import('../utils/smartPolling');
    
    setLoadingMessage('Preparing your session...');
    
    const poller = new SmartPoller(axios, '/adapt/pack', {
      user_id: user.id,
      session_id: sessionId
    }, {
      budgetMs: 75000, // 75s budget aligned with backend timeout
      baseDelay: 1000,
      maxDelay: 8000,
      treat404AsPreparingMs: 65000 // NEW: Handle early 404 as preparing
    });

    const result = await poller.poll();

    if (result.success) {
      setLoadingMessage('Session ready! Loading questions...');
      console.log(`✅ Pack ready after ${result.elapsed_ms}ms, ${result.attempts} attempts`);
      
      // Return pack in expected format for existing code
      return result.data.pack || result.data;
      
    } else {
      console.error(`❌ Polling failed after ${result.elapsed_ms}ms, ${result.attempts} attempts:`, result.error);
      
      // Set error state for UI handling
      if (result.retryAvailable) {
        setError(`${result.error} Please try again.`);
      } else {
        setError(`${result.error} Please refresh the page.`);
      }
      
      throw new Error(result.error);
    }
  };

  // PRE-WARMING: Trigger next session preparation in background
  const triggerNextSessionPreWarming = async () => {
    try {
      const nextSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Fire-and-forget request to pre-warm next session
      axios.post(`${API}/adapt/plan-next`, {
        user_id: user.id,
        last_session_id: sessionId,
        next_session_id: nextSessionId
      }, { 
        headers: { 
          Authorization: `Bearer ${localStorage.getItem('cat_prep_token')}`,
          'Content-Type': 'application/json',
          'Idempotency-Key': `prewarm_${Date.now()}`
        },
        timeout: 8000
      }).then(response => {
        if (response.status === 202) {
          console.log('🔄 Next session pre-warming triggered successfully');
        }
      }).catch(err => {
        console.log('⚠️ Pre-warming trigger failed (non-critical):', err.message);
      });
      
    } catch (error) {
      console.log('⚠️ Pre-warming setup failed (non-critical):', error.message);
    }
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
    
    // SURGICAL FIX: Gate fetchNextQuestion while planning to prevent double-boot
    if (isPlanning) {
      console.log(`[DIAGNOSTIC] ${requestId}: Planning in progress; skipping fetchNextQuestion to avoid race.`);
      return;
    }
    
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
      blueprintEnabled,
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
      console.log(`[DIAGNOSTIC] ${requestId}: Using ADAPTIVE-ONLY flow`);
      // ADAPTIVE-ONLY FLOW: Use local pack data
      await handleAdaptiveQuestionFlow();
    } catch (err) {
      console.error(`[DIAGNOSTIC] ${requestId}: Question flow ERROR:`, {
        error: err.message,
        stack: err.stack,
        blueprintEnabled,
        currentFlow: blueprintEnabled ? 'blueprint' : 'legacy'
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
    // SURGICAL FIX: Use currentPackRef to avoid stale closure reads
    if (currentPackRef.current && currentPackRef.current.length > 0) {
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
      const pack = await fetchPackSafe(user.id, sessionId);
      
      // SURGICAL FIX: Safe guard - loading-aware and session-aware
      if (!isLoadingPack && (pack == null || pack.length === 0) && !inProgressSession) {
        // SURGICAL FIX: DO NOT navigate - show local error UI
        setError('Pack unavailable for this session. Please refresh to restart.');
        setLoading(false);
        setIsPlanning(false);
        return;
      }
      
      if (pack && pack.length > 0) {
        console.log('✅ Pack received, setting up session state...');
        setCurrentPackSafe(pack, 'startNextAdaptiveSession-success');
        setCurrentQuestionIndex(0);
        setSessionId(sessionId);
        
        // Mark as served after we start rendering
        await markPackServed(sessionId);
        
        console.log('✅ Serving first question from pack...');
        
        // SURGICAL FIX: State-driven serving - removed setTimeout, will be handled by useEffect
        console.log('✅ Adaptive session started successfully');
      }
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
      let pack = await fetchPackSafe(user.id, nextSessionId);
      
      // SURGICAL FIX: Safe guard for pack check
      if (!isLoadingPack && (pack == null || pack.length === 0) && !inProgressSession) {
        console.log('📋 No existing pack, triggering planning...');
        
        // ASYNC PATTERN: Trigger planning in background (202), then poll for readiness
        try {
          console.log('🚀 Triggering async session planning...');
          
          // 1. Trigger planning (expect 202, don't wait)
          const planResponse = await axios.post(`${API}/adapt/plan-next`, {
            user_id: user.id,
            last_session_id: lastSessionId,
            next_session_id: nextSessionId
          }, { 
            headers: planHeaders,
            timeout: 8000  // Short timeout - just triggering background job
          });
          
          if (planResponse.status === 202) {
            console.log('✅ Session planning triggered in background');
            
            // CRITICAL: Use backend's canonical session ID for polling
            const canonicalSessionId = planResponse.data?.session_id || nextSessionId;
            if (canonicalSessionId !== nextSessionId) {
              console.log(`📋 Backend returned canonical session ID: ${canonicalSessionId.substring(0, 8)}... (was: ${nextSessionId.substring(0, 8)}...)`);
            }
            
            // 2. Poll for pack readiness using canonical ID
            pack = await pollForPackReadiness(canonicalSessionId);
            
            console.log('✅ Pack received from polling:', pack?.length || 0, 'questions');
            
          } else {
            throw new Error(`Unexpected plan-next response: ${planResponse.status}`);
          }
          
        } catch (error) {
          console.log('Planning trigger failed, trying fallback...', error.message);
          
          // Fallback: retry once with longer timeout for backward compatibility
          try {
            const retryResponse = await axios.post(`${API}/adapt/plan-next`, {
              user_id: user.id,
              last_session_id: lastSessionId,
              next_session_id: nextSessionId
            }, { 
              headers: planHeaders,
              timeout: 25000  // Fallback timeout
            });
            
            console.log('✅ Planning fallback completed:', retryResponse.status);
            
            // If fallback succeeded, fetch pack normally
            await new Promise(r => setTimeout(r, 1000));
            pack = await fetchPackSafe(user.id, nextSessionId);
            
          } catch (retryError) {
            console.error('❌ Session planning failed after retry');
            setError('Session planning failed. Please refresh the page to try again.');
            return;
          }
        }
        
        // SURGICAL FIX: Safe guard after planning
        if (!isLoadingPack && (pack == null || pack.length === 0) && !inProgressSession) {
          console.error('❌ Pack still not available after planning');
          // SURGICAL FIX: Don't navigate - show local error UI
          setError('Session planning completed but pack not ready. Please refresh to try again.');
          return;  // V2 FIX: Early return to prevent state issues
        }
      }
      
      // Success - serve adaptive pack
      console.log('✅ Pack available, setting up adaptive session...');
      console.log('📊 Pack preview:', pack.slice(0, 1));  // Log first item for debugging
      
      setCurrentPackSafe(pack, 'startNextAdaptiveSessionWithAutoPlanning-success');
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
      
      // SURGICAL FIX: State-driven serving - removed setTimeout, will be handled by useEffect
      console.log('✅ Auto-plan guard successful, serving adaptive pack');
      
    } catch (error) {
      console.error('❌ Auto-plan guard failed:', error);
      // ADAPTIVE-ONLY: Show user-friendly error message
      setError('Session creation failed. Please refresh the page to try again.');
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
    // SURGICAL FIX: Use currentPackRef to get live pack
    const livePack = currentPackRef.current;
    console.log(`[DIAGNOSTIC] ${requestId}: Serving question ${questionIndex + 1} of ${livePack.length}`);
    
    // DIAGNOSTIC: Dump critical state before serving
    console.log(`[STATE_DUMP] ${requestId}`, {
      questionIndex,
      packLength: livePack.length,
      sessionId,
      currentQuestionId: currentQuestion?.id,
      sessionProgress,
      isLoading: loading,
      isPlanning,
      localStorage_keys: Object.keys(localStorage),
      sessionStorage_keys: Object.keys(sessionStorage)
    });
    
    // SURGICAL FIX: Use livePack to avoid stale closure reads
    if (!livePack || livePack.length === 0) {
      console.error(`[DIAGNOSTIC] ${requestId}: CRITICAL - Pack is empty! Cannot serve question.`);
      setError('Session pack is empty. Please refresh to restart.');
      return;
    }
    
    if (questionIndex >= livePack.length) {
      console.log(`[DIAGNOSTIC] ${requestId}: Session completion triggered - ${questionIndex} >= ${livePack.length}`);
      // Session completed - trigger adaptive planning for next session
      handleAdaptiveSessionCompletion();
      return;
    }

    const packItem = livePack[questionIndex];
    console.log(`[DIAGNOSTIC] ${requestId}: Pack item keys:`, Object.keys(packItem));
    
    // V2 FIX: Use actual question data from V2 pack structure
    const question = {
      id: packItem.id,  // Use correct ID field
      stem: packItem.stem || 'Question content unavailable',  // V2: Use correct stem field
      options: {
        a: packItem.option_a || 'Option A',  // V2: Use real options
        b: packItem.option_b || 'Option B',
        c: packItem.option_c || 'Option C', 
        d: packItem.option_d || 'Option D'
      },
      has_image: false,
      subcategory: packItem.subcategory || packItem.pair?.split(':')[0] || 'Unknown',
      difficulty_band: packItem.difficulty_band || packItem.bucket || 'Medium',
      right_answer: packItem.answer || ''  // Use answer field from pack (clean answer)
    };

    console.log(`[DIAGNOSTIC] ${requestId}: Question prepared:`, {
      id: question.id,
      stem_length: question.stem?.length,
      options_keys: Object.keys(question.options),
      real_options: Object.values(question.options).filter(opt => !opt.startsWith('Option '))
    });

    // CRITICAL FIX: Force synchronous state updates to ensure React re-renders
    console.log(`[STATE_UPDATE] ${requestId}: About to set current question: ${question.id}`);
    
    // Clear loading states first to ensure clean state
    setLoading(false);
    setIsPlanning(false);
    setError('');
    
    // Set question and progress together
    setCurrentQuestion(question);
    setSessionProgress({
      current_question: questionIndex + 1,
      total_questions: livePack.length
    });
    
    console.log(`[STATE_UPDATE] ${requestId}: State updates called, waiting for React to process...`);
    
    // CRITICAL: Track session progress for resumption
    updateSessionProgress(questionIndex, question.id);
    
    console.log(`[DIAGNOSTIC] ${requestId}: V2 Adaptive question served successfully: ${question.id} (${questionIndex + 1}/${currentPack.length})`);
    
    // DIAGNOSTIC: Verify state was set correctly with delay to allow React processing
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

  // Session Completion - Updated for Blueprint Sessions
  const finishSession = async () => {
    try {
      console.log(`[SESSION] Finishing session ${sessionId.substring(0, 8)}`);
      
      // Check if this is a Blueprint session
      const isBlueprintSession = sessionMetadata?.session_type === 'blueprint' || 
                                sessionMetadata?.questions?.length > 0;
      
      if (isBlueprintSession) {
        console.log(`[BLUEPRINT] Completing Blueprint session`);
        
        const summary = await completeBlueprintSession(sessionId);
        console.log(`[BLUEPRINT] Session completed with summary:`, summary);
        
        // Show completion UI or navigate back
        if (onSessionEnd) {
          onSessionEnd(summary);
        }
        return;
      }
      
      // Legacy adaptive session completion
      await handleSessionCompletionWithHandshake();
      
    } catch (error) {
      console.error('[SESSION] Error finishing session:', error);
      // Still call onSessionEnd to allow navigation back
      if (onSessionEnd) {
        onSessionEnd(null);
      }
    }
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
      
      // End-of-session handshake: plan next session if blueprint enabled
      if (blueprintEnabled) {
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
      
      // NEW: Trigger pre-warming for next session (fire-and-forget)
      triggerNextSessionPreWarming();
      
    } catch (error) {
      console.error('❌ Session completion handshake failed:', error);
      // Still call session end
      if (onSessionEnd) {
        onSessionEnd(completionData);
      }
      
      // Still try pre-warming even if completion had issues
      triggerNextSessionPreWarming();
    }
  };

  const handleAdaptiveSessionCompletion = async () => {
    const livePack = currentPackRef.current;
    
    // Clear session progress tracking since session is complete
    try {
      await clearSessionProgress(sessionId);
      console.log('[PROGRESS] Session progress cleared after completion');
    } catch (error) {
      console.warn('[PROGRESS] Failed to clear session progress:', error.message);
    }
    
    await handleSessionCompletionWithHandshake({
      completed: true,
      questionsCompleted: livePack?.length || 12,
      totalQuestions: livePack?.length || 12
    });
  };

  // REMOVED: handleLegacyQuestionFlow - System is now adaptive-only

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
      // Check if this is a Blueprint session
      const isBlueprintSession = sessionMetadata?.session_type === 'blueprint' || 
                                sessionMetadata?.questions?.length > 0;
      
      if (isBlueprintSession) {
        console.log(`[CRITICAL_DEBUG] ${requestId}: Submitting to Blueprint session`);
        
        // For Blueprint sessions, use the new submission API
        const currentPosition = (currentQuestionIndex || 0) + 1; // Convert to 1-based position
        
        const blueprintResult = await submitBlueprintAnswer(sessionId, currentPosition, userAnswer);
        
        // Create result object compatible with existing UI
        const result = {
          correct: blueprintResult.is_correct,
          status: blueprintResult.is_correct ? 'correct' : 'incorrect', // FIX: Add status field for UI display
          message: blueprintResult.is_correct ? 'Well done!' : 'Not quite right, but keep learning!',
          correct_answer: blueprintResult.correct_answer,
          explanation: blueprintResult.explanation,
          solution_feedback: blueprintResult.solution_feedback,
          user_answer: userAnswer
        };
        
        setResult(result);
        setShowResult(true);
        console.log(`[CRITICAL_DEBUG] ${requestId}: Blueprint answer submitted successfully`);
        console.log(`[SOLUTION_FEEDBACK_DEBUG] Complete result object:`, result);
        console.log(`[SOLUTION_FEEDBACK_DEBUG] Solution feedback data:`, {
          hasSolutionFeedback: !!result.solution_feedback,
          snapRead: result.solution_feedback?.snap_read?.substring(0, 50),
          approach: result.solution_feedback?.solution_approach?.substring(0, 50),
          detailedSolution: result.solution_feedback?.detailed_solution?.substring(0, 50),
          principle: result.solution_feedback?.principle_to_remember?.substring(0, 50)
        });
        
        // Let user manually control progression - no auto-advance
        console.log(`[BLUEPRINT] ✅ Answer result displayed, waiting for user action`);
        
        return;
      }
      
      // Legacy adaptive session submission
      console.log(`[CRITICAL_DEBUG] ${requestId}: Submitting to legacy adaptive session`);
      
      // DEBUG: Log the payload before sending
      const payload = {
        session_id: sessionId,
        question_id: currentQuestion?.id,
        action: 'submit',
        data: {
          user_answer: userAnswer,
          session_type: blueprintEnabled ? 'blueprint' : 'legacy'
        },
        timestamp: new Date().toISOString()
      };
      
      console.log(`[CRITICAL_DEBUG] ${requestId}: Making submit request with payload:`, payload);
      console.log(`[CRITICAL_DEBUG] ${requestId}: currentQuestion object:`, currentQuestion);
      
      if (!currentQuestion?.id) {
        console.error(`[CRITICAL_DEBUG] ${requestId}: ERROR - currentQuestion.id is missing!`, {
          currentQuestion,
          hasCurrentQuestion: !!currentQuestion,
          questionId: currentQuestion?.id
        });
        setError('Question data is missing. Please refresh to restart the session.');
        return;
      }
      
      // Use fetch for better error control than axios
      const res = await fetch(`${API}/log/question-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`,
          'X-Request-Id': requestId
        },
        body: JSON.stringify(payload)
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
      
      // Check if response contains result data (from enhanced question-action endpoint)
      if (responseData && responseData.result) {
        // Use the result data from backend
        setResult(responseData.result);
        setShowResult(true);
      } else {
        // Fallback: Create adaptive result for display (backward compatibility)
        const isCorrect = userAnswer.toLowerCase() === (currentQuestion.right_answer?.toLowerCase() || 'unknown');
        const result = {
          correct: isCorrect,
          status: isCorrect ? 'correct' : 'incorrect',
          message: isCorrect ? 'Well done!' : 'Not quite right, but keep learning!',
          user_answer: userAnswer,
          correct_answer: currentQuestion.right_answer || 'Not specified',
          explanation: 'Answer logged successfully'
        };
        
        setResult(result);
        setShowResult(true);
      }
      
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
    
    // CRITICAL FIX: Clear previous question's answer state before advancing
    setShowResult(false);
    setResult(null);
    setUserAnswer('');
    setAnswerSubmitted(false);
    
    // ADAPTIVE-ONLY: Advance to next question in pack
    const livePack = currentPackRef.current;
    const nextIndex = currentQuestionIndex + 1;
    console.log(`[CRITICAL_DEBUG] ${requestId}: Advancing to question ${nextIndex + 1} of ${livePack.length}`);
    
    // Validate before advancing using livePack
    if (!livePack || livePack.length === 0) {
      console.error(`[CRITICAL_DEBUG] ${requestId}: No pack data available`);
      setError('Session pack not available. Please refresh to restart.');
      return;
    }
    
    if (nextIndex >= livePack.length) {
      console.log(`[CRITICAL_DEBUG] ${requestId}: Reached end of pack (${nextIndex} >= ${livePack.length}) - completing session`);
      handleAdaptiveSessionCompletion();
      return;
    }
    
    setCurrentQuestionIndex(nextIndex);
    serveQuestionFromPack(nextIndex);
  };

  // Helper function to extract clean answer from MCQ option
  const extractCleanAnswer = (optionText) => {
    if (!optionText) return optionText;
    
    // Remove MCQ prefixes like "(A) ", "(B) ", etc.
    const cleaned = optionText.replace(/^\([A-D]\)\s*/, '').trim();
    return cleaned;
  };

  const handleOptionSelect = (option) => {
    if (!answerSubmitted) {
      // Store the clean answer value (without (A), (B) prefixes)
      const cleanAnswer = extractCleanAnswer(option);
      setUserAnswer(cleanAnswer);
      console.log(`[ANSWER] User selected: "${option}" → Clean answer: "${cleanAnswer}"`);
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

  // Session Progress Tracking Functions
  const updateSessionProgress = async (questionIndex, questionId) => {
    if (!sessionId || !user?.id) return;
    
    try {
      const progressPayload = {
        session_id: sessionId,
        current_question_index: questionIndex,
        total_questions: currentPackRef.current?.length || 12,
        last_question_id: questionId
      };
      
      console.log(`[PROGRESS] Updating session progress with payload:`, progressPayload);
      
      if (!questionId) {
        console.warn('[PROGRESS] Skipping progress update - questionId is missing');
        return;
      }
      
      await axios.post(`${API}/session-progress/update`, progressPayload);
      
      console.log(`[PROGRESS] Updated session progress: Q${questionIndex + 1}/${currentPackRef.current?.length || 12}`);
    } catch (error) {
      console.warn('[PROGRESS] Failed to update session progress:', error.message);
      if (error.response?.status === 422) {
        console.warn('[PROGRESS] 422 error details:', error.response?.data);
      }
      // Don't fail the session flow for progress tracking issues
    }
  };

  const getSessionProgress = async (sessionId) => {
    if (!sessionId || !user?.id) return null;
    
    try {
      const response = await axios.get(`${API}/session-progress/${sessionId}`);
      return response.data.has_progress ? response.data : null;
    } catch (error) {
      console.warn('[PROGRESS] Failed to get session progress:', error.message);
      return null;
    }
  };

  const checkForIncompleteSession = async () => {
    if (!user?.id) return null;
    
    try {
      const response = await axios.get(`${API}/session-progress/current/${user.id}`);
      return response.data.has_current_session ? response.data : null;
    } catch (error) {
      console.warn('[PROGRESS] Failed to check incomplete session:', error.message);
      return null;
    }
  };

  const clearSessionProgress = async (sessionId) => {
    if (!sessionId || !user?.id) return;
    
    try {
      await axios.delete(`${API}/session-progress/${sessionId}`);
      console.log(`[PROGRESS] Cleared session progress: ${sessionId}`);
    } catch (error) {
      console.warn('[PROGRESS] Failed to clear session progress:', error.message);
    }
  };

  const tryFetchPack = async (userId, sessionId) => {
    // SURGICAL FIX: Use the new atomic fetch method
    return await fetchPackSafe(userId, sessionId);
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

  // Enhanced message rendering for Ask Twelvr responses
  const renderEnhancedMessage = (content) => {
    // Check if this is a Mode 3 response (has the structured headings)
    const hasStructuredFormat = content.includes('### What that step is doing') && 
                               content.includes('### The idea behind it') &&
                               content.includes('### Try this (quick practice)');
    
    if (!hasStructuredFormat) {
      return <div className="whitespace-pre-wrap">{content}</div>;
    }
    
    // Parse structured response
    const sections = content.split('###').filter(section => section.trim());
    
    return (
      <div className="space-y-4">
        {sections.map((section, index) => {
          const lines = section.trim().split('\n');
          const heading = lines[0].trim();
          const content = lines.slice(1).join('\n').trim();
          
          // Define section styles
          const getSectionStyle = (heading) => {
            if (heading.includes('What that step is doing')) {
              return { 
                icon: '🔍', 
                bgColor: '#f0f9ff', 
                borderColor: '#0ea5e9',
                headingColor: '#0369a1' 
              };
            } else if (heading.includes('The idea behind it')) {
              return { 
                icon: '💡', 
                bgColor: '#fefce8', 
                borderColor: '#eab308',
                headingColor: '#a16207' 
              };
            } else if (heading.includes('Try this')) {
              return { 
                icon: '🎯', 
                bgColor: '#f0fdf4', 
                borderColor: '#22c55e',
                headingColor: '#15803d' 
              };
            } else if (heading.includes('Solution')) {
              return { 
                icon: '✅', 
                bgColor: '#fafafa', 
                borderColor: '#9ac026',
                headingColor: '#7a8520' 
              };
            } else if (heading.includes('Next')) {
              return { 
                icon: '🚀', 
                bgColor: '#fdf2f8', 
                borderColor: '#ec4899',
                headingColor: '#be185d' 
              };
            }
            return { 
              icon: '📝', 
              bgColor: '#f9fafb', 
              borderColor: '#d1d5db',
              headingColor: '#374151' 
            };
          };
          
          const style = getSectionStyle(heading);
          
          return (
            <div 
              key={index}
              className="border-l-4 p-3 rounded-r-lg"
              style={{ 
                backgroundColor: style.bgColor, 
                borderLeftColor: style.borderColor 
              }}
            >
              <div 
                className="font-semibold text-sm mb-2 flex items-center"
                style={{ color: style.headingColor }}
              >
                <span className="mr-2">{style.icon}</span>
                {heading}
              </div>
              <div 
                className="text-sm whitespace-pre-wrap leading-relaxed"
                style={{ color: '#545454' }}
              >
                {content}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // Doubt conversation functions - Twelvr New Version
  const handleAskDoubt = async () => {
    if (!doubtMessage.trim() || conversationLocked) return;

    // FIXED: Send message first, then open modal with updated history
    const userMessage = doubtMessage.trim();
    setDoubtMessage(''); // Clear input immediately for better UX
    setDoubtLoading(true);
    
    try {
      const response = await axios.post(`${API}/doubts/ask`, {
        question_id: currentQuestion.id,
        session_id: sessionId,
        message: userMessage
      });

      if (response.data.success) {
        // Update local state
        setMessageCount(response.data.message_count);
        setRemainingMessages(response.data.remaining_messages);
        setConversationLocked(response.data.is_locked);
        
        // Load complete conversation history (includes new exchange)
        await loadDoubtHistory();
        
        // NOW open modal with updated history
        setShowDoubtModal(true);
      } else {
        alert(response.data.error || 'Failed to send doubt');
        setDoubtMessage(userMessage); // Restore message on error
      }
    } catch (error) {
      console.error('Error sending doubt:', error);
      alert('Failed to send your doubt. Please try again.');
      setDoubtMessage(userMessage); // Restore message on error
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

  const openDoubtModal = async () => {
    // Load history and open modal to view conversation
    await loadDoubtHistory();
    setShowDoubtModal(true);
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
            {loadingMessage || (isPlanning ? 'Preparing next session...' : 'Loading your session...')}
          </p>
          
          {/* Progress indicator for async preparation */}
          {loadingMessage && loadingMessage.includes('Preparing your session') && (
            <div className="mt-4 w-64 mx-auto">
              <div className="bg-gray-200 rounded-full h-2">
                <div 
                  className="h-2 rounded-full transition-all duration-500" 
                  style={{ 
                    backgroundColor: '#9ac026',
                    width: `${Math.min(parseInt(loadingMessage.match(/\((\d+)s\)/)?.[1] || '0') * 1.67, 100)}%`
                  }}
                ></div>
              </div>
              <p className="text-sm mt-2" style={{ color: '#888', fontFamily: 'Lato, sans-serif' }}>
                Your adaptive session is being prepared...
              </p>
            </div>
          )}
          
          {/* Retry button for failed states */}
          {error && error.includes('preparation failed') && (
            <button 
              onClick={() => window.location.reload()}
              className="mt-4 px-6 py-2 text-white rounded transition-colors"
              style={{ backgroundColor: '#9ac026', fontFamily: 'Lato, sans-serif' }}
            >
              Try Again
            </button>
          )}
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
                    const cleanValue = extractCleanAnswer(value);
                    const isSelected = userAnswer === cleanValue;
                    return (
                      <button
                        key={key}
                        onClick={() => handleOptionSelect(value)}
                        disabled={answerSubmitted}
                        className="w-full text-left p-4 rounded-lg border-2 transition-all"
                        style={{
                          borderColor: isSelected ? '#9ac026' : '#e5e7eb',
                          backgroundColor: isSelected ? '#f7fdf0' : '#ffffff',
                          color: '#545454',
                          fontFamily: 'Lato, sans-serif'
                        }}
                        onMouseOver={(e) => {
                          if (!isSelected && !answerSubmitted) {
                            e.target.style.borderColor = '#ff6d4d';
                            e.target.style.backgroundColor = '#fff5f3';
                          }
                        }}
                        onMouseOut={(e) => {
                          if (!isSelected) {
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
                          content={extractCleanAnswer(value)}
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
                    
                    {/* Snap Read - Display above solution_approach */}
                    {result.solution_feedback.snap_read && (
                      <div className="mb-6">
                        <h5 className="font-semibold mb-3 text-lg" style={{ color: '#545454', fontFamily: 'Manrope, sans-serif' }}>⚡ Snap Read:</h5>
                        <div className="bg-white p-4 rounded-lg border" style={{ borderColor: '#e8f5e8' }}>
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
                {result.solution_feedback && currentQuestion && !showDoubtModal && (
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
                          {messageCount > 0 && (
                            conversationLocked ? (
                              <span style={{ color: '#ff6d4d' }} className="font-medium">❌ Conversation limit reached (10/10)</span>
                            ) : (
                              <span>💬 Messages used: {messageCount}/10</span>
                            )
                          )}
                        </div>
                        <div className="flex space-x-2">
                          {messageCount > 0 && (
                            <button
                              onClick={openDoubtModal}
                              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md focus:outline-none focus:ring-2 transition-colors"
                              style={{ 
                                fontFamily: 'Lato, sans-serif'
                              }}
                              onMouseOver={(e) => {
                                e.target.style.backgroundColor = '#f3f4f6';
                              }}
                              onMouseOut={(e) => {
                                e.target.style.backgroundColor = 'transparent';
                              }}
                            >
                              📖 View Conversation
                            </button>
                          )}
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

      {/* Pre-Session Insight Modal */}
      {showPreSessionModal && preSessionInsight && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="text-center mb-4">
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                {preSessionInsight.title}
              </h2>
            </div>
            
            <div className="space-y-4 mb-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-blue-800 text-sm">
                  {preSessionInsight.progress}
                </p>
              </div>
              
              {preSessionInsight.way_forward && preSessionInsight.way_forward.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-green-800 text-sm font-medium mb-2">Way Forward:</p>
                  <ul className="text-green-700 text-sm space-y-1">
                    {preSessionInsight.way_forward.map((item, index) => (
                      <li key={index}>• {item}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <p className="text-yellow-800 text-sm">
                  <strong>Today:</strong> {preSessionInsight.today}
                </p>
              </div>
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={() => {
                  setShowPreSessionModal(false);
                  // Don't start session - just dismiss modal
                }}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowPreSessionModal(false);
                  // Session will continue loading automatically
                }}
                className="flex-1 px-4 py-2 bg-[#9ac026] text-white rounded-lg hover:bg-[#8bb024]"
              >
                Start Session
              </button>
            </div>
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
                      <div className={`${message.role === 'user' ? '' : ''}`} style={{ 
                        color: message.role === 'user' ? 'white' : '#545454',
                        fontFamily: 'Lato, sans-serif' 
                      }}>
                        {message.role === 'assistant' ? 
                          renderEnhancedMessage(message.content) : 
                          <div className="whitespace-pre-wrap">{message.content}</div>
                        }
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