import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import { UserProvider, useUser } from './context/UserContext';
import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import RecordTransaction from './pages/RecordTransaction';
import GSTReports from './pages/GSTReports';
import Settings from './pages/Settings';
import OnboardingSuccess from './pages/OnboardingSuccess';
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
