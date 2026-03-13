import React, { useState, useRef } from 'react';
import { 
  X, 
  Upload, 
  Mic, 
  Type, 
  Loader2, 
  CheckCircle2,
  AlertCircle,
  Save
} from 'lucide-react';
import axios from 'axios';

const TransactionModal = ({ isOpen, onClose, onRefresh }) => {
  const [activeTab, setActiveTab] = useState('upload');
  const [loading, setLoading] = useState(false);
  const [extraction, setExtraction] = useState(null);
  const [mediaUrl, setMediaUrl] = useState(null);
  const [text, setText] = useState('');
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const whatsappId = localStorage.getItem('whatsapp_id') || '919703333319';

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post(`/api/transactions/process-image?whatsapp_id=${whatsappId}`, formData);
      setExtraction(res.data.extraction);
      setMediaUrl(res.data.media_url || `temp_${res.data.transaction_id}.jpg`);
    } catch (err) {
      setError('AI Extraction failed. Please try a clearer image.');
    } finally {
      setLoading(false);
    }
  };

  const handleTextSubmit = async () => {
    if (!text) return;
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`/api/transactions/process-text?whatsapp_id=${whatsappId}&text=${text}`);
      setExtraction(res.data.extraction);
    } catch (err) {
      setError('Failed to process text. Try: "Sold mask for 500 at 18% GST"');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await axios.post(`/api/transactions/save?whatsapp_id=${whatsappId}`, {
        extraction,
        media_url: mediaUrl
      });
      onRefresh();
      onClose();
      reset();
    } catch (err) {
      setError('Failed to save to Google Sheets.');
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setExtraction(null);
    setMediaUrl(null);
    setText('');
    setError(null);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-[2.5rem] w-full max-w-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
          <h2 className="text-xl font-bold text-gray-900">Record Transaction</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-full transition">
            <X size={20} />
          </button>
        </div>

        <div className="p-8">
          {!extraction ? (
            <>
              {/* Tabs */}
              <div className="flex space-x-2 mb-8 bg-gray-100 p-1 rounded-2xl">
                <button 
                  onClick={() => setActiveTab('upload')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl font-bold text-sm transition ${activeTab === 'upload' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  <Upload size={18} />
                  <span>Upload Bill</span>
                </button>
                <button 
                  onClick={() => setActiveTab('text')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl font-bold text-sm transition ${activeTab === 'text' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  <Type size={18} />
                  <span>Text/Voice</span>
                </button>
              </div>

              {activeTab === 'upload' ? (
                <div 
                  onClick={() => fileInputRef.current.click()}
                  className="border-2 border-dashed border-gray-200 rounded-[2rem] p-12 flex flex-col items-center justify-center space-y-4 hover:border-blue-400 hover:bg-blue-50/50 cursor-pointer transition group"
                >
                  <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition">
                    {loading ? <Loader2 className="animate-spin" size={32} /> : <Upload size={32} />}
                  </div>
                  <div className="text-center">
                    <p className="font-bold text-gray-900 text-lg">Click to upload bill photo</p>
                    <p className="text-gray-500 text-sm">PNG, JPG or PDF up to 10MB</p>
                  </div>
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    className="hidden" 
                    onChange={handleFileUpload}
                    accept="image/*,application/pdf"
                  />
                </div>
              ) : (
                <div className="space-y-4">
                  <textarea 
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="E.g. Sold 10 Masks to Apollo for 1500 at 12% GST"
                    className="w-full h-32 p-6 bg-gray-50 border border-gray-200 rounded-[2rem] focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none font-medium"
                  />
                  <button 
                    onClick={handleTextSubmit}
                    disabled={loading || !text}
                    className="w-full bg-blue-600 text-white font-bold py-4 rounded-2xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center space-x-2"
                  >
                    {loading ? <Loader2 className="animate-spin" size={20} /> : <CheckCircle2 size={20} />}
                    <span>{loading ? 'Processing with AI...' : 'Analyze Record'}</span>
                  </button>
                </div>
              )}

              {error && (
                <div className="mt-6 p-4 bg-red-50 border border-red-100 text-red-600 rounded-2xl flex items-center space-x-3 text-sm font-bold">
                  <AlertCircle size={18} />
                  <span>{error}</span>
                </div>
              )}
            </>
          ) : (
            <div className="space-y-6">
              <div className="bg-blue-50 p-4 rounded-2xl flex items-center justify-between border border-blue-100">
                <div className="flex items-center space-x-3 text-blue-700 font-bold">
                  <CheckCircle2 size={20} />
                  <span>AI Extraction Complete</span>
                </div>
                <button onClick={() => setExtraction(null)} className="text-blue-600 text-sm font-bold underline">Change</button>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100">
                  <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block mb-1">Type</label>
                  <select 
                    value={extraction.transaction_type}
                    onChange={(e) => setExtraction({...extraction, transaction_type: e.target.value})}
                    className="bg-transparent font-bold text-gray-900 border-none p-0 focus:ring-0 w-full"
                  >
                    <option value="Sale">Sale (Income)</option>
                    <option value="Purchase">Purchase (Expense)</option>
                  </select>
                </div>
                <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100">
                  <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block mb-1">Invoice No</label>
                  <input 
                    type="text" 
                    value={extraction.invoice_no}
                    onChange={(e) => setExtraction({...extraction, invoice_no: e.target.value})}
                    className="bg-transparent font-bold text-gray-900 border-none p-0 focus:ring-0 w-full"
                  />
                </div>
                <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100">
                  <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block mb-1">Total Amount</label>
                  <input 
                    type="number" 
                    value={extraction.total_amount}
                    onChange={(e) => setExtraction({...extraction, total_amount: parseFloat(e.target.value)})}
                    className="bg-transparent font-bold text-gray-900 border-none p-0 focus:ring-0 w-full"
                  />
                </div>
                <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100">
                  <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block mb-1">GST Rate (%)</label>
                  <input 
                    type="number" 
                    value={extraction.gst_rate}
                    onChange={(e) => setExtraction({...extraction, gst_rate: parseInt(e.target.value)})}
                    className="bg-transparent font-bold text-gray-900 border-none p-0 focus:ring-0 w-full"
                  />
                </div>
              </div>

              <button 
                onClick={handleSave}
                disabled={loading}
                className="w-full bg-blue-600 text-white font-bold py-5 rounded-[2rem] shadow-xl shadow-blue-200 hover:bg-blue-700 transition flex items-center justify-center space-x-2"
              >
                {loading ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
                <span>{loading ? 'Saving...' : 'Confirm & Save to Ledger'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TransactionModal;
