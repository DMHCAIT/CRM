import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const token = localStorage.getItem('access_token');
    const storedUser = localStorage.getItem('user');
    
    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (error) {
        console.error('Failed to parse user from localStorage:', error);
        logout();
      }
    }
    
    setLoading(false);
  }, []);

  const login = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  };

  const isAuthenticated = () => {
    return !!user && !!localStorage.getItem('access_token');
  };

  const hasRole = (requiredRole) => {
    if (!user) return false;
    
    const roleLevels = {
      'Counselor': 1,
      'Team Leader': 2,
      'Manager': 3,
      'Hospital Admin': 4,
      'Super Admin': 5,
    };
    
    return roleLevels[user.role] >= roleLevels[requiredRole];
  };

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated,
    hasRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
