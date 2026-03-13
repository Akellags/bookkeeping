import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import GSTReports from './pages/GSTReports';
import Settings from './pages/Settings';
import OnboardingSuccess from './pages/OnboardingSuccess';
import AuthError from './pages/AuthError';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/reports" element={<GSTReports />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/onboarding-success" element={<OnboardingSuccess />} />
        <Route path="/auth-error" element={<AuthError />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
