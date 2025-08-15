import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Utility function to get backend URL (same as in Dashboard)
const getBackendURL = () => {
  if (process.env.REACT_APP_BACKEND_URL && process.env.REACT_APP_BACKEND_URL.trim()) {
    return process.env.REACT_APP_BACKEND_URL;
  }
  
  const currentDomain = window.location.hostname;
  
  if (currentDomain === 'localhost' || currentDomain === '127.0.0.1') {
    return 'http://localhost:8001';
  } else if (currentDomain === 'twelvr.com' || currentDomain.includes('twelvr')) {
    return 'https://adaptive-quant.emergent.host';
  } else if (currentDomain.includes('preview.emergentagent.com')) {
    return '';
  } else {
    return '';
  }
};

const BACKEND_URL = getBackendURL();
const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

const PYQFilesTable = ({ onFileUploaded }) => {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchUploadedFiles = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/admin/pyq/uploaded-files`);
      setUploadedFiles(response.data.files || []);
    } catch (err) {
      console.error('Error fetching uploaded files:', err);
    } finally {
      setLoading(false);
    }
  };

  const downloadFile = async (fileId, filename) => {
    try {
      const response = await axios.get(`${API}/admin/pyq/download-file/${fileId}`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      console.log(`Downloaded: ${filename}`);
    } catch (err) {
      console.error('Error downloading file:', err);
      alert('Failed to download file');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid Date';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Load files on component mount
  useEffect(() => {
    fetchUploadedFiles();
  }, []);

  // Refresh when new file is uploaded
  useEffect(() => {
    if (onFileUploaded) {
      fetchUploadedFiles();
    }
  }, [onFileUploaded]);

  return (
    <div className="mb-8">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">📋 Uploaded PYQ Files</h3>
            <button
              onClick={fetchUploadedFiles}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Loading...
                </>
              ) : (
                <>
                  🔄 Refresh
                </>
              )}
            </button>
          </div>
        </div>

        <div className="overflow-hidden">
          {loading && uploadedFiles.length === 0 ? (
            <div className="text-center py-12">
              <svg className="animate-spin h-8 w-8 text-gray-400 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="text-gray-500">Loading uploaded files...</p>
            </div>
          ) : uploadedFiles.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">📄</div>
              <h4 className="text-lg font-medium text-gray-900 mb-2">No Files Uploaded Yet</h4>
              <p className="text-gray-500">Upload your first PYQ CSV file to see it listed here.</p>
            </div>
          ) : (
            <div className="max-h-96 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      File Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Upload Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Questions
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Years
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Uploaded By
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {uploadedFiles.map((file) => (
                    <tr key={file.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="text-sm font-medium text-gray-900">
                            📄 {file.filename}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {formatDate(file.upload_date)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {file.questions_created} questions
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {file.years_processed && file.years_processed.length > 0 
                            ? file.years_processed.join(', ')
                            : file.year || 'Mixed'
                          }
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatFileSize(file.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {file.uploaded_by || 'Unknown'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => downloadFile(file.id, file.filename)}
                          className="text-blue-600 hover:text-blue-900 font-medium hover:underline flex items-center ml-auto"
                          title={`Download ${file.filename}`}
                        >
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                          Download
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {uploadedFiles.length > 0 && (
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-700 rounded-b-lg">
            Total: {uploadedFiles.length} file{uploadedFiles.length !== 1 ? 's' : ''} uploaded
            {uploadedFiles.reduce((sum, file) => sum + (file.questions_created || 0), 0) > 0 && (
              <span className="ml-2 text-gray-500">
                • {uploadedFiles.reduce((sum, file) => sum + (file.questions_created || 0), 0)} total questions
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PYQFilesTable;