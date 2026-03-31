import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const UserContext = createContext();

const isValidId = (id) => id && id !== 'null' && id !== 'undefined' && id.trim() !== '';

export const UserProvider = ({ children }) => {
  const [userStats, setUserStats] = useState(null);
  const [businesses, setBusinesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [whatsappId, setWhatsappId] = useState(localStorage.getItem('whatsapp_id'));

  const fetchUserStats = async (id = whatsappId) => {
    if (!isValidId(id)) {
      setLoading(false);
      return;
    }
    try {
      const response = await axios.get(`/api/user/stats?whatsapp_id=${id}`);
      setUserStats(response.data);
    } catch (error) {
      console.error('Error fetching user stats:', error);
    } finally {
      setLoading(false);
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

  const login = (id) => {
    localStorage.setItem('whatsapp_id', id);
    setWhatsappId(id);
  };

  const logout = () => {
    localStorage.removeItem('whatsapp_id');
    setWhatsappId(null);
    setUserStats(null);
    setBusinesses([]);
  };

  useEffect(() => {
    if (isValidId(whatsappId)) {
      fetchUserStats();
      fetchBusinesses();
    } else {
      setLoading(false);
    }
  }, [whatsappId]);

  return (
    <UserContext.Provider value={{ 
      userStats, 
      businesses, 
      loading, 
      whatsappId, 
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
