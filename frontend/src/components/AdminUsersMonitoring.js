import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './AdminUsersMonitoring.css';

const AdminUsersMonitoring = () => {
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uuidFilter, setUuidFilter] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'last_session_created', direction: 'desc' });
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown, setCountdown] = useState(60);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [actionLoading, setActionLoading] = useState({});

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  // Fetch users data
  const fetchUsersData = useCallback(async () => {
    try {
      const token = localStorage.getItem('cat_prep_token');
      if (!token) {
        setError('Not authenticated. Please log in.');
        return;
      }

      const response = await axios.get(`${backendUrl}/api/admin/users-monitoring`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.data.success) {
        setUsers(response.data.users);
        setFilteredUsers(response.data.users);
        setLastUpdated(new Date(response.data.timestamp));
        setError(null);
      }
    } catch (err) {
      console.error('Error fetching users data:', err);
      if (err.response?.status === 403) {
        setError('Access denied. Admin privileges required.');
      } else {
        setError('Failed to fetch monitoring data. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  // Initial fetch
  useEffect(() => {
    fetchUsersData();
  }, [fetchUsersData]);

  // Auto-refresh timer
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          fetchUsersData();
          return 60;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, fetchUsersData]);

  // Filter by UUID
  useEffect(() => {
    if (!uuidFilter.trim()) {
      setFilteredUsers(users);
    } else {
      const filtered = users.filter(user =>
        user.user_id.toLowerCase().includes(uuidFilter.toLowerCase())
      );
      setFilteredUsers(filtered);
    }
  }, [uuidFilter, users]);

  // Sorting
  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });

    const sorted = [...filteredUsers].sort((a, b) => {
      let aVal = a[key];
      let bVal = b[key];

      // Handle null values
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      // Date comparison
      if (key === 'last_session_created') {
        aVal = aVal ? new Date(aVal).getTime() : 0;
        bVal = bVal ? new Date(bVal).getTime() : 0;
      }

      if (aVal < bVal) return direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return direction === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredUsers(sorted);
  };

  // Fix user jobs
  const handleFixUserJobs = async (userId, userEmail) => {
    if (!window.confirm(`Fix exhausted jobs and regenerate pack for ${userEmail}?`)) {
      return;
    }

    setActionLoading({ ...actionLoading, [userId]: true });

    try {
      const token = localStorage.getItem('cat_prep_token');
      const response = await axios.post(
        `${backendUrl}/api/admin/fix-user-jobs`,
        { user_id: userId },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data.success) {
        // Build detailed success message
        let message = `✅ ${response.data.message}\n\n`;
        message += `📊 Actions Taken:\n`;
        if (response.data.actions_taken && response.data.actions_taken.length > 0) {
          response.data.actions_taken.forEach(action => {
            message += `  • ${action}\n`;
          });
        }
        message += `\n📈 Summary:\n`;
        message += `  • Exhausted Jobs Deleted: ${response.data.deleted_jobs_count || 0}\n`;
        message += `  • Stuck Jobs Cancelled: ${response.data.stuck_jobs_cancelled || 0}\n`;
        message += `  • Empty Sessions Fixed: ${response.data.empty_sessions_fixed || 0}\n`;
        if (response.data.new_job_id) {
          message += `  • New Job Enqueued: ${response.data.new_job_id.substring(0, 8)}...\n`;
        }
        
        alert(message);
        fetchUsersData(); // Refresh data
      }
    } catch (err) {
      console.error('Error fixing user jobs:', err);
      alert('❌ Failed to fix user jobs. Please try again.');
    } finally {
      setActionLoading({ ...actionLoading, [userId]: false });
    }
  };

  // Download CSV
  const downloadCSV = () => {
    const headers = [
      'UUID',
      'Email',
      'Name',
      'Sessions Completed',
      'Last Session Created',
      'Current Session ID',
      'Pre-Pack Available',
      'Jobs Enqueued',
      'Exhausted Jobs',
      'Critical Issue',
      'Failed Job Type'
    ];

    const rows = filteredUsers.map(user => [
      user.user_id,
      user.email,
      user.name,
      user.sessions_completed,
      user.last_session_created || 'N/A',
      user.current_session_id || 'None',
      user.pre_pack_available ? 'Yes' : 'No',
      user.jobs_enqueued,
      user.exhausted_jobs,
      user.critical_issue ? 'CRITICAL' : 'OK',
      user.failed_job_type || '-'
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `twelvr_users_monitor_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getSortIcon = (key) => {
    if (sortConfig.key !== key) return '↕️';
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };

  if (loading) {
    return (
      <div className="admin-monitoring-container">
        <div className="loading-spinner">Loading monitoring data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-monitoring-container">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  return (
    <div className="admin-monitoring-container">
      <div className="monitoring-header">
        <h1>User & Job Monitoring</h1>
        <p className="subtitle">Real-time monitoring of all users, sessions, and background jobs</p>
      </div>

      <div className="controls-panel">
        <div className="filter-section">
          <label>🔍 Filter by UUID:</label>
          <input
            type="text"
            value={uuidFilter}
            onChange={(e) => setUuidFilter(e.target.value)}
            placeholder="Enter full or partial UUID..."
            className="uuid-filter-input"
          />
          {uuidFilter && (
            <button onClick={() => setUuidFilter('')} className="clear-filter-btn">
              Clear
            </button>
          )}
        </div>

        <div className="refresh-section">
          <div className="auto-refresh-toggle">
            <label>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              Auto-refresh ({autoRefresh ? `${countdown}s` : 'OFF'})
            </label>
          </div>
          <button onClick={fetchUsersData} className="refresh-btn">
            🔄 Refresh Now
          </button>
          <button onClick={downloadCSV} className="csv-btn">
            📥 Download CSV
          </button>
        </div>
      </div>

      {lastUpdated && (
        <div className="last-updated">
          Last updated: {lastUpdated.toLocaleString()}
        </div>
      )}

      <div className="users-count">
        Showing {filteredUsers.length} of {users.length} users
      </div>

      <div className="table-container">
        <table className="monitoring-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('user_id')}>
                UUID {getSortIcon('user_id')}
              </th>
              <th onClick={() => handleSort('email')}>
                Email {getSortIcon('email')}
              </th>
              <th onClick={() => handleSort('name')}>
                Name {getSortIcon('name')}
              </th>
              <th onClick={() => handleSort('sessions_completed')}>
                Sessions {getSortIcon('sessions_completed')}
              </th>
              <th onClick={() => handleSort('last_session_created')}>
                Last Session {getSortIcon('last_session_created')}
              </th>
              <th onClick={() => handleSort('current_session_id')}>
                Current Session ID {getSortIcon('current_session_id')}
              </th>
              <th onClick={() => handleSort('pre_pack_available')}>
                Pre-Pack {getSortIcon('pre_pack_available')}
              </th>
              <th onClick={() => handleSort('jobs_enqueued')}>
                Jobs Enqueued {getSortIcon('jobs_enqueued')}
              </th>
              <th onClick={() => handleSort('exhausted_jobs')}>
                Exhausted Jobs {getSortIcon('exhausted_jobs')}
              </th>
              <th onClick={() => handleSort('critical_issue')}>
                Status {getSortIcon('critical_issue')}
              </th>
              <th onClick={() => handleSort('failed_job_type')}>
                Failed Job Type {getSortIcon('failed_job_type')}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr
                key={user.user_id}
                className={user.critical_issue ? 'critical-row' : ''}
              >
                <td className="uuid-cell" title={user.user_id}>
                  {user.user_id}
                </td>
                <td>{user.email}</td>
                <td>{user.name}</td>
                <td className="centered">{user.sessions_completed}</td>
                <td>
                  {user.last_session_created
                    ? new Date(user.last_session_created).toLocaleString()
                    : 'N/A'}
                </td>
                <td className="uuid-cell" title={user.current_session_id}>
                  {user.current_session_id || 'None'}
                </td>
                <td className="centered">
                  {user.pre_pack_available ? (
                    <span className="status-badge success">✅ Yes</span>
                  ) : (
                    <span className="status-badge error">❌ No</span>
                  )}
                </td>
                <td className="centered">{user.jobs_enqueued}</td>
                <td className="centered">
                  {user.exhausted_jobs > 0 ? (
                    <span className="badge-warning">{user.exhausted_jobs}</span>
                  ) : (
                    user.exhausted_jobs
                  )}
                </td>
                <td className="centered">
                  {user.critical_issue ? (
                    <span className="status-badge critical">🔴 CRITICAL</span>
                  ) : (
                    <span className="status-badge ok">✅ OK</span>
                  )}
                </td>
                <td>{user.failed_job_type || '-'}</td>
                <td>
                  {(user.exhausted_jobs > 0 || !user.pre_pack_available) && (
                    <button
                      onClick={() => handleFixUserJobs(user.user_id, user.email)}
                      disabled={actionLoading[user.user_id]}
                      className="fix-btn"
                      title="Clean exhausted jobs, fix empty packs, and regenerate session pack"
                    >
                      {actionLoading[user.user_id] ? '⏳ Processing...' : '🔧 Fix & Regenerate'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredUsers.length === 0 && (
        <div className="no-results">
          No users found matching the filter criteria.
        </div>
      )}
    </div>
  );
};

export default AdminUsersMonitoring;
