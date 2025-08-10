import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import "./App.css";
import { AuthProvider, useAuth } from "./components/AuthProvider";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Professional Login Component
const Login = () => {
  const [formData, setFormData] = useState({ email: "", password: "", name: "" });
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPasswordReset, setShowPasswordReset] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetMessage, setResetMessage] = useState("");

  const { login, register, requestPasswordReset } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      let result;
      if (isRegister) {
        result = await register(formData.name, formData.email, formData.password);
      } else {
        result = await login(formData.email, formData.password);
      }

      if (!result.success) {
        setError(result.error);
      }
    } catch (error) {
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordReset = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResetMessage("");

    const result = await requestPasswordReset(resetEmail);
    if (result.success) {
      setResetMessage(result.message);
      setShowPasswordReset(false);
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  if (showPasswordReset) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
        <div className="max-w-md w-full">
          <div className="bg-white rounded-lg shadow-xl p-8">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900">Reset Password</h2>
              <p className="mt-2 text-sm text-gray-600">
                Enter your email to receive reset instructions
              </p>
            </div>

            <form onSubmit={handlePasswordReset} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? "Sending..." : "Send Reset Email"}
              </button>

              <button
                type="button"
                onClick={() => setShowPasswordReset(false)}
                className="w-full text-center text-sm text-blue-600 hover:text-blue-500"
              >
                Back to Login
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="text-center mb-8">
            <div className="mx-auto h-12 w-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
              <svg className="h-8 w-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold text-gray-900">CAT Preparation Platform</h2>
            <p className="mt-2 text-sm text-gray-600">
              {isRegister ? "Create your account" : "Sign in to your account"}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-gray-700">Full Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Password</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
                minLength="6"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            {resetMessage && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                {resetMessage}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? "Please wait..." : (isRegister ? "Create Account" : "Sign In")}
            </button>

            <div className="text-center space-y-2">
              <button
                type="button"
                onClick={() => setIsRegister(!isRegister)}
                className="text-sm text-blue-600 hover:text-blue-500"
              >
                {isRegister ? "Already have an account? Sign in" : "Need an account? Register"}
              </button>
              
              {!isRegister && (
                <div>
                  <button
                    type="button"
                    onClick={() => setShowPasswordReset(true)}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Forgot your password?
                  </button>
                </div>
              )}
            </div>

            {/* Admin Info */}
            <div className="mt-6 p-3 bg-blue-50 rounded-md">
              <p className="text-xs text-blue-700">
                <strong>Admin access:</strong> sumedhprabhu18@gmail.com
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && !isAdmin()) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900">Access Denied</h2>
          <p className="mt-2 text-gray-600">You need admin privileges to access this page.</p>
        </div>
      </div>
    );
  }

  return children;
};

