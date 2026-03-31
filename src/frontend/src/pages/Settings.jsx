import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Building2, 
  Mail, 
  Phone, 
  ExternalLink,
  Save,
  Loader2,
  Database,
  MessageCircle
} from 'lucide-react';
import { useUser } from '../context/UserContext';

const Settings = () => {
  const { userStats: globalUserStats, whatsappId, fetchUserStats } = useUser();
  const [loading, setLoading] = useState(!globalUserStats);
  const [saving, setSaving] = useState(false);
  const [linkToken, setLinkToken] = useState(null);
  const [generatingToken, setGeneratingToken] = useState(false);
  const [formData, setFormData] = useState({
    business_name: '',
    business_gstin: ''
  });

  const botNumber = import.meta.env.VITE_WHATSAPP_BOT_NUMBER || "919000000000";

  useEffect(() => {
    if (globalUserStats) {
      setFormData({
        business_name: globalUserStats.business_name || '',
        business_gstin: globalUserStats.business_gstin || ''
      });
      setLoading(false);
    }
  }, [globalUserStats]);

  const handleSave = async () => {
    try {
      if (!whatsappId) return;
      setSaving(true);
      await axios.post(`/api/user/settings?whatsapp_id=${whatsappId}`, formData);
      await fetchUserStats();
      alert('Settings updated successfully!');
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateToken = async () => {
    try {
      if (!whatsappId) return;
      setGeneratingToken(true);
      const response = await axios.post(`/api/user/generate-link-token?whatsapp_id=${whatsappId}`);
      setLinkToken(response.data.link_token);
    } catch (error) {
      console.error('Failed to generate token:', error);
      alert('Failed to generate link token. Please try again.');
    } finally {
      setGeneratingToken(false);
    }
  };

  const handleWhatsAppLink = () => {
    if (linkToken) {
      const message = `VERIFY_${linkToken}`;
      const url = `https://wa.me/${botNumber}?text=${encodeURIComponent(message)}`;
      window.open(url, '_blank');
    }
  };

  if (loading && !globalUserStats) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-8">
      {/* WhatsApp Linking Section (Only for web users) */}
      {whatsappId && whatsappId.startsWith('web_') && (
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-8 border border-green-100 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-10 text-green-600">
            <MessageCircle size={120} />
          </div>
          
          <div className="relative z-10 space-y-6">
            <div className="space-y-2">
              <h3 className="text-2xl font-bold text-green-900">Connect to WhatsApp Bot</h3>
              <p className="text-green-700 font-medium max-w-lg">
                Link your WhatsApp account to start recording transactions via chat, snap photos of bills, and receive monthly GSTR-1 reminders.
              </p>
            </div>

            {!linkToken ? (
              <button
                onClick={handleGenerateToken}
                disabled={generatingToken}
                className="flex items-center space-x-2 bg-green-600 text-white px-8 py-4 rounded-xl font-bold shadow-lg shadow-green-200 hover:bg-green-700 transition transform hover:scale-105 disabled:opacity-50"
              >
                {generatingToken ? <Loader2 className="animate-spin" size={20} /> : <MessageCircle size={20} />}
                <span>Generate Magic Link</span>
              </button>
            ) : (
              <div className="space-y-4">
                <div className="bg-white/60 backdrop-blur-sm p-4 rounded-xl border border-green-200 inline-block">
                  <p className="text-xs font-bold text-green-600 uppercase tracking-wider mb-1">Your Verification Code</p>
                  <p className="text-3xl font-mono font-black text-green-900 tracking-widest">{linkToken}</p>
                </div>
                
                <div className="flex flex-col sm:flex-row gap-4">
                  <button
                    onClick={handleWhatsAppLink}
                    className="flex items-center justify-center space-x-2 bg-green-600 text-white px-8 py-4 rounded-xl font-bold shadow-lg shadow-green-200 hover:bg-green-700 transition transform hover:scale-105"
                  >
                    <ExternalLink size={20} />
                    <span>Connect WhatsApp Now</span>
                  </button>
                  <button
                    onClick={() => setLinkToken(null)}
                    className="text-green-700 font-bold px-6 py-4"
                  >
                    Cancel
                  </button>
                </div>
                <p className="text-[10px] text-green-600 font-bold uppercase italic">Valid for 30 minutes • Single use only</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Business Profile */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
        <div className="flex items-center space-x-3 mb-6">
          <Building2 className="text-blue-600" size={24} />
          <h3 className="text-xl font-bold text-gray-900">Business Profile</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-bold text-gray-500 uppercase tracking-wider">Business Name</label>
            <input 
              type="text" 
              value={formData.business_name}
              onChange={(e) => setFormData({...formData, business_name: e.target.value})}
              className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-bold text-gray-500 uppercase tracking-wider">GSTIN</label>
            <input 
              type="text" 
              value={formData.business_gstin}
              onChange={(e) => setFormData({...formData, business_gstin: e.target.value})}
              className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-bold text-gray-500 uppercase tracking-wider">WhatsApp Number</label>
            <div className="flex items-center bg-gray-50 border border-gray-200 rounded-xl px-4 py-4 space-x-3 text-gray-500">
              <Phone size={18} />
              <span>+{globalUserStats?.whatsapp_id}</span>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-bold text-gray-500 uppercase tracking-wider">Login Email</label>
            <div className="flex items-center bg-gray-50 border border-gray-200 rounded-xl px-4 py-4 space-x-3 text-gray-500">
              <Mail size={18} />
              <span>{globalUserStats?.google_email}</span>
            </div>
          </div>
        </div>

        <div className="mt-8 flex justify-end">
          <button 
            onClick={handleSave}
            disabled={saving}
            className="flex items-center space-x-2 bg-blue-600 text-white font-bold py-3 px-8 rounded-xl hover:bg-blue-700 transition shadow-sm disabled:opacity-50"
          >
            {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            <span>{saving ? 'Saving...' : 'Save Changes'}</span>
          </button>
        </div>
      </div>

      {/* Connections */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
        <div className="flex items-center space-x-3 mb-6">
          <Database className="text-blue-600" size={24} />
          <h3 className="text-xl font-bold text-gray-900">Data Storage</h3>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-100">
            <div className="flex items-center space-x-4">
              <div className="bg-white p-2.5 rounded-lg border border-gray-100 shadow-sm">
                <img src="https://upload.wikimedia.org/wikipedia/commons/1/12/Google_Drive_icon_%282020%29.svg" className="w-6 h-6" alt="Drive" />
              </div>
              <div>
                <p className="font-bold text-gray-900">Google Drive Ledger</p>
                <p className="text-sm text-gray-500">Connected to your personal Drive storage</p>
              </div>
            </div>
            <a 
              href={`https://docs.google.com/spreadsheets/d/${globalUserStats?.sheet_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 font-bold text-sm"
            >
              <span>Manage Sheet</span>
              <ExternalLink size={14} />
            </a>
          </div>
          
          <button className="w-full py-4 text-red-500 font-bold border-2 border-dashed border-red-100 rounded-xl hover:bg-red-50 hover:border-red-200 transition">
            Reset Connection & Disconnect Storage
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
