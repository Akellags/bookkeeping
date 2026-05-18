import React from 'react';
import { AlertCircle, ArrowLeft, RefreshCw, MessageSquare } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';

const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) return envUrl;
  
  const hostname = window.location.hostname;
  
  if (hostname === 'books.helpsu.ai' || hostname === 'www.books.helpsu.ai') {
    return 'https://bookkeeper-be-486079244466.asia-south1.run.app';
  }
  
  if (hostname.includes('-fe-')) {
    return window.location.origin.replace('-fe-', '-be-');
  }
  
  return '';
};

const AuthError = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const errorMsg = searchParams.get('message') || 'We encountered an issue while connecting to your Google account.';
  const isTokenExpired = searchParams.get('type') === 'token_expired';
  
  const whatsappId = localStorage.getItem('whatsapp_id');
  const apiBaseUrl = getApiBaseUrl();
  const reauthUrl = `${apiBaseUrl}/auth/google?whatsapp_id=${whatsappId || 'new_user'}`;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 font-inter">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-xl shadow-gray-200 border border-red-50 p-8 text-center space-y-6">
        <div className="w-20 h-20 bg-red-50 text-red-600 rounded-full flex items-center justify-center mx-auto">
          <AlertCircle size={40} />
        </div>
        
        <div className="space-y-2">
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
            {isTokenExpired ? 'Google Access Expired' : 'Oops! Connection Failed'}
          </h1>
          <p className="text-gray-500 font-medium leading-relaxed">
            {errorMsg}
          </p>
        </div>

        <div className="bg-blue-50 p-4 rounded-2xl text-left border border-blue-100">
          <h3 className="text-sm font-bold text-blue-800 mb-1 flex items-center gap-2">
            <RefreshCw size={14} />
            {isTokenExpired ? 'How to fix this:' : 'Next Steps:'}
          </h3>
          <ul className="text-sm text-blue-700 space-y-2 font-medium">
            {isTokenExpired ? (
              <>
                <li>• Click the "Re-authorize" button below.</li>
                <li>• Sign in with your Google account.</li>
                <li>• Help U will automatically reconnect to your Drive.</li>
              </>
            ) : (
              <>
                <li>• Ensure you're logged into the correct Google account.</li>
                <li>• Make sure you allow all requested permissions.</li>
                <li>• Try clearing your browser cache and retrying.</li>
              </>
            )}
          </ul>
        </div>

        <div className="flex flex-col space-y-3">
          {isTokenExpired ? (
            <a 
              href={reauthUrl}
              className="flex items-center justify-center space-x-2 bg-blue-600 text-white font-bold py-4 rounded-2xl shadow-lg shadow-blue-100 hover:bg-blue-700 transition transform active:scale-95"
            >
              <RefreshCw size={18} />
              <span>Re-authorize Google Access</span>
            </a>
          ) : (
            <button 
              onClick={() => navigate('/')}
              className="flex items-center justify-center space-x-2 bg-blue-600 text-white font-bold py-4 rounded-2xl shadow-lg shadow-blue-100 hover:bg-blue-700 transition transform active:scale-95"
            >
              <ArrowLeft size={18} />
              <span>Back to Home</span>
            </button>
          )}
          
          {whatsappId ? (
            <button 
              onClick={() => navigate('/dashboard')}
              className="flex items-center justify-center space-x-2 bg-white text-gray-700 border border-gray-200 font-bold py-4 rounded-2xl hover:bg-gray-50 transition"
            >
              <span>Back to Dashboard</span>
            </button>
          ) : (
            <a 
              href="https://wa.me/919000521868" 
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center space-x-2 bg-white text-gray-700 border border-gray-200 font-bold py-4 rounded-2xl hover:bg-gray-50 transition"
            >
              <MessageSquare size={18} />
              <span>Contact Support on WhatsApp</span>
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthError;