// Dashboard Component
const Dashboard = () => {
  const { user, logout } = useAuth();
  const [analytics, setAnalytics] = useState(null);
  const [studyPlan, setStudyPlan] = useState([]);

  useEffect(() => {
    fetchAnalytics();
    fetchStudyPlan();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API}/analytics/${user.id}`);
      setAnalytics(response.data);
    } catch (error) {
      console.error("Error fetching analytics:", error);
    }
  };

  const fetchStudyPlan = async () => {
    try {
      const response = await axios.get(`${API}/study-plan/${user.id}`);
      setStudyPlan(response.data.study_plans || []);
    } catch (error) {
      console.error("Error fetching study plan:", error);
    }
  };

  const generateStudyPlan = async () => {
    try {
      await axios.post(`${API}/study-plan/${user.id}`);
      alert("90-day study plan generated successfully!");
      fetchStudyPlan();
    } catch (error) {
      alert("Error generating study plan");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">CAT Prep Dashboard</h1>
              {user.is_admin && (
                <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Admin
                </span>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-700">
                <span className="font-medium">{user.name}</span>
                {user.email_verified && (
                  <span className="ml-2 text-green-600">✓</span>
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

      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Welcome back, {user.name}!</h2>
          <p className="mt-1 text-sm text-gray-600">
            Track your progress and continue your CAT preparation journey.
          </p>
        </div>

        {/* Study Plan Section */}
        <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">90-Day Study Plan</h3>
            {studyPlan.length === 0 ? (
              <div className="text-center py-6">
                <div className="mx-auto h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                  <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
                <p className="text-gray-500 mb-4">No study plan generated yet</p>
                <button
                  onClick={generateStudyPlan}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
                >
                  Generate Study Plan
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Your personalized 90-day journey to CAT success
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">{studyPlan.length}</div>
                    <div className="text-sm text-blue-600">Days Planned</div>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {studyPlan.filter(p => p.completed_questions.length > 0).length}
                    </div>
                    <div className="text-sm text-green-600">Days Completed</div>
                  </div>
                  <div className="bg-yellow-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-600">
                      {Math.round((studyPlan.filter(p => p.completed_questions.length > 0).length / studyPlan.length) * 100)}%
                    </div>
                    <div className="text-sm text-yellow-600">Progress</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Analytics Section */}
        {analytics && (
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Performance Analytics</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-md font-medium text-gray-700 mb-2">Overall Stats</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Total Questions:</span>
                      <span className="font-semibold">{analytics.total_questions_attempted}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Overall Accuracy:</span>
                      <span className="font-semibold text-green-600">{analytics.overall_accuracy}%</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="text-md font-medium text-gray-700 mb-2">Category Performance</h4>
                  <div className="space-y-2">
                    {Object.entries(analytics.category_performance || {}).map(([category, stats]) => (
                      <div key={category} className="flex justify-between text-sm">
                        <span className="truncate">{category}:</span>
                        <span className={`font-semibold ${stats.accuracy > 70 ? 'text-green-600' : stats.accuracy > 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {stats.accuracy}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Practice Component (keeping existing functionality)
const Practice = () => {
  const [taxonomy, setTaxonomy] = useState({});
  const [questions, setQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedSubCategory, setSelectedSubCategory] = useState("");
  const [userAnswer, setUserAnswer] = useState("");
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);

  const { user } = useAuth();

  useEffect(() => {
    fetchTaxonomy();
  }, []);

  const fetchTaxonomy = async () => {
    try {
      const response = await axios.get(`${API}/taxonomy`);
      setTaxonomy(response.data.taxonomy);
    } catch (error) {
      console.error("Error fetching taxonomy:", error);
    }
  };

  const fetchQuestions = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedCategory) params.append("category", selectedCategory);
      if (selectedSubCategory) params.append("sub_category", selectedSubCategory);
      
      const response = await axios.get(`${API}/questions?${params.toString()}`);
      setQuestions(response.data.questions);
      if (response.data.questions.length > 0) {
        setCurrentQuestion(response.data.questions[0]);
      }
    } catch (error) {
      console.error("Error fetching questions:", error);
    }
  };

  const submitAnswer = async () => {
    if (!userAnswer) {
      alert("Please select an answer");
      return;
    }

    try {
      const progressData = {
        user_id: user.id,
        question_id: currentQuestion.id,
        user_answer: userAnswer,
        time_taken: 120
      };

      const response = await axios.post(`${API}/progress`, progressData);
      setResult(response.data);
      setShowResult(true);
    } catch (error) {
      console.error("Error submitting answer:", error);
      alert("Error submitting answer");
    }
  };

  const nextQuestion = () => {
    const currentIndex = questions.findIndex(q => q.id === currentQuestion.id);
    if (currentIndex < questions.length - 1) {
      setCurrentQuestion(questions[currentIndex + 1]);
      setUserAnswer("");
      setShowResult(false);
      setResult(null);
    } else {
      alert("You've completed all questions in this category!");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-8">Practice Questions</h1>

        {/* Category Selection */}
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-lg font-medium mb-4">Select Category</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setSelectedSubCategory("");
              }}
              className="border border-gray-300 rounded-md px-3 py-2"
            >
              <option value="">Select Category</option>
              {Object.keys(taxonomy).map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
            
            {selectedCategory && (
              <select
                value={selectedSubCategory}
                onChange={(e) => setSelectedSubCategory(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2"
              >
                <option value="">Select Sub-Category</option>
                {Object.keys(taxonomy[selectedCategory] || {}).map(subCat => (
                  <option key={subCat} value={subCat}>{subCat}</option>
                ))}
              </select>
            )}
          </div>
          
          <button
            onClick={fetchQuestions}
            disabled={!selectedCategory}
            className="mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-md"
          >
            Load Questions
          </button>
        </div>

        {/* Question Display */}
        {currentQuestion && (
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="mb-4">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {currentQuestion.category} → {currentQuestion.sub_category}
              </span>
              <span className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                currentQuestion.difficulty_level === 'Easy' ? 'bg-green-100 text-green-800' :
                currentQuestion.difficulty_level === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {currentQuestion.difficulty_level}
              </span>
            </div>

            <h3 className="text-lg font-medium mb-4">{currentQuestion.text}</h3>

            {currentQuestion.options && (
              <div className="space-y-2 mb-6">
                {currentQuestion.options.map((option, index) => (
                  <label key={index} className="flex items-center">
                    <input
                      type="radio"
                      name="answer"
                      value={option}
                      checked={userAnswer === option}
                      onChange={(e) => setUserAnswer(e.target.value)}
                      className="mr-2"
                      disabled={showResult}
                    />
                    <span className={showResult && option === currentQuestion.correct_answer ? 'text-green-600 font-semibold' : ''}>
                      {option}
                    </span>
                  </label>
                ))}
              </div>
            )}

            {!currentQuestion.options && (
              <div className="mb-6">
                <input
                  type="text"
                  placeholder="Enter your answer"
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  disabled={showResult}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                />
              </div>
            )}

            {showResult && result && (
              <div className={`p-4 rounded-md mb-4 ${result.is_correct ? 'bg-green-50' : 'bg-red-50'}`}>
                <p className={`font-medium ${result.is_correct ? 'text-green-800' : 'text-red-800'}`}>
                  {result.is_correct ? '✓ Correct!' : '✗ Incorrect'}
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  Correct Answer: {result.correct_answer}
                </p>
                {result.explanation && (
                  <p className="text-sm text-gray-600 mt-2">
                    <strong>Explanation:</strong> {result.explanation}
                  </p>
                )}
              </div>
            )}

            <div className="flex gap-4">
              {!showResult ? (
                <button
                  onClick={submitAnswer}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md"
                >
                  Submit Answer
                </button>
              ) : (
                <button
                  onClick={nextQuestion}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md"
                >
                  Next Question
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Admin Panel Component
const AdminPanel = () => {
  const [questions, setQuestions] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [taxonomy, setTaxonomy] = useState({});
  const [stats, setStats] = useState(null);
  const [questionForm, setQuestionForm] = useState({
    text: "",
    options: ["", "", "", ""],
    correct_answer: "",
    explanation: "",
    category: "",
    sub_category: "",
    year: new Date().getFullYear()
  });

  const { user } = useAuth();

  useEffect(() => {
    fetchQuestions();
    fetchTaxonomy();
    fetchStats();
  }, []);

  const fetchQuestions = async () => {
    try {
      const response = await axios.get(`${API}/questions`);
      setQuestions(response.data.questions);
    } catch (error) {
      console.error("Error fetching questions:", error);
    }
  };

  const fetchTaxonomy = async () => {
    try {
      const response = await axios.get(`${API}/taxonomy`);
      setTaxonomy(response.data.taxonomy);
    } catch (error) {
      console.error("Error fetching taxonomy:", error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/admin/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/questions`, questionForm);
      alert("Question created successfully!");
      setShowForm(false);
      fetchQuestions();
      setQuestionForm({
        text: "",
        options: ["", "", "", ""],
        correct_answer: "",
        explanation: "",
        category: "",
        sub_category: "",
        year: new Date().getFullYear()
      });
    } catch (error) {
      alert("Error creating question: " + error.response?.data?.detail);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("year", "2024");

    try {
      const response = await axios.post(`${API}/admin/upload-pyq`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      alert(response.data.message);
      fetchQuestions();
    } catch (error) {
      alert("Error uploading PYQ: " + error.response?.data?.detail);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
            <p className="text-sm text-gray-600">Welcome, {user.name} (Admin)</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
          >
            {showForm ? "Cancel" : "Add Question"}
          </button>
        </div>

        {/* Admin Stats */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-2xl font-bold text-blue-600">{stats.total_users}</div>
              <div className="text-sm text-gray-600">Total Users</div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-2xl font-bold text-green-600">{stats.total_questions}</div>
              <div className="text-sm text-gray-600">Total Questions</div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-2xl font-bold text-purple-600">{stats.total_attempts}</div>
              <div className="text-sm text-gray-600">Total Attempts</div>
            </div>
          </div>
        )}

        {/* PYQ Upload */}
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-lg font-medium mb-4">Upload PYQ (Word Document)</h2>
          <input
            type="file"
            accept=".docx,.doc"
            onChange={handleFileUpload}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>

        {/* Question Form */}
        {showForm && (
          <div className="bg-white p-6 rounded-lg shadow mb-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Question Text</label>
                <textarea
                  value={questionForm.text}
                  onChange={(e) => setQuestionForm({...questionForm, text: e.target.value})}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                  rows="4"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Category</label>
                  <select
                    value={questionForm.category}
                    onChange={(e) => setQuestionForm({...questionForm, category: e.target.value, sub_category: ""})}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                    required
                  >
                    <option value="">Select Category</option>
                    {Object.keys(taxonomy).map(category => (
                      <option key={category} value={category}>{category}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Sub-Category</label>
                  <select
                    value={questionForm.sub_category}
                    onChange={(e) => setQuestionForm({...questionForm, sub_category: e.target.value})}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                    required
                  >
                    <option value="">Select Sub-Category</option>
                    {questionForm.category && Object.keys(taxonomy[questionForm.category] || {}).map(subCat => (
                      <option key={subCat} value={subCat}>{subCat}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Options (leave blank for NAT type)</label>
                {questionForm.options.map((option, index) => (
                  <input
                    key={index}
                    type="text"
                    placeholder={`Option ${index + 1}`}
                    value={option}
                    onChange={(e) => {
                      const newOptions = [...questionForm.options];
                      newOptions[index] = e.target.value;
                      setQuestionForm({...questionForm, options: newOptions});
                    }}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                  />
                ))}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Correct Answer</label>
                <input
                  type="text"
                  value={questionForm.correct_answer}
                  onChange={(e) => setQuestionForm({...questionForm, correct_answer: e.target.value})}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Explanation</label>
                <textarea
                  value={questionForm.explanation}
                  onChange={(e) => setQuestionForm({...questionForm, explanation: e.target.value})}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2"
                  rows="3"
                />
              </div>

              <button
                type="submit"
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md"
              >
                Create Question
              </button>
            </form>
          </div>
        )}

        {/* Questions List */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b">
            <h2 className="text-lg font-medium">Questions ({questions.length})</h2>
          </div>
          <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
            {questions.map((question, index) => (
              <div key={question.id} className="px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-2">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {question.category}
                      </span>
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {question.sub_category}
                      </span>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        question.difficulty_level === 'Easy' ? 'bg-green-100 text-green-800' :
                        question.difficulty_level === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {question.difficulty_level}
                      </span>
                    </div>
                    <p className="text-sm text-gray-900 mb-1">{question.text}</p>
                    <p className="text-xs text-gray-500">
                      Correct Answer: {question.correct_answer} | Type: {question.question_type}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Navigation Component
const Navigation = () => {
  const { user, logout, isAdmin } = useAuth();
  const [currentView, setCurrentView] = useState("dashboard");

  const navItems = [
    { key: "dashboard", label: "Dashboard", icon: "🏠" },
    { key: "practice", label: "Practice", icon: "📝" },
  ];

  if (isAdmin()) {
    navItems.push({ key: "admin", label: "Admin", icon: "⚙️" });
  }

  return (
    <>
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex space-x-8">
              {navItems.map((item) => (
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

      {/* Content */}
      {currentView === "dashboard" && <Dashboard />}
      {currentView === "practice" && <Practice />}
      {currentView === "admin" && isAdmin() && <AdminPanel />}
    </>
  );
};

// Main App Component
const AppContent = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return <Login />;
  }

  return <Navigation />;
};

// Root App Component
function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;