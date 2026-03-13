import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Folder, 
  Table, 
  Loader2,
  PlusCircle
} from 'lucide-react';
import Layout from '../components/Layout';
import TransactionModal from '../components/TransactionModal';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchStats = async () => {
    try {
      const whatsappId = localStorage.getItem('whatsapp_id') || '919703333319';
      let url = `/api/user/stats?whatsapp_id=${whatsappId}`;
      if (dateRange.start) url += `&start_date=${formatDate(dateRange.start)}`;
      if (dateRange.end) url += `&end_date=${formatDate(dateRange.end)}`;
      const response = await axios.get(url);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [dateRange]);

  const formatDate = (dateStr) => {
    const [year, month, day] = dateStr.split('-');
    return `${day}-${month}-${year}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
      </div>
    );
  }

  const userStats = stats || { bills: 0, sales: 0, purchases: 0 };

  return (
    <Layout userStats={userStats}>
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-10 gap-6">
          <div className="flex flex-col sm:flex-row items-center gap-4 bg-white p-2 rounded-2xl border border-gray-100 shadow-sm">
            {/* Date Filters */}
            <div className="flex items-center gap-2 px-3 border-r border-gray-100">
              <span className="text-xs font-bold text-gray-400 uppercase">From</span>
              <input 
                type="date" 
                value={dateRange.start}
                onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                className="text-sm font-semibold text-gray-700 bg-transparent border-none focus:ring-0 cursor-pointer" 
              />
            </div>
            <div className="flex items-center gap-2 px-3">
              <span className="text-xs font-bold text-gray-400 uppercase">To</span>
              <input 
                type="date" 
                value={dateRange.end}
                onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                className="text-sm font-semibold text-gray-700 bg-transparent border-none focus:ring-0 cursor-pointer" 
              />
            </div>
            {(dateRange.start || dateRange.end) && (
              <button 
                onClick={() => setDateRange({ start: '', end: '' })}
                className="text-xs font-bold text-blue-600 px-3 hover:text-blue-700 transition"
              >
                Clear
              </button>
            )}
          </div>

          <button 
            onClick={() => setIsModalOpen(true)}
            className="w-full lg:w-auto flex items-center justify-center space-x-2 bg-blue-600 text-white font-bold py-3 px-6 rounded-2xl shadow-xl shadow-blue-100 hover:bg-blue-700 transition transform hover:scale-105 active:scale-95"
          >
            <PlusCircle size={20} />
            <span>Add Transaction</span>
          </button>
        </div>

        <TransactionModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          onRefresh={fetchStats}
        />

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition">
            <p className="text-gray-400 text-sm font-medium mb-1">Bills Processed</p>
            <p className="text-3xl font-bold text-gray-900">{userStats.bills}</p>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition">
            <p className="text-gray-400 text-sm font-medium mb-1">Total Sales</p>
            <p className="text-3xl font-bold text-gray-900">₹{userStats.sales.toLocaleString()}</p>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition">
            <p className="text-gray-400 text-sm font-medium mb-1">Total Purchases</p>
            <p className="text-3xl font-bold text-gray-900">₹{userStats.purchases.toLocaleString()}</p>
          </div>
        </div>

        {/* Drive Access Card */}
        <div className="bg-white rounded-3xl p-8 border border-gray-100 shadow-sm flex flex-col lg:flex-row items-center justify-between space-y-4 lg:space-y-0">
          <div className="flex items-center space-x-6">
            <div className="bg-blue-100 text-blue-600 p-4 rounded-2xl">
              <Folder size={40} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Your Google Drive Ledger</h3>
              <p className="text-gray-500 max-w-sm">All financial data stays in your personal storage. Access your Master Ledger sheet and Purchase folder anytime.</p>
            </div>
          </div>
          <div className="flex space-x-3 w-full lg:w-auto">
            <a 
              href={`https://drive.google.com/drive/folders/${userStats.drive_folder_id}`} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex-1 lg:flex-none flex items-center justify-center space-x-2 bg-gray-100 text-gray-700 font-bold py-3 px-6 rounded-xl hover:bg-gray-200 transition"
            >
              <Folder size={18} />
              <span>View Folder</span>
            </a>
            <a 
              href={`https://docs.google.com/spreadsheets/d/${userStats.sheet_id}`} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex-1 lg:flex-none flex items-center justify-center space-x-2 bg-blue-600 text-white font-bold py-3 px-6 rounded-xl hover:bg-blue-700 transition"
            >
              <Table size={18} />
              <span>Open Sheet</span>
            </a>
          </div>
        </div>
    </Layout>
  );
};

export default Dashboard;
