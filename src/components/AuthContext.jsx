import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userType, setUserType] = useState(null);

  const login = async (type, credentials) => {
    if (type === 'doctor') {
      if (credentials.username === 'Doctor' && credentials.password === 'Doctor123') {
        setIsAuthenticated(true);
        setUserType('doctor');
      } else {
        throw new Error('Invalid doctor credentials');
      }
    } 
    else {
      if (credentials.username && credentials.password) {
        setIsAuthenticated(true);
        setUserType('patient');
      } 
      else {
        throw new Error('Invalid credentials');
      }
    }
  };

  const logout = () => {
    setIsAuthenticated(false);
    setUserType(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, userType, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}