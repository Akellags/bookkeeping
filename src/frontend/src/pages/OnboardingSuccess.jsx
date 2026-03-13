import React, { useEffect } from 'react';
import { CheckCircle2, Folder, Table, ArrowRight, LayoutDashboard } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';

const OnboardingSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const whatsappId = searchParams.get('whatsapp_id');

  useEffect(() => {
    if (whatsappId) {
      localStorage.setItem('whatsapp_id', whatsappId);
    }
  }, [whatsappId]);

  return (
    <div className="bg-gray-50 flex flex-col items-center justify-center min-h-screen p-4 text-center font-inter">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-10 space-y-8 border border-gray-100 relative overflow-hidden">
        {/* Celebration Effect */}
        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-green-400 to-blue-500"></div>
        <div className="absolute -top-10 -left-10 w-40 h-40 bg-blue-100 rounded-full blur-3xl opacity-50"></div>
        <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-green-100 rounded-full blur-3xl opacity-50"></div>

        {/* Success Icon */}
        <div className="relative mx-auto bg-green-100 text-green-600 p-4 rounded-full w-20 h-20 flex items-center justify-center shadow-inner">
          <CheckCircle2 size={40} />
        </div>

        <div className="space-y-4">
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">You're All Set! 🚀</h1>
          <p className="text-gray-500 text-lg leading-relaxed font-medium">
            Your <strong>Google Drive</strong> is now linked and your <strong>Master Ledger</strong> has been initialized.
          </p>
        </div>

        {/* Details Card */}
        <div className="bg-blue-50 rounded-2xl p-6 text-left space-y-4 border border-blue-100">
          <div className="flex items-center space-x-3 text-blue-700">
            <Folder size={20} />
            <span className="font-bold text-sm">Folder: /Help U</span>
          </div>
          <div className="flex items-center space-x-3 text-blue-700">
            <Table size={20} />
            <span className="font-bold text-sm">Sheet: Master_Ledger</span>
          </div>
        </div>

        <div className="pt-4 space-y-4">
          <button 
            onClick={() => navigate('/dashboard')}
            className="flex items-center justify-center space-x-2 w-full bg-blue-600 text-white font-bold py-4 rounded-2xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition duration-200 transform hover:scale-105 active:scale-95"
          >
            <LayoutDashboard size={20} />
            <span>Go to Dashboard</span>
          </button>
          
          <div className="flex flex-col space-y-2">
            <p className="text-xs text-gray-400 font-medium">
              You can now record transactions directly from the web or via WhatsApp.
            </p>
            {whatsappId && whatsappId.startsWith('web_') && (
              <p className="text-[10px] text-gray-300">
                Web ID: {whatsappId}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnboardingSuccess;
