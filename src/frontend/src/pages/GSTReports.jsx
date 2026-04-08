import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Download, 
  Filter,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { useUser } from '../context/UserContext';

const GSTReports = () => {
  const { userStats: globalUserStats, whatsappId } = useUser();
  const [reportData, setReportData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const [year, month, day] = dateStr.split('-');
    return `${day}-${month}-${year}`;
  };

  const handleDownload = async () => {
    try {
      setDownloading(true);
      if (!whatsappId) return;
      
      // Use absolute URL for the request if apiBaseUrl exists
      const endpoint = `/api/user/reports/download?whatsapp_id=${whatsappId}`;
      let url = apiBaseUrl ? `${apiBaseUrl}${endpoint}` : endpoint;
      
      if (dateRange.start) url += `&start_date=${formatDate(dateRange.start)}`;
      if (dateRange.end) url += `&end_date=${formatDate(dateRange.end)}`;
      const response = await axios.get(url);
      
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const urlBlob = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = urlBlob;
      link.setAttribute('download', `GSTR1_${dateRange.start || 'All'}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Download failed:', err);
      alert('Failed to generate GSTR-1 JSON. Make sure you have recorded sales transactions.');
    } finally {
      setDownloading(false);
    }
  };

  const downloadInvoice = (invoiceNo) => {
    if (!whatsappId) return;
    // Ensure absolute URL for window.open to avoid SPA routing capture
    const baseUrl = apiBaseUrl || window.location.origin.replace('-fe-', '-be-'); 
    const url = `${baseUrl}/api/user/invoice/pdf?whatsapp_id=${whatsappId}&invoice_no=${invoiceNo}`;
    console.log('Opening PDF:', url);
    window.open(url, '_blank');
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        if (!whatsappId) {
           setLoading(false);
           return;
        }
        
        let statsUrl = `/api/user/stats?whatsapp_id=${whatsappId}`;
        let reportsUrl = `/api/user/reports?whatsapp_id=${whatsappId}`;
        
        const params = [];
        if (dateRange.start) params.push(`start_date=${formatDate(dateRange.start)}`);
        if (dateRange.end) params.push(`end_date=${formatDate(dateRange.end)}`);
        
        if (params.length > 0) {
          statsUrl += `&${params.join('&')}`;
          reportsUrl += `&${params.join('&')}`;
        }

        const [reportRes] = await Promise.all([
          axios.get(reportsUrl)
        ]);
        setReportData(reportRes.data.rows || []);
      } catch (err) {
        console.error('Error fetching report data:', err);
        setError('Failed to load report data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [dateRange, whatsappId, globalUserStats?.business_id]);

  if (loading && reportData.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
      </div>
    );
  }

  // Header is index 0
  const headers = reportData[0] || [];
  const rows = reportData.slice(1);

  return (
    <div className="space-y-6 max-w-full overflow-hidden">
      {/* Filters & Actions */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-4 rounded-2xl border border-gray-100 shadow-sm">
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <div className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg border border-gray-200">
            <span className="text-xs font-bold text-gray-400 uppercase">From</span>
            <input 
              type="date" 
              value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
              className="text-sm font-semibold text-gray-700 bg-transparent border-none focus:ring-0 cursor-pointer" 
            />
          </div>
          <div className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg border border-gray-200">
            <span className="text-xs font-bold text-gray-400 uppercase">To</span>
            <input 
              type="date" 
              value={dateRange.end}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
              className="text-sm font-semibold text-gray-700 bg-transparent border-none focus:ring-0 cursor-pointer" 
            />
          </div>
          <p className="text-sm text-gray-500">{rows.length} transactions found</p>
        </div>
        <button 
          onClick={handleDownload}
          disabled={downloading}
          className="flex items-center space-x-2 bg-blue-600 text-white font-bold py-2.5 px-5 rounded-xl hover:bg-blue-700 transition shadow-sm disabled:opacity-50"
        >
          {downloading ? <Loader2 className="animate-spin" size={18} /> : <Download size={18} />}
          <span>{downloading ? 'Generating...' : 'Download GSTR-1 (JSON)'}</span>
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-100 text-red-600 p-4 rounded-xl flex items-center space-x-3">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Table Container */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden w-full">
        <div className="overflow-auto max-h-[calc(100vh-220px)]">
          <table className="w-full text-left border-collapse min-w-full">
            <thead className="sticky top-0 z-10 bg-gray-50 shadow-sm">
              <tr className="border-b border-gray-100">
                <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider whitespace-nowrap bg-gray-50">
                  Action
                </th>
                {headers.map((header, i) => (
                  <th key={i} className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider whitespace-nowrap bg-gray-50">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={headers.length + 1} className="px-6 py-10 text-center text-gray-500">
                    No transactions recorded yet. Start by sending a bill photo to WhatsApp!
                  </td>
                </tr>
              ) : (
                rows.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50 transition">
                    <td className="px-6 py-4 text-sm">
                      {row[8] === 'Sale' && (
                        <button 
                          onClick={() => downloadInvoice(row[2])}
                          className="text-blue-600 hover:text-blue-800 font-bold"
                        >
                          PDF
                        </button>
                      )}
                    </td>
                    {row.map((cell, j) => (
                      <td key={j} className="px-6 py-4 text-sm text-gray-700 whitespace-nowrap">
                        {j === 4 ? `₹${Number(cell).toLocaleString()}` : cell}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default GSTReports;
