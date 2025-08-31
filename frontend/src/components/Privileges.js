import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from './AuthProvider';

const Privileges = () => {
  const [privilegedEmails, setPrivilegedEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newEmail, setNewEmail] = useState('');
  const [newNotes, setNewNotes] = useState('');
  const [addingEmail, setAddingEmail] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchPrivilegedEmails();
  }, []);

  const fetchPrivilegedEmails = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/admin/privileges`);
      setPrivilegedEmails(response.data.privileged_emails || []);
    } catch (error) {
      console.error('Error fetching privileged emails:', error);
      setError('Failed to fetch privileged emails');
    } finally {
      setLoading(false);
    }
  };

  const handleAddEmail = async (e) => {
    e.preventDefault();
    
    if (!newEmail.trim()) {
      setError('Email address is required');
      return;
    }

    try {
      setAddingEmail(true);
      setError('');
      
      const response = await axios.post(`${API}/admin/privileges`, {
        email: newEmail.trim(),
        notes: newNotes.trim()
      });

      setSuccess(`Email ${newEmail} successfully added to privileged list`);
      setNewEmail('');
      setNewNotes('');
      
      // Refresh the list
      await fetchPrivilegedEmails();
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(''), 3000);
      
    } catch (error) {
      console.error('Error adding email:', error);
      setError(error.response?.data?.detail || 'Failed to add email');
    } finally {
      setAddingEmail(false);
    }
  };

  const handleRemoveEmail = async (emailId, emailAddress) => {
    if (!window.confirm(`Are you sure you want to remove "${emailAddress}" from the privileged list?`)) {
      return;
    }

    try {
      await axios.delete(`${API}/admin/privileges/${emailId}`);
      setSuccess(`Email ${emailAddress} successfully removed from privileged list`);
      
      // Refresh the list
      await fetchPrivilegedEmails();
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(''), 3000);
      
    } catch (error) {
      console.error('Error removing email:', error);
      setError(error.response?.data?.detail || 'Failed to remove email');
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#9ac026]"></div>
        <span className="ml-3 text-[#545454]">Loading privileged emails...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-2xl font-bold text-[#545454] mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
          🔐 Email Privileges Management
        </h2>
        <p className="text-gray-600" style={{ fontFamily: 'Lato, sans-serif' }}>
          Manage email addresses that bypass the 15-session free trial limit. Privileged users have unlimited session access.
        </p>
      </div>

      {/* Success/Error Messages */}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg">
          <div className="flex items-center">
            <svg className="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span style={{ fontFamily: 'Lato, sans-serif' }}>{success}</span>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
          <div className="flex items-center">
            <svg className="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span style={{ fontFamily: 'Lato, sans-serif' }}>{error}</span>
          </div>
        </div>
      )}

      {/* Add New Email Form */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-[#545454] mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
          Add New Privileged Email
        </h3>
        
        <form onSubmit={handleAddEmail} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#545454] mb-2" style={{ fontFamily: 'Lato, sans-serif' }}>
              Email Address *
            </label>
            <input
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder="Enter email address"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#9ac026] focus:border-transparent"
              style={{ fontFamily: 'Lato, sans-serif' }}
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-[#545454] mb-2" style={{ fontFamily: 'Lato, sans-serif' }}>
              Notes (Optional)
            </label>
            <textarea
              value={newNotes}
              onChange={(e) => setNewNotes(e.target.value)}
              placeholder="Add notes about why this email should be privileged"
              rows="3"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#9ac026] focus:border-transparent"
              style={{ fontFamily: 'Lato, sans-serif' }}
            />
          </div>
          
          <button
            type="submit"
            disabled={addingEmail}
            className="bg-[#9ac026] text-white px-6 py-2 rounded-lg hover:bg-[#8bb024] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ fontFamily: 'Lato, sans-serif' }}
          >
            {addingEmail ? 'Adding...' : 'Add Email'}
          </button>
        </form>
      </div>

      {/* Privileged Emails List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-[#545454]" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Privileged Emails ({privilegedEmails.length})
          </h3>
        </div>
        
        {privilegedEmails.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <svg className="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p style={{ fontFamily: 'Lato, sans-serif' }}>No privileged emails found</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {privilegedEmails.map((emailRecord) => (
              <div key={emailRecord.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className="text-lg font-medium text-[#545454]" style={{ fontFamily: 'Lato, sans-serif' }}>
                        {emailRecord.email}
                      </span>
                      <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full font-medium">
                        Unlimited Sessions
                      </span>
                    </div>
                    
                    <div className="text-sm text-gray-600 space-y-1" style={{ fontFamily: 'Lato, sans-serif' }}>
                      <p>Added by: <span className="font-medium">{emailRecord.added_by_admin}</span></p>
                      <p>Date: <span className="font-medium">{formatDate(emailRecord.created_at)}</span></p>
                      {emailRecord.notes && (
                        <p>Notes: <span className="font-medium">{emailRecord.notes}</span></p>
                      )}
                    </div>
                  </div>
                  
                  <button
                    onClick={() => handleRemoveEmail(emailRecord.id, emailRecord.email)}
                    className="ml-4 text-red-600 hover:text-red-800 hover:bg-red-50 p-2 rounded-lg transition-colors"
                    title={`Remove ${emailRecord.email} from privileged list`}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Privileges;