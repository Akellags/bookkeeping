import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const UserContext = createContext();

const isValidId = (id) => id && id !== 'null' && id !== 'undefined' && id.trim() !== '';

export const UserProvider = ({ children }) => {
  const [userStats, setUserStats] = useState(null);
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(false);
  const [whatsappId, setWhatsappId] = useState(localStorage.getItem('whatsapp_id'));
  const [authToken, setAuthToken] = useState(localStorage.getItem('auth_token'));

  const fetchUserStats = async (id = whatsappId) => {
    if (!isValidId(id)) return;
    setStatsLoading(true);
    try {
      // Use the stored token if available
      const response = await axios.get(`/api/user/stats?whatsapp_id=${id}`);
      setUserStats(response.data);
    } catch (error) {
      console.error('Error fetching user stats:', error);
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchBusinesses = async (id = whatsappId) => {
    if (!isValidId(id)) return;
    try {
      const response = await axios.get(`/api/user/businesses?whatsapp_id=${id}`);
      setBusinesses(response.data.businesses || []);
    } catch (error) {
      console.error('Error fetching businesses:', error);
    }
  };

  const login = (id, token = null) => {
    localStorage.setItem('whatsapp_id', id);
    setWhatsappId(id);
    if (token) {
      localStorage.setItem('auth_token', token);
      setAuthToken(token);
    }
  };

  const logout = () => {
    localStorage.removeItem('whatsapp_id');
    localStorage.removeItem('auth_token');
    setWhatsappId(null);
    setAuthToken(null);
    setUserStats(null);
    setBusinesses([]);
  };

  useEffect(() => {
    if (isValidId(whatsappId)) {
      fetchUserStats();
      fetchBusinesses();
    }
    setLoading(false);
  }, [whatsappId, authToken]);

  return (
    <UserContext.Provider value={{ 
      userStats, 
      businesses, 
      loading, 
      statsLoading,
      whatsappId, 
      authToken,
      fetchUserStats, 
      fetchBusinesses, 
      login, 
      logout 
    }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};
