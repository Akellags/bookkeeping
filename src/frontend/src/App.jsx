import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import GSTReports from './pages/GSTReports';
import Settings from './pages/Settings';
import OnboardingSuccess from './pages/OnboardingSuccess';
import AuthError from './pages/AuthError';

// Helper to validate WhatsApp ID
const isValidId = (id) => {
  return id && id !== 'null' && id !== 'undefined' && id.trim() !== '';
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const whatsappId = localStorage.getItem('whatsapp_id');
  const location = useLocation();

  if (!isValidId(whatsappId)) {
    // Redirect to landing page but save the attempted url
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  return children;
};

function App() {
  useEffect(() => {
    // Global Axios Interceptor for 401 Unauthorized
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          console.warn(`401 Unauthorized for ${error.config.url}. Logging out...`);
          localStorage.removeItem('whatsapp_id');
          window.location.href = '/'; // Force reload to landing page
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><GSTReports /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        <Route path="/onboarding-success" element={<OnboardingSuccess />} />
        <Route path="/auth-error" element={<AuthError />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
