import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../AuthContext';
import api from '../services/api';
import logoViolet from '../assets/logo-violet.png';

export default function AdminDashboard() {
  const [pendingUsers, setPendingUsers] = useState([]);
  const [approvedUsers, setApprovedUsers] = useState([]);
  const [activeTab, setActiveTab] = useState('pending'); // 'pending' or 'approved'
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  
  const { logout } = useContext(AuthContext);

  // Fetch all users when component mounts
  useEffect(() => {
    fetchAllUsers();
  }, []);

  const fetchAllUsers = async () => {
    try {
      setLoading(true);
      const response = await api.getAllUsers();
      
      if (response.success) {
        const users = response.users || [];
        setPendingUsers(users.filter(user => !user.isApproved));
        setApprovedUsers(users.filter(user => user.isApproved));
      } else {
        setMessage(response.message || 'Failed to fetch users');
        setMessageType('error');
      }
    } catch (err) {
      console.error('Error fetching users:', err);
      setMessage(err.message || 'Failed to fetch users');
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveUser = async (email) => {
    try {
      const formData = new FormData();
      formData.append('email', email);
      
      const response = await api.approveUser(formData);
      
      if (response.success) {
        setMessage(`User ${email} approved successfully`);
        setMessageType('success');
        
        // Move the user from pending to approved
        const userToMove = pendingUsers.find(user => user.email === email);
        if (userToMove) {
          userToMove.isApproved = true;
          setApprovedUsers([...approvedUsers, userToMove]);
          setPendingUsers(pendingUsers.filter(user => user.email !== email));
        }
      } else {
        setMessage(response.message || 'Failed to approve user');
        setMessageType('error');
      }
    } catch (err) {
      console.error('Error approving user:', err);
      setMessage(err.message || 'Failed to approve user');
      setMessageType('error');
    }
  };

  const handleDeleteUser = async (email, isApproved) => {
    if (!confirm(`Are you sure you want to delete user ${email}?`)) {
      return;
    }
    
    try {
      const formData = new FormData();
      formData.append('email', email);
      
      const response = await api.deleteUser(formData);
      
      if (response.success) {
        setMessage(`User ${email} deleted successfully`);
        setMessageType('success');
        
        // Remove user from the appropriate list
        if (isApproved) {
          setApprovedUsers(approvedUsers.filter(user => user.email !== email));
        } else {
          setPendingUsers(pendingUsers.filter(user => user.email !== email));
        }
      } else {
        setMessage(response.message || 'Failed to delete user');
        setMessageType('error');
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      setMessage(err.message || 'Failed to delete user');
      setMessageType('error');
    }
  };

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div style={styles.dashboard}>
      <div style={styles.header}>
        <img src={logoViolet} alt="Logo" style={styles.logo} />
        <h1>Admin Dashboard</h1>
        <button 
          style={styles.logoutButton}
          onClick={handleLogout}
        >
          Logout
        </button>
      </div>
      
      {message && (
        <div style={{
          ...styles.message,
          ...(messageType === 'error' ? styles.errorMessage : styles.successMessage)
        }}>
          {message}
        </div>
      )}
      
      <div style={styles.tabs}>
        <button 
          style={{
            ...styles.tabButton,
            ...(activeTab === 'pending' ? styles.activeTab : {})
          }}
          onClick={() => setActiveTab('pending')}
        >
          Pending Users ({pendingUsers.length})
        </button>
        <button 
          style={{
            ...styles.tabButton,
            ...(activeTab === 'approved' ? styles.activeTab : {})
          }}
          onClick={() => setActiveTab('approved')}
        >
          Approved Users ({approvedUsers.length})
        </button>
      </div>
      
      <div style={styles.section}>
        <h2>{activeTab === 'pending' ? 'Pending User Approvals' : 'Approved Users'}</h2>
        
        {loading ? (
          <p>Loading users...</p>
        ) : activeTab === 'pending' && pendingUsers.length === 0 ? (
          <p>No pending users to approve.</p>
        ) : activeTab === 'approved' && approvedUsers.length === 0 ? (
          <p>No approved users.</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Username</th>
                <th style={styles.th}>Email</th>
                <th style={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {activeTab === 'pending' ? (
                pendingUsers.map((user) => (
                  <tr key={user.id}>
                    <td style={styles.td}>{user.username}</td>
                    <td style={styles.td}>{user.email}</td>
                    <td style={styles.tdActions}>
                      <button 
                        style={styles.approveButton}
                        onClick={() => handleApproveUser(user.email)}
                      >
                        Approve
                      </button>
                      <button 
                        style={styles.deleteButton}
                        onClick={() => handleDeleteUser(user.email, false)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                approvedUsers.map((user) => (
                  <tr key={user.id}>
                    <td style={styles.td}>{user.username}</td>
                    <td style={styles.td}>{user.email}</td>
                    <td style={styles.tdActions}>
                      <button 
                        style={styles.deleteButton}
                        onClick={() => handleDeleteUser(user.email, true)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const styles = {
  dashboard: {
    padding: '2rem',
    maxWidth: '1200px',
    margin: '0 auto',
    fontFamily: 'Inter, sans-serif'
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '2rem',
    paddingBottom: '1rem',
    borderBottom: '1px solid #e0e0e0'
  },
  logo: {
    height: '60px',
    width: 'auto'
  },
  logoutButton: {
    backgroundColor: '#f44336',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: 'bold'
  },
  tabs: {
    display: 'flex',
    marginBottom: '1rem'
  },
  tabButton: {
    padding: '0.75rem 1.5rem',
    border: 'none',
    backgroundColor: '#f5f5f5',
    cursor: 'pointer',
    fontWeight: '500',
    borderTop: '1px solid #e0e0e0',
    borderLeft: '1px solid #e0e0e0',
    borderRight: '1px solid #e0e0e0',
    borderTopLeftRadius: '4px',
    borderTopRightRadius: '4px',
    marginRight: '0.5rem'
  },
  activeTab: {
    backgroundColor: 'white',
    borderBottom: '2px solid #4e7aff',
    fontWeight: '600'
  },
  section: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse'
  },
  th: {
    textAlign: 'left',
    padding: '0.75rem',
    borderBottom: '1px solid #e0e0e0',
    backgroundColor: '#f5f5f5',
    fontWeight: '600'
  },
  td: {
    textAlign: 'left',
    padding: '0.75rem',
    borderBottom: '1px solid #e0e0e0'
  },
  tdActions: {
    textAlign: 'left',
    padding: '0.75rem',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    gap: '0.5rem'
  },
  approveButton: {
    backgroundColor: '#4caf50',
    color: 'white',
    border: 'none',
    padding: '0.5rem 0.75rem',
    borderRadius: '4px',
    cursor: 'pointer'
  },
  deleteButton: {
    backgroundColor: '#f44336',
    color: 'white',
    border: 'none',
    padding: '0.5rem 0.75rem',
    borderRadius: '4px',
    cursor: 'pointer'
  },
  message: {
    padding: '0.75rem 1rem',
    borderRadius: '4px',
    marginBottom: '1.5rem'
  },
  errorMessage: {
    backgroundColor: '#ffebee',
    color: '#c62828',
    border: '1px solid #ef9a9a'
  },
  successMessage: {
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
    border: '1px solid #a5d6a7'
  }
};