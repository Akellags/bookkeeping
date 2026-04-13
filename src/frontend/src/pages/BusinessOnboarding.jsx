import React, { useState, useEffect } from 'react';
import { Building2, Hash, ArrowRight, Loader2, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import axios from 'axios';

const BusinessOnboarding = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useUser();
  
  const whatsappId = searchParams.get('whatsapp_id');
  const token = searchParams.get('token');
  const isNewUser = searchParams.get('new') === 'true';

  const [formData, setFormData] = useState({
    business_name: '',
    business_gstin: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // If we have token/id, log them in immediately so the context has the auth
    if (whatsappId && token) {
      login(whatsappId, token);
    }
  }, [whatsappId, token, login]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.business_name) {
      setError("Business Name is required");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`/api/user/onboard?whatsapp_id=${whatsappId}`, formData);
      
      // Redirect to success page with original params
      const successUrl = `/onboarding-success?${searchParams.toString()}`;
      navigate(successUrl);
    } catch (err) {
      console.error('Onboarding failed:', err);
      setError(err.response?.data?.detail || "Failed to save business details. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-50 flex flex-col items-center justify-center min-h-screen p-4 font-inter">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl p-10 space-y-8 border border-gray-100 relative overflow-hidden">
        {/* Progress Bar */}
        <div className="absolute top-0 left-0 w-full h-2 bg-gray-100">
          <div className="h-full bg-blue-600 w-2/3"></div>
        </div>

        <div className="text-center space-y-2">
          <div className="mx-auto bg-blue-100 text-blue-600 p-4 rounded-2xl w-16 h-16 flex items-center justify-center mb-4">
            <Building2 size={32} />
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
            {isNewUser ? "Business Setup" : "Update Profile"}
          </h1>
          <p className="text-gray-500 font-medium">
            {isNewUser 
              ? "Let's personalize your bookkeeping experience." 
              : "Please update your legal business details to continue."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            {/* Business Name */}
            <div className="space-y-1.5">
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                <Building2 size={12} /> Legal Business Name
              </label>
              <input 
                type="text"
                required
                value={formData.business_name}
                onChange={(e) => setFormData({...formData, business_name: e.target.value})}
                placeholder="e.g. Acme Corporation"
                className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none font-bold text-gray-700 transition"
              />
            </div>

            {/* GSTIN */}
            <div className="space-y-1.5">
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                <Hash size={12} /> GSTIN (Optional)
              </label>
              <input 
                type="text"
                value={formData.business_gstin}
                onChange={(e) => setFormData({...formData, business_gstin: e.target.value.toUpperCase()})}
                placeholder="15-digit GST number"
                maxLength={15}
                className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none font-bold text-gray-700 transition"
              />
              <p className="text-[10px] text-gray-400 font-bold uppercase tracking-tight">
                This helps us automate your GSTR-1 reports.
              </p>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl text-sm font-bold border border-red-100 flex items-center space-x-2">
              <ShieldCheck size={18} />
              <span>{error}</span>
            </div>
          )}

          <button 
            type="submit"
            disabled={loading}
            className="flex items-center justify-center space-x-2 w-full bg-blue-600 text-white font-bold py-4 rounded-2xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition duration-200 transform hover:scale-[1.02] active:scale-95 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <>
                <span>Complete Setup</span>
                <ArrowRight size={20} />
              </>
            )}
          </button>
        </form>

        <div className="pt-4 text-center border-t border-gray-50">
          <div className="flex items-center justify-center space-x-2 text-green-600">
            <CheckCircle2 size={16} />
            <span className="text-xs font-bold uppercase tracking-widest">Google Drive Ready</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BusinessOnboarding;
