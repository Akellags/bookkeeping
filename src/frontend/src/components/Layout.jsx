import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  Settings, 
  LogOut,
  Building,
  ChevronDown,
  Plus,
  ArrowLeft
} from 'lucide-react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import axios from 'axios';
import { useUser } from '../context/UserContext';

const Layout = ({ children }) => {
  const { userStats, businesses, whatsappId, fetchUserStats, fetchBusinesses, logout } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const [showSwitch, setShowSwitch] = useState(false);

  const isRecordPage = location.pathname === '/transactions/new';

  const handleSwitch = async (businessId) => {
    try {
      await axios.post(`/api/user/businesses/switch?whatsapp_id=${whatsappId}&business_id=${businessId}`);
      await fetchUserStats();
      setShowSwitch(false);
    } catch (error) {
      console.error('Switch failed:', error);
    }
  };

  const handleAddBusiness = async () => {
    const name = prompt("Enter Business Name:");
    const gstin = prompt("Enter Business GSTIN:");
    if (name && gstin) {
      try {
        await axios.post(`/api/user/businesses/add?whatsapp_id=${whatsappId}&business_name=${name}&business_gstin=${gstin}`);
        await Promise.all([fetchUserStats(), fetchBusinesses()]);
        setShowSwitch(false);
      } catch (error) {
        console.error('Add business failed:', error);
      }
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post('/api/auth/logout');
      logout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
      logout();
      navigate('/');
    }
  };

  const navItems = [
    { name: 'Dashboard', icon: <LayoutDashboard size={20} />, path: '/dashboard' },
    { name: 'GST Reports', icon: <FileText size={20} />, path: '/reports' },
    { name: 'Settings', icon: <Settings size={20} />, path: '/settings' },
  ];

  return (
    <div className="bg-gray-50 flex flex-col md:flex-row min-h-screen font-inter">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-white border-r border-gray-200 p-6 flex flex-col space-y-8">
        <div className="flex items-center space-x-3">
          <div className="bg-blue-600 text-white p-2 rounded-md font-bold">HU</div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Help U</h1>
        </div>
        
        {/* Business Switcher */}
        <div className="relative">
          <button 
            onClick={() => setShowSwitch(!showSwitch)}
            className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100 hover:border-blue-200 transition"
          >
            <div className="flex items-center space-x-2 overflow-hidden text-left">
              <Building size={16} className="text-blue-600 flex-shrink-0" />
              <span className="text-sm font-bold truncate text-gray-700">
                {userStats?.business_name || 'Select Business'}
              </span>
            </div>
            <ChevronDown size={14} className={`text-gray-400 transform transition ${showSwitch ? 'rotate-180' : ''}`} />
          </button>
          
          {showSwitch && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-100 shadow-xl rounded-lg z-50 overflow-hidden py-1">
              {businesses.map(b => (
                <button
                  key={b.id}
                  onClick={() => handleSwitch(b.id)}
                  className={`w-full text-left px-4 py-2.5 text-sm font-semibold hover:bg-blue-50 transition flex items-center justify-between ${userStats?.business_id === b.id ? 'text-blue-600 bg-blue-50/50' : 'text-gray-600'}`}
                >
                  <span className="truncate">{b.name}</span>
                  {userStats?.business_id === b.id && <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>}
                </button>
              ))}
              <button
                onClick={handleAddBusiness}
                className="w-full text-left px-4 py-2.5 text-sm font-bold text-blue-600 hover:bg-blue-50 transition border-t border-gray-50 flex items-center space-x-2"
              >
                <Plus size={14} />
                <span>Add Merchant</span>
              </button>
            </div>
          )}
        </div>
        
        <nav className="flex-1 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.name}
              to={item.path}
              className={`flex items-center space-x-3 p-3 rounded-lg transition font-semibold ${
                location.pathname === item.path 
                ? 'bg-blue-50 text-blue-700' 
                : 'text-gray-500 hover:bg-gray-50'
              }`}
            >
              {item.icon}
              <span>{item.name}</span>
            </Link>
          ))}
          <button 
            onClick={handleLogout}
            className="flex items-center space-x-3 text-red-500 hover:bg-red-50 p-3 rounded-lg transition w-full text-left font-semibold"
          >
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </nav>

        <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl p-4 text-white">
          <p className="text-xs opacity-75 mb-1">Current Plan</p>
          <p className="font-bold mb-3">Free Trial (7 Days)</p>
          <button className="bg-white text-blue-600 text-xs font-bold py-2 px-4 rounded-md w-full">Upgrade Now</button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8">
        <header className="flex justify-between items-center mb-10">
          <div className="flex items-center space-x-4">
            {isRecordPage && (
              <button 
                onClick={() => navigate('/dashboard')}
                className="p-2.5 hover:bg-gray-100 rounded-full transition text-gray-500 border border-gray-100 shadow-sm"
              >
                <ArrowLeft size={22} />
              </button>
            )}
            <div>
              <h2 className="text-2xl font-black text-gray-900 tracking-tight">
                {isRecordPage ? 'Record Transaction' : (navItems.find(i => i.path === location.pathname)?.name || 'Dashboard')}
              </h2>
              <p className="text-sm font-bold text-gray-400 uppercase tracking-widest mt-0.5">
                {isRecordPage ? 'Add new data to your ledger' : `Welcome back, ${userStats?.google_email || 'User'}`}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4 text-right">
            <div>
              <p className="text-sm font-bold text-gray-900">+{userStats?.whatsapp_id || '91XXXX'}</p>
              <div className="flex items-center justify-end space-x-1 text-green-600">
                <span className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></span>
                <span className="text-xs font-semibold">Linked & Active</span>
              </div>
            </div>
            <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${userStats?.whatsapp_id}`} className="w-12 h-12 bg-gray-200 rounded-full border-2 border-white shadow-sm" alt="Avatar" />
          </div>
        </header>

        {children}
      </main>
    </div>
  );
};

export default Layout;
