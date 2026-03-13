import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Building2, 
  Mail, 
  Phone, 
  ExternalLink,
  Save,
  Loader2,
  Database
} from 'lucide-react';
import Layout from '../components/Layout';

const Settings = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    business_name: '',
    business_gstin: ''
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const whatsappId = localStorage.getItem('whatsapp_id') || '919703333319';
        const response = await axios.get(`/api/user/stats?whatsapp_id=${whatsappId}`);
        setStats(response.data);
        setFormData({
          business_name: response.data.business_name || '',
          business_gstin: response.data.business_gstin || ''
        });
      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      const whatsappId = localStorage.getItem('whatsapp_id') || '919703333319';
      await axios.post(`/api/user/settings?whatsapp_id=${whatsappId}`, formData);
      alert('Settings updated successfully!');
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <Layout userStats={stats}>
      <div className="max-w-4xl space-y-8">
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
                <span>+{stats?.whatsapp_id}</span>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-bold text-gray-500 uppercase tracking-wider">Login Email</label>
              <div className="flex items-center bg-gray-50 border border-gray-200 rounded-xl px-4 py-4 space-x-3 text-gray-500">
                <Mail size={18} />
                <span>{stats?.google_email}</span>
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
                href={`https://docs.google.com/spreadsheets/d/${stats?.sheet_id}`}
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
    </Layout>
  );
};

export default Settings;
