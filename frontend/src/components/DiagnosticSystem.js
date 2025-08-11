import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from './AuthProvider';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const DiagnosticSystem = () => {
  const { user } = useAuth();
  const [phase, setPhase] = useState('intro'); // intro, taking, completed, results
  const [diagnosticId, setDiagnosticId] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [timeSpent, setTimeSpent] = useState({});
  const [startTime, setStartTime] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const startDiagnostic = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.post(`${API}/diagnostic/start`, {});
      const { diagnostic_id } = response.data;
      setDiagnosticId(diagnostic_id);
      
      // Fetch questions
      const questionsResponse = await axios.get(`${API}/diagnostic/${diagnostic_id}/questions`);
      setQuestions(questionsResponse.data.questions);
      setPhase('taking');
      setStartTime(Date.now());
    } catch (err) {
      setError('Failed to start diagnostic. Please try again.');
      console.error('Diagnostic start error:', err);
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async (questionId, answer) => {
    try {
      const timeForQuestion = Date.now() - startTime;
      await axios.post(`${API}/diagnostic/submit-answer`, {
        diagnostic_id: diagnosticId,
        question_id: questionId,
        user_answer: answer,
        time_sec: Math.round(timeForQuestion / 1000),
        context: 'diagnostic',
        hint_used: false
      });

      setAnswers(prev => ({ ...prev, [questionId]: answer }));
      setTimeSpent(prev => ({ ...prev, [questionId]: timeForQuestion }));
    } catch (err) {
      console.error('Answer submission error:', err);
    }
  };

  const nextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setStartTime(Date.now());
    } else {
      completeDiagnostic();
    }
  };

  const completeDiagnostic = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/diagnostic/${diagnosticId}/complete`, {});
      setResults(response.data);
      setPhase('results');
    } catch (err) {
      setError('Failed to complete diagnostic. Please contact support.');
      console.error('Diagnostic completion error:', err);
    } finally {
      setLoading(false);
    }
  };

  const resetDiagnostic = () => {
    setPhase('intro');
    setDiagnosticId(null);
    setQuestions([]);
    setCurrentQuestionIndex(0);
    setAnswers({});
    setTimeSpent({});
    setResults(null);
    setError('');
  };

  if (phase === 'intro') {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-8">
            <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
              <svg className="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">CAT Diagnostic Assessment</h1>
            <p className="text-lg text-gray-600 mb-6">
              Take our comprehensive 25-question diagnostic to assess your current preparation level
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div className="bg-blue-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-blue-900 mb-3">📊 What You'll Get</h3>
              <ul className="space-y-2 text-blue-800">
                <li>• Detailed capability scoring across all topics</li>
                <li>• Personalized 90-day study plan</li>
                <li>• Strength and weakness analysis</li>
                <li>• Recommended learning path</li>
              </ul>
            </div>
            <div className="bg-green-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-green-900 mb-3">⏱️ Test Details</h3>
              <ul className="space-y-2 text-green-800">
                <li>• 25 carefully selected questions</li>
                <li>• Covers all 5 major CAT topics</li>
                <li>• Adaptive difficulty levels</li>
                <li>• No time pressure - take your time</li>
              </ul>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          <div className="text-center">
            <button
              onClick={startDiagnostic}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-8 py-3 rounded-lg text-lg font-semibold transition-colors"
            >
              {loading ? 'Starting...' : 'Begin Diagnostic Assessment'}
            </button>
            <p className="text-sm text-gray-500 mt-3">
              This assessment will help create your personalized study plan
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (phase === 'taking' && questions.length > 0) {
    const currentQuestion = questions[currentQuestionIndex];
    const progress = ((currentQuestionIndex + 1) / questions.length) * 100;

    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Question {currentQuestionIndex + 1} of {questions.length}</span>
              <span>{Math.round(progress)}% Complete</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>

          {/* Question */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                {currentQuestion.category}
              </span>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                currentQuestion.difficulty_band === 'Easy' ? 'bg-green-100 text-green-800' :
                currentQuestion.difficulty_band === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {currentQuestion.difficulty_band}
              </span>
              <span className="text-sm text-gray-500">
                Expected Time: {Math.round(currentQuestion.expected_time_sec / 60)} mins
              </span>
            </div>

            <h2 className="text-xl font-medium text-gray-900 mb-6 leading-relaxed">
              {currentQuestion.stem}
            </h2>

            {/* MCQ Options */}
            {currentQuestion.options && (
              <div className="space-y-3">
                {Object.entries(currentQuestion.options).filter(([key]) => key !== 'correct').map(([key, value]) => (
                  <button
                    key={key}
                    onClick={() => submitAnswer(currentQuestion.id, key)}
                    className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                      answers[currentQuestion.id] === key
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                    }`}
                  >
                    <div className="flex items-start">
                      <span className="font-semibold text-blue-600 mr-3">{key}.</span>
                      <span className="text-gray-900">{value}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex justify-between items-center pt-6 border-t">
            <div className="text-sm text-gray-500">
              {answers[currentQuestion.id] ? 'Answer recorded' : 'Select an answer to continue'}
            </div>
            <button
              onClick={nextQuestion}
              disabled={!answers[currentQuestion.id]}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-medium transition-colors"
            >
              {currentQuestionIndex === questions.length - 1 ? 'Complete Assessment' : 'Next Question'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (phase === 'results' && results) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-8">
            <div className="mx-auto h-16 w-16 bg-green-600 rounded-full flex items-center justify-center mb-4">
              <svg className="h-10 w-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Diagnostic Complete!</h1>
            <p className="text-lg text-gray-600">Here's your comprehensive assessment report</p>
          </div>

          {/* Overall Score */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div className="bg-blue-50 p-6 rounded-lg text-center">
              <div className="text-3xl font-bold text-blue-600">{results.overall_accuracy || 0}%</div>
              <div className="text-sm text-blue-600">Overall Accuracy</div>
            </div>
            <div className="bg-green-50 p-6 rounded-lg text-center">
              <div className="text-3xl font-bold text-green-600">{results.speed_score || 0}</div>
              <div className="text-sm text-green-600">Speed Score</div>
            </div>
            <div className="bg-purple-50 p-6 rounded-lg text-center">
              <div className="text-3xl font-bold text-purple-600">{results.stability_score || 0}</div>
              <div className="text-sm text-purple-600">Stability Score</div>
            </div>
          </div>

          {/* Category Performance */}
          {results.category_performance && (
            <div className="mb-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Category Performance</h3>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(results.category_performance).map(([category, performance]) => (
                  <div key={category} className="bg-gray-50 p-4 rounded-lg">
                    <div className="font-medium text-gray-900">{category}</div>
                    <div className={`text-lg font-bold ${
                      performance.accuracy > 70 ? 'text-green-600' :
                      performance.accuracy > 50 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {performance.accuracy}% ({performance.correct}/{performance.total})
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {results.recommendations && (
            <div className="mb-8">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">Recommendations</h3>
              <div className="bg-yellow-50 p-6 rounded-lg">
                <div className="text-gray-800">
                  <p><strong>Study Track:</strong> {results.recommended_track || 'Beginner'}</p>
                  <p className="mt-2"><strong>Focus Areas:</strong> {results.focus_areas?.join(', ') || 'Will be determined in your study plan'}</p>
                  <p className="mt-2"><strong>Next Steps:</strong> Generate your personalized 90-day study plan to begin targeted preparation</p>
                </div>
              </div>
            </div>
          )}

          <div className="text-center">
            <button
              onClick={() => window.location.reload()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg text-lg font-semibold transition-colors mr-4"
            >
              Go to Study Plan
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="bg-white rounded-lg shadow-lg p-8 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading diagnostic assessment...</p>
      </div>
    </div>
  );
};