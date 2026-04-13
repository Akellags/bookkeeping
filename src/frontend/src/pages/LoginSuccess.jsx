import React, { useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';

const LoginSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useUser();
  const whatsappId = searchParams.get('whatsapp_id');
  const token = searchParams.get('token');

  useEffect(() => {
    if (whatsappId && token) {
      // Perform login in context
      login(whatsappId, token);
      
      // Small delay to ensure state is set before navigating
      const timer = setTimeout(() => {
        navigate('/dashboard', { replace: true });
      }, 500);
      
      return () => clearTimeout(timer);
    } else {
      // If params are missing, fallback to landing
      navigate('/', { replace: true });
    }
  }, [whatsappId, token, login, navigate]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-white">
      <Loader2 className="w-12 h-12 text-blue-600 animate-spin mb-4" />
      <p className="text-gray-500 font-bold animate-pulse">Signing you in...</p>
    </div>
  );
};

export default LoginSuccess;
