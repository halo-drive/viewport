import { createContext, useState, useEffect } from 'react';
import api from './services/api';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userRole, setUserRole] = useState(null);
  const [userEmail, setUserEmail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check auth status when the app loads
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await api.checkAuthStatus();
        if (response.loggedIn) {
          setIsLoggedIn(true);
          setUserRole(response.role);
          setUserEmail(response.email);
        }
      } catch (err) {
        console.error('Error checking auth status:', err);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Login function
  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('email', email);
      formData.append('password', password);
      
      const response = await api.login(formData);
      
      if (response.success) {
        setIsLoggedIn(true);
        setUserRole(response.role);
        setUserEmail(email);
        return { success: true, role: response.role };
      } else {
        setError(response.message);
        return { success: false, message: response.message };
      }
    } catch (err) {
      const errorMsg = err.message || 'Login failed';
      setError(errorMsg);
      return { success: false, message: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  // Signup function
  const signup = async (username, email, password) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('email', email);
      formData.append('password', password);
      
      const response = await api.signup(formData);
      
      if (response.success) {
        return { success: true, message: response.message };
      } else {
        setError(response.message);
        return { success: false, message: response.message };
      }
    } catch (err) {
      const errorMsg = err.message || 'Signup failed';
      setError(errorMsg);
      return { success: false, message: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    setLoading(true);
    try {
      await api.logout();
      setIsLoggedIn(false);
      setUserRole(null);
      setUserEmail(null);
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setLoading(false);
    }
  };

  const authContextValue = {
    isLoggedIn,
    userRole,
    userEmail,
    loading,
    error,
    login,
    signup,
    logout
  };

  return (
    <AuthContext.Provider value={authContextValue}>
      {children}
    </AuthContext.Provider>
  );
}