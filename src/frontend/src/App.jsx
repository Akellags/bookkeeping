import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom';
import axios from 'axios';
import { Loader2 } from 'lucide-react';

// Configure Axios Defaults
const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) return envUrl;
  
  const hostname = window.location.hostname;
  
  // Production fallback
  if (hostname === 'books.helpsu.ai' || hostname === 'www.books.helpsu.ai') {
    return 'https://bookkeeper-be-486079244466.asia-south1.run.app';
  }
  
  // Intelligent fallback for Cloud Run deployments
  if (hostname.includes('-fe-')) {
    return window.location.origin.replace('-fe-', '-be-');
  }
  
  // Local development default (relative calls if no base URL)
  return '';
};

axios.defaults.baseURL = getApiBaseUrl();

import { UserProvider, useUser } from './context/UserContext';
import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import RecordTransaction from './pages/RecordTransaction';
import GSTReports from './pages/GSTReports';
import Settings from './pages/Settings';
import OnboardingSuccess from './pages/OnboardingSuccess';
import BusinessOnboarding from './pages/BusinessOnboarding';
import LoginSuccess from './pages/LoginSuccess';
import AuthError from './pages/AuthError';

// Protected Route Component
const ProtectedRoute = () => {
  const { whatsappId, loading } = useUser();
  const location = useLocation();

  // Only show a white screen if we are truly loading the initial auth state
  // and we don't have a whatsappId in memory yet
  if (loading && !whatsappId) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!whatsappId) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  return <Outlet />;
};

// Layout Wrapper
const MainLayout = () => {
  const { userStats } = useUser();
  return (
    <Layout userStats={userStats}>
      <Outlet />
    </Layout>
  );
};

function AppContent() {
  useEffect(() => {
    // Request Interceptor to add JWT Token
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Global Axios Interceptor for 401 Unauthorized
    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          console.warn(`401 Unauthorized for ${error.config.url}. Logging out...`);
          localStorage.removeItem('whatsapp_id');
          localStorage.removeItem('auth_token');
          window.location.href = '/'; // Force reload to landing page
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(requestInterceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, []);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        
        {/* Protected Routes with shared Layout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/reports" element={<GSTReports />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/transactions/new" element={<RecordTransaction />} />
          </Route>
        </Route>

        <Route path="/onboarding-success" element={<OnboardingSuccess />} />
        <Route path="/onboarding-business" element={<BusinessOnboarding />} />
        <Route path="/login-success" element={<LoginSuccess />} />
        <Route path="/auth-error" element={<AuthError />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

function App() {
  return (
    <UserProvider>
      <AppContent />
    </UserProvider>
  );
}

export default App;
