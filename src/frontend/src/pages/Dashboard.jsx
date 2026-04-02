import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { 
  Folder, 
  Table, 
  Loader2,
  PlusCircle,
  ShoppingBag,
  ShoppingCart,
  Wallet,
  ArrowUpRight,
  Plus,
  Maximize2
} from 'lucide-react';
import { useUser } from '../context/UserContext';
import TransactionDrawer from '../components/TransactionDrawer';

const Dashboard = () => {
  const { userStats: globalUserStats, whatsappId, statsLoading: globalStatsLoading } = useUser();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [drawerConfig, setDrawerConfig] = useState({ isOpen: false, category: null });

  const fetchStats = async () => {
    try {
      if (!whatsappId) {
        setLoading(false);
        return;
      }

      setLoading(true);
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
  }, [dateRange, whatsappId, globalUserStats?.business_id]);

  const formatDate = (dateStr) => {
    const [year, month, day] = dateStr.split('-');
    return `${day}-${month}-${year}`;
  };

  const openDrawer = (category = null) => {
    setDrawerConfig({ isOpen: true, category });
  };

  const userStats = stats || globalUserStats || { bills: 0, sales: 0, purchases: 0, payments: 0, expenses: 0, expenses_paid: 0, expenses_unpaid: 0 };
  const isCurrentlyLoading = loading || globalStatsLoading;

  return (
    <>
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-10 gap-6">
          <div className="flex flex-col sm:flex-row items-center gap-4 bg-white p-2 rounded-xl border border-gray-100 shadow-sm">
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

          <div className="flex flex-col sm:flex-row gap-4 w-full lg:w-auto">
            <button 
              onClick={() => navigate('/transactions/new')}
              className="flex-1 lg:flex-none flex items-center justify-center space-x-2 bg-white text-blue-600 border-2 border-blue-600 font-bold py-3 px-6 rounded-xl hover:bg-blue-50 transition"
            >
              <Maximize2 size={20} />
              <span>Full Page Entry</span>
            </button>

            <button 
              onClick={() => openDrawer()}
              className="flex-1 lg:flex-none flex items-center justify-center space-x-2 bg-blue-600 text-white font-bold py-3 px-6 rounded-xl shadow-xl shadow-blue-100 hover:bg-blue-700 transition transform hover:scale-105 active:scale-95"
            >
              <PlusCircle size={20} />
              <span>Add Transaction</span>
            </button>
          </div>
        </div>

        <TransactionDrawer 
          isOpen={drawerConfig.isOpen} 
          initialCategory={drawerConfig.category}
          onClose={() => setDrawerConfig({ isOpen: false, category: null })} 
          onRefresh={fetchStats}
          whatsappId={whatsappId}
        />

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6 mb-10">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 group relative">
            <p className="text-gray-400 text-sm font-medium mb-1">Bills Processed</p>
            {isCurrentlyLoading && !stats ? <div className="h-9 w-16 bg-gray-100 animate-pulse rounded" /> : <p className="text-3xl font-bold text-gray-900">{userStats.bills}</p>}
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 group relative hover:shadow-md transition">
            <p className="text-gray-400 text-sm font-medium mb-1">Total Sales</p>
            {isCurrentlyLoading && !stats ? <div className="h-8 w-24 bg-gray-100 animate-pulse rounded" /> : <p className="text-2xl font-bold text-gray-900">₹{(userStats.sales || 0).toLocaleString()}</p>}
            <button 
              onClick={() => openDrawer('Sale')}
              className="absolute top-4 right-4 p-1.5 bg-blue-50 text-blue-600 rounded-lg opacity-0 group-hover:opacity-100 transition"
            >
              <Plus size={16} />
            </button>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 group relative hover:shadow-md transition">
            <p className="text-gray-400 text-sm font-medium mb-1">Total Purchases</p>
            {isCurrentlyLoading && !stats ? <div className="h-8 w-24 bg-gray-100 animate-pulse rounded" /> : <p className="text-2xl font-bold text-gray-900">₹{(userStats.purchases || 0).toLocaleString()}</p>}
            <button 
              onClick={() => openDrawer('Purchase')}
              className="absolute top-4 right-4 p-1.5 bg-indigo-50 text-indigo-600 rounded-lg opacity-0 group-hover:opacity-100 transition"
            >
              <Plus size={16} />
            </button>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 group relative hover:shadow-md transition">
            <p className="text-gray-400 text-sm font-medium mb-1">Total Payments</p>
            {isCurrentlyLoading && !stats ? <div className="h-8 w-24 bg-gray-100 animate-pulse rounded" /> : <p className="text-2xl font-bold text-gray-900">₹{(userStats.payments || 0).toLocaleString()}</p>}
            <button 
              onClick={() => openDrawer('Payment')}
              className="absolute top-4 right-4 p-1.5 bg-green-50 text-green-600 rounded-lg opacity-0 group-hover:opacity-100 transition"
            >
              <Plus size={16} />
            </button>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 group relative hover:shadow-md transition overflow-hidden">
            <p className="text-gray-400 text-sm font-medium mb-1">Total Expenses</p>
            {isCurrentlyLoading && !stats ? (
              <div className="space-y-2">
                <div className="h-8 w-24 bg-gray-100 animate-pulse rounded" />
                <div className="h-4 w-32 bg-gray-50 animate-pulse rounded" />
              </div>
            ) : (
              <>
                <p className="text-2xl font-bold text-gray-900 mb-2">₹{(userStats.expenses || 0).toLocaleString()}</p>
                <div className="flex gap-2 text-[10px] font-bold uppercase">
                  <span className="text-green-600 bg-green-50 px-1.5 py-0.5 rounded">P: ₹{(userStats.expenses_paid || 0).toLocaleString()}</span>
                  <span className="text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded">C: ₹{(userStats.expenses_unpaid || 0).toLocaleString()}</span>
                </div>
              </>
            )}
            <button 
              onClick={() => openDrawer('Expense')}
              className="absolute top-4 right-4 p-1.5 bg-orange-50 text-orange-600 rounded-lg opacity-0 group-hover:opacity-100 transition"
            >
              <Plus size={16} />
            </button>
          </div>
        </div>

        {/* Drive Access Card */}
        <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm flex flex-col lg:flex-row items-center justify-between space-y-4 lg:space-y-0">
          <div className="flex items-center space-x-6">
            <div className="bg-blue-100 text-blue-600 p-4 rounded-xl">
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
    </>
  );
};

export default Dashboard;
