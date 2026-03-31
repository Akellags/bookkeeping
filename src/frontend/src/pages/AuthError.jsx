import React from 'react';
import { AlertCircle, ArrowLeft, RefreshCw, MessageSquare } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';

const AuthError = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const errorMsg = searchParams.get('message') || 'We encountered an issue while connecting to your Google account.';

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 font-inter">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-xl shadow-gray-200 border border-red-50 p-8 text-center space-y-6">
        <div className="w-20 h-20 bg-red-50 text-red-600 rounded-full flex items-center justify-center mx-auto">
          <AlertCircle size={40} />
        </div>
        
        <div className="space-y-2">
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Oops! Connection Failed</h1>
          <p className="text-gray-500 font-medium leading-relaxed">
            {errorMsg}
          </p>
        </div>

        <div className="bg-blue-50 p-4 rounded-2xl text-left border border-blue-100">
          <h3 className="text-sm font-bold text-blue-800 mb-1 flex items-center gap-2">
            <RefreshCw size={14} />
            Next Steps:
          </h3>
          <ul className="text-sm text-blue-700 space-y-2 font-medium">
            <li>• Ensure you're logged into the correct Google account.</li>
            <li>• Make sure you allow all requested permissions.</li>
            <li>• Try clearing your browser cache and retrying.</li>
          </ul>
        </div>

        <div className="flex flex-col space-y-3">
          <button 
            onClick={() => navigate('/')}
            className="flex items-center justify-center space-x-2 bg-blue-600 text-white font-bold py-4 rounded-2xl shadow-lg shadow-blue-100 hover:bg-blue-700 transition transform active:scale-95"
          >
            <ArrowLeft size={18} />
            <span>Back to Home</span>
          </button>
          
          <a 
            href="https://wa.me/your_number_here" 
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center space-x-2 bg-white text-gray-700 border border-gray-200 font-bold py-4 rounded-2xl hover:bg-gray-50 transition"
          >
            <MessageSquare size={18} />
            <span>Contact Support on WhatsApp</span>
          </a>
        </div>
      </div>
    </div>
  );
};

export default AuthError;
