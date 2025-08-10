import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Components
const Login = ({ onLogin }) => {
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [isRegister, setIsRegister] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const endpoint = isRegister ? "/register" : "/login";
      const response = await axios.post(`${API}${endpoint}`, formData);
      
      if (isRegister) {
        alert("Registration successful! Please login.");
        setIsRegister(false);
      } else {
        onLogin(response.data.user);
      }
    } catch (error) {
      alert(error.response?.data?.detail || "Authentication failed");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900">
            CAT Preparation Platform
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {isRegister ? "Create your account" : "Sign in to your account"}
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {isRegister && (
            <input
              type="text"
              placeholder="Full Name"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              required
            />
          )}
          <input
            type="email"
            placeholder="Email"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            required
          />
          <input
            type="password"
            placeholder="Password"
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            required
          />
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            {isRegister ? "Register" : "Sign In"}
          </button>
          <button
            type="button"
            onClick={() => setIsRegister(!isRegister)}
            className="w-full text-center text-sm text-blue-600 hover:text-blue-500"
          >
            {isRegister ? "Already have an account? Sign in" : "Need an account? Register"}
          </button>
        </form>
      </div>
    </div>
  );
};

const Dashboard = ({ user, onLogout }) => {
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
              <h1 className="text-xl font-semibold">CAT Prep Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-700">Welcome, {user.name}</span>
              <button
                onClick={onLogout}
                className="text-sm bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {/* Study Plan Section */}
        <div className="bg-white overflow-hidden shadow rounded-lg mb-6">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">90-Day Study Plan</h3>
            {studyPlan.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-gray-500 mb-4">No study plan generated yet</p>
                <button
                  onClick={generateStudyPlan}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
                >
                  Generate Study Plan
                </button>
              </div>
            ) : (
              <div className="space-y-2">
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

const Practice = ({ user }) => {
  const [taxonomy, setTaxonomy] = useState({});
  const [questions, setQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedSubCategory, setSelectedSubCategory] = useState("");
  const [userAnswer, setUserAnswer] = useState("");
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);

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
        time_taken: 120 // Placeholder
      };

      const response = await axios.post(`${API}/progress`, progressData);
      setResult(response.data);
      setShowResult(true);
    } catch (error) {
      console.error("Error submitting answer:", error);
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

const AdminPanel = ({ user }) => {
  const [questions, setQuestions] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [taxonomy, setTaxonomy] = useState({});
  const [questionForm, setQuestionForm] = useState({
    text: "",
    options: ["", "", "", ""],
    correct_answer: "",
    explanation: "",
    category: "",
    sub_category: "",
    year: new Date().getFullYear()
  });

  useEffect(() => {
    fetchQuestions();
    fetchTaxonomy();
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
      const response = await axios.post(`${API}/upload-pyq`, formData, {
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
          <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md"
          >
            {showForm ? "Cancel" : "Add Question"}
          </button>
        </div>

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
          <div className="divide-y divide-gray-200">
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

// Main App
const App = () => {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState("dashboard");

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    setUser(null);
    setCurrentView("dashboard");
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="App">
      <BrowserRouter>
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex space-x-8">
                <button
                  onClick={() => setCurrentView("dashboard")}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                    currentView === "dashboard" ? "text-blue-600 border-b-2 border-blue-500" : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setCurrentView("practice")}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                    currentView === "practice" ? "text-blue-600 border-b-2 border-blue-500" : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  Practice
                </button>
                {user.is_admin && (
                  <button
                    onClick={() => setCurrentView("admin")}
                    className={`inline-flex items-center px-1 pt-1 text-sm font-medium ${
                      currentView === "admin" ? "text-blue-600 border-b-2 border-blue-500" : "text-gray-500 hover:text-gray-700"
                    }`}
                  >
                    Admin
                  </button>
                )}
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-gray-700">Welcome, {user.name}</span>
                <button
                  onClick={handleLogout}
                  className="text-sm bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* Content */}
        {currentView === "dashboard" && <Dashboard user={user} onLogout={handleLogout} />}
        {currentView === "practice" && <Practice user={user} />}
        {currentView === "admin" && user.is_admin && <AdminPanel user={user} />}
      </BrowserRouter>
    </div>
  );
};

export default App;