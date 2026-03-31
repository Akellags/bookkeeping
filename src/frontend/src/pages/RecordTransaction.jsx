import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  X, 
  Upload, 
  Type, 
  Loader2, 
  CheckCircle2,
  AlertCircle,
  Save,
  ShoppingBag,
  ShoppingCart,
  Wallet,
  Sparkles,
  Calendar,
  User,
  Hash,
  IndianRupee,
  Percent,
  Tag,
  CreditCard,
  ArrowUpRight,
  ArrowLeft,
  ArrowRight,
  RefreshCcw,
  Mic,
  Square,
  Trash2
} from 'lucide-react';
import axios from 'axios';
import { useUser } from '../context/UserContext';

const RecordTransaction = () => {
  const navigate = useNavigate();
  const { whatsappId, refreshStats } = useUser();
  
  const [activeCategory, setActiveCategory] = useState('Sale'); // 'Sale', 'Purchase', 'Expense', 'Payment'
  const [entryMethod, setEntryMethod] = useState('manual'); // Default to manual for full page
  const [activeTab, setActiveTab] = useState('upload'); // for AI: 'upload' or 'text'
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [showToast, setShowToast] = useState(false);
  
  // Form States
  const [formData, setFormData] = useState({
    transaction_type: 'Sale',
    date: new Date().toISOString().split('T')[0],
    party_name: '',
    party_gstin: '',
    invoice_no: '',
    total_amount: '',
    gst_rate: '18',
    hsn_code: '',
    hsn_description: '',
    category: '', // For Expenses
    payment_mode: 'Cash',
    payment_type: 'Incoming', // For Payments
    reference_id: '', // For Payments
    notes: ''
  });

  const [extraction, setExtraction] = useState(null);
  const [mediaUrl, setMediaUrl] = useState(null);
  const [text, setText] = useState('');
  const fileInputRef = useRef(null);
  
  // Voice Recording
  const [isRecording, setIsRecording] = useState(false);
  const [recordTime, setRecordTime] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordTime(prev => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
      setRecordTime(0);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        handleVoiceUpload(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setError(null);
    } catch (err) {
      setError("Microphone access denied or not available.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleVoiceUpload = async (audioBlob) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.webm');
      
      const response = await axios.post(`/api/transactions/process-voice?whatsapp_id=${whatsappId}`, formData);
      setExtraction(response.data.extraction);
      setText(response.data.transcript);
      setEntryMethod('ai');
    } catch (err) {
      setError('Failed to process voice. Try typing instead.');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      transaction_type: activeCategory,
      date: new Date().toISOString().split('T')[0],
      party_name: '',
      party_gstin: '',
      invoice_no: '',
      total_amount: '',
      gst_rate: '18',
      hsn_code: '',
      hsn_description: '',
      category: '',
      payment_mode: 'Cash',
      payment_type: 'Incoming',
      reference_id: '',
      notes: ''
    });
    setExtraction(null);
    setMediaUrl(null);
    setText('');
    setSuccess(false);
    setError(null);
  };

  const categories = [
    { id: 'Sale', label: 'Sale', icon: <ShoppingBag size={20} />, color: 'blue', desc: 'Income' },
    { id: 'Purchase', label: 'Purchase', icon: <ShoppingCart size={20} />, color: 'indigo', desc: 'Inventory' },
    { id: 'Expense', label: 'Expense', icon: <Wallet size={20} />, color: 'orange', desc: 'Bills' },
    { id: 'Payment', label: 'Payment', icon: <ArrowUpRight size={20} />, color: 'green', desc: 'Balance' },
  ];

  useEffect(() => {
    setFormData(prev => ({ ...prev, transaction_type: activeCategory }));
  }, [activeCategory]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(`/api/transactions/upload?whatsapp_id=${whatsappId}`, formData);
      setExtraction(response.data.extraction);
      setMediaUrl(response.data.media_url);
      setEntryMethod('ai');
    } catch (err) {
      setError('Failed to process receipt. Please try manual entry.');
    } finally {
      setLoading(false);
    }
  };

  const handleTextSubmit = async () => {
    if (!text) return;
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`/api/transactions/process-text?whatsapp_id=${whatsappId}`, { text });
      setExtraction(response.data.extraction);
      setEntryMethod('ai');
    } catch (err) {
      setError('AI could not understand the text. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleFinalSave = async () => {
    if (!whatsappId) return;
    
    const currentData = extraction || formData;
    if (!currentData.party_name || !currentData.total_amount) {
      setError('Please fill Name and Amount');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = extraction ? {
        extraction,
        media_url: mediaUrl
      } : {
        extraction: {
          ...formData,
          transaction_type: activeCategory
        }
      };

      await axios.post(`/api/transactions/save?whatsapp_id=${whatsappId}`, payload);
      setSuccess(true);
      setShowToast(true);
      refreshStats();
      setTimeout(() => setShowToast(false), 5000);
    } catch (err) {
      setError('Failed to save. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const renderField = (label, icon, key, type = 'text', options = null) => {
    const value = extraction ? extraction[key] : formData[key];
    const onChange = (val) => extraction ? setExtraction({...extraction, [key]: val}) : setFormData({...formData, [key]: val});

    return (
      <div className="space-y-2">
        <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
          {icon} {label}
        </label>
        {options ? (
          <select 
            value={value || options[0]} 
            onChange={(e) => onChange(e.target.value)}
            className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 outline-none font-bold appearance-none cursor-pointer transition shadow-sm"
          >
            {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        ) : (
          <input 
            type={type}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={`Enter ${label.toLowerCase()}`}
            className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 outline-none font-bold transition shadow-sm"
          />
        )}
      </div>
    );
  };

  if (false) { // Success logic moved to inline toast and buttons
    return null;
  }

  return (
    <div className="max-w-6xl mx-auto pb-20 relative">
      {/* Success Toast */}
      {showToast && (
        <div className="fixed top-24 right-10 z-[110] animate-in slide-in-from-right duration-500">
          <div className="bg-green-600 text-white px-8 py-4 rounded-xl shadow-2xl flex items-center space-x-3 border border-green-500">
            <CheckCircle2 size={24} />
            <div>
              <p className="font-black uppercase tracking-widest text-xs">Success</p>
              <p className="font-bold">Record added to {activeCategory}s</p>
            </div>
          </div>
        </div>
      )}

      {/* Tabs & Method Toggle Row */}
      <div className="flex flex-col lg:flex-row items-center justify-between gap-6 mb-10">
        {/* Category Tabs (Left Aligned) */}
        <div className="flex bg-gray-100 p-1.5 rounded-[1rem] w-full lg:w-auto">
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => {
                setActiveCategory(cat.id);
                resetForm();
              }}
              className={`flex-1 lg:flex-none flex items-center justify-center space-x-2 px-6 py-3 rounded-[0.75rem] font-black text-xs uppercase tracking-widest transition ${
                activeCategory === cat.id 
                ? `bg-white text-${cat.color}-600 shadow-sm` 
                : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {cat.icon}
              <span className="hidden sm:inline">{cat.label}</span>
            </button>
          ))}
        </div>

        {/* Input Method Toggle (Right Aligned) */}
        <div className="bg-gray-100 p-1.5 rounded-[1rem] flex w-full lg:w-auto">
          <button 
            onClick={() => setEntryMethod('manual')}
            className={`flex-1 lg:px-8 py-3 rounded-[0.75rem] font-black text-xs uppercase tracking-widest transition ${entryMethod === 'manual' ? 'bg-blue-600 text-white shadow-md' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Manual
          </button>
          <button 
            onClick={() => setEntryMethod('ai')}
            className={`flex-1 lg:px-8 py-3 rounded-[0.75rem] font-black text-xs uppercase tracking-widest transition ${entryMethod === 'ai' ? 'bg-blue-600 text-white shadow-md' : 'text-gray-500 hover:text-gray-700'}`}
          >
            AI Magic
          </button>
        </div>
      </div>

      <div className="space-y-10">
        {/* AI Input Section (Full Width Symmetrical Layout) */}
        {entryMethod === 'ai' && (
          <div className="bg-white rounded-[1.25rem] border border-gray-100 shadow-sm overflow-hidden animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="grid grid-cols-1 lg:grid-cols-3">
              {/* Left Side: Controls */}
              <div className="lg:col-span-1 p-8 border-b lg:border-b-0 lg:border-r border-gray-100 space-y-6">
                <div className="flex bg-gray-100 p-1.5 rounded-xl">
                  <button 
                    onClick={() => setActiveTab('upload')}
                    className={`flex-1 flex items-center justify-center space-x-2 py-3 rounded-lg font-bold text-xs transition uppercase tracking-widest ${activeTab === 'upload' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    <Upload size={14} />
                    <span>Scan Receipt</span>
                  </button>
                  <button 
                    onClick={() => setActiveTab('text')}
                    className={`flex-1 flex items-center justify-center space-x-2 py-3 rounded-lg font-bold text-xs transition uppercase tracking-widest ${activeTab === 'text' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    <Type size={14} />
                    <span>Voice/Text</span>
                  </button>
                </div>

                {activeTab === 'upload' ? (
                  <div 
                    onClick={() => fileInputRef.current.click()}
                    className="border-2 border-dashed border-gray-200 rounded-2xl p-10 flex flex-col items-center justify-center space-y-4 hover:border-blue-400 hover:bg-blue-50 transition group cursor-pointer"
                  >
                    <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition">
                      {loading ? <Loader2 className="animate-spin" size={30} /> : <Upload size={30} />}
                    </div>
                    <div className="text-center">
                      <p className="font-black text-gray-900 text-sm">Upload Receipt</p>
                      <p className="text-gray-400 text-[10px] uppercase font-black">PNG, JPG or PDF</p>
                    </div>
                    <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} accept="image/*,application/pdf" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="relative">
                      <textarea 
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder={`E.g. Paid ${activeCategory === 'Sale' ? 'from' : 'to'} Rahul ₹2500...`}
                        className="w-full h-32 p-4 bg-gray-50 border border-gray-100 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition resize-none font-medium text-sm"
                      />
                      {isRecording && (
                        <div className="absolute inset-0 bg-blue-600/90 rounded-xl flex flex-col items-center justify-center text-white space-y-3 animate-in fade-in duration-300">
                          <div className="flex items-center space-x-3">
                            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                            <span className="font-black text-lg tracking-widest">
                              {Math.floor(recordTime / 60)}:{(recordTime % 60).toString().padStart(2, '0')}
                            </span>
                          </div>
                          <p className="text-[10px] font-black uppercase tracking-widest opacity-80">Recording Voice...</p>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      {isRecording ? (
                        <button 
                          onClick={stopRecording}
                          className="flex-1 bg-red-600 text-white font-black py-4 rounded-xl shadow-lg shadow-red-100 hover:bg-red-700 transition flex items-center justify-center space-x-2 uppercase tracking-widest text-xs"
                        >
                          <Square size={16} fill="white" />
                          <span>Stop & Analyze</span>
                        </button>
                      ) : (
                        <>
                          <button 
                            onClick={startRecording}
                            className="flex-none bg-blue-50 text-blue-600 p-4 rounded-xl hover:bg-blue-100 transition"
                            title="Record Voice"
                          >
                            <Mic size={20} />
                          </button>
                          <button 
                            onClick={handleTextSubmit}
                            disabled={loading || !text}
                            className="flex-1 bg-blue-600 text-white font-black py-4 rounded-xl shadow-lg shadow-blue-100 hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center space-x-2 uppercase tracking-widest text-xs"
                          >
                            {loading ? <Loader2 className="animate-spin" size={16} /> : <Sparkles size={16} />}
                            <span>AI Analysis</span>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Right Side: Banner / Status */}
              <div className={`lg:col-span-2 p-10 flex flex-col justify-center relative overflow-hidden transition-colors duration-500 ${extraction ? 'bg-gradient-to-br from-blue-600 to-indigo-700 text-white' : 'bg-gray-50/50'}`}>
                {extraction ? (
                  <>
                    <div className="absolute top-0 right-0 p-8 opacity-10">
                      <Sparkles size={120} />
                    </div>
                    <div className="relative z-10">
                      <div className="flex items-center space-x-3 mb-4">
                        <Sparkles size={24} className="text-blue-200" />
                        <h3 className="text-xl font-black tracking-tight uppercase tracking-widest">AI Insights Ready</h3>
                      </div>
                      <p className="text-blue-100 text-lg font-medium leading-relaxed max-w-xl">
                        I've extracted the details from your {activeTab === 'upload' ? 'receipt' : 'text'}. 
                        Please review the form below and hit save to record this {activeCategory}.
                      </p>
                      <button 
                        onClick={() => {
                          setExtraction(null);
                          setEntryMethod('manual');
                        }}
                        className="mt-8 text-[10px] font-black uppercase tracking-widest bg-white/10 hover:bg-white/20 px-6 py-3 rounded-lg transition border border-white/20"
                      >
                        Discard AI Data
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="relative z-10 text-center lg:text-left max-w-md">
                    <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center mb-6 mx-auto lg:mx-0">
                      <Sparkles size={32} />
                    </div>
                    <h3 className="text-xl font-black text-gray-900 uppercase tracking-widest mb-3">AI Magic Scanner</h3>
                    <p className="text-gray-500 font-medium leading-relaxed">
                      Upload a photo of your receipt or type a natural sentence. Our AI will automatically extract the party name, items, and taxes for you.
                    </p>
                    <div className="mt-8 flex items-center space-x-6 text-[10px] font-black uppercase tracking-[0.2em] text-gray-400">
                       <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-green-500"></div> No Manual Entry</span>
                       <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div> GSTR-1 Ready</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Main Form (Full Real Estate) */}
        <div className="bg-white rounded-[1.25rem] border border-gray-100 shadow-sm overflow-hidden">
          <div className="p-8 lg:p-12">
            <div className="space-y-12">
              {/* Unified Horizontal Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-12 gap-y-10">
                
                {/* Row 1: Basic Info */}
                <div className="lg:col-span-3">
                  <h3 className="text-[10px] font-black text-blue-600 uppercase tracking-[0.3em] mb-6 border-b border-blue-50 pb-2">1. Party & Reference</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {renderField('Transaction Date', <Calendar size={12} />, 'date', 'date')}
                    
                    {activeCategory === 'Payment' ? (
                      <div className="space-y-2">
                        <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                          <CreditCard size={12} /> Direction
                        </label>
                        <div className="bg-gray-50 p-1 rounded-xl flex border border-gray-100">
                          <button 
                            onClick={() => setFormData({...formData, payment_type: 'Incoming'})}
                            className={`flex-1 py-3 text-[10px] font-black uppercase tracking-widest rounded-lg transition ${formData.payment_type === 'Incoming' ? 'bg-white text-green-600 shadow-sm' : 'text-gray-400'}`}
                          >
                            Money In
                          </button>
                          <button 
                            onClick={() => setFormData({...formData, payment_type: 'Outgoing'})}
                            className={`flex-1 py-3 text-[10px] font-black uppercase tracking-widest rounded-lg transition ${formData.payment_type === 'Outgoing' ? 'bg-white text-red-600 shadow-sm' : 'text-gray-400'}`}
                          >
                            Money Out
                          </button>
                        </div>
                      </div>
                    ) : (
                      renderField(activeCategory === 'Sale' ? 'Customer Name' : activeCategory === 'Purchase' ? 'Supplier Name' : 'Payee / Vendor', <User size={12} />, 'party_name')
                    )}

                    {activeCategory === 'Payment' ? (
                      renderField(formData.payment_type === 'Incoming' ? 'Received From' : 'Paid To', <User size={12} />, 'party_name')
                    ) : (
                      renderField(activeCategory === 'Sale' ? 'Customer GSTIN' : activeCategory === 'Purchase' ? 'Supplier GSTIN' : 'Expense category', <Hash size={12} />, activeCategory === 'Expense' ? 'category' : 'party_gstin', activeCategory === 'Expense' ? 'text' : 'text', activeCategory === 'Expense' ? ['Rent', 'Utilities', 'Salary', 'Office Supplies', 'Marketing', 'Repairs', 'Other'] : null)
                    )}
                  </div>
                </div>

                {/* Row 2: Item & Tax (Skip for Payment) */}
                {activeCategory !== 'Payment' && (
                  <div className="lg:col-span-3">
                    <h3 className="text-[10px] font-black text-blue-600 uppercase tracking-[0.3em] mb-6 border-b border-blue-50 pb-2">2. Item & Tax Details</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-3 gap-8">
                      {renderField('Invoice #', <Hash size={12} />, 'invoice_no')}
                      {renderField('HSN Code', <Hash size={12} />, 'hsn_code')}
                      {renderField('HSN Description', <Tag size={12} />, 'hsn_description')}
                    </div>
                  </div>
                )}

                {/* Row 3: Financials */}
                <div className="lg:col-span-3">
                  <h3 className="text-[10px] font-black text-blue-600 uppercase tracking-[0.3em] mb-6 border-b border-blue-50 pb-2">{activeCategory === 'Payment' ? '2. Payment Details' : '3. Financials'}</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {renderField('Total Amount', <IndianRupee size={12} />, 'total_amount', 'number')}
                    
                    {activeCategory === 'Payment' ? (
                      <>
                        {renderField('Reference / Trans ID', <Hash size={12} />, 'reference_id')}
                        {renderField('Payment Mode', <CreditCard size={12} />, 'payment_mode', 'select', ['Cash', 'UPI', 'Bank Transfer', 'Cheque'])}
                      </>
                    ) : (
                      <>
                        {renderField('GST Rate', <Percent size={12} />, 'gst_rate', 'select', ['0', '5', '12', '18', '28'])}
                        {renderField('Payment Status', <Wallet size={12} />, 'payment_mode', 'select', ['Cash', 'Online', 'Bank', 'Credit'])}
                      </>
                    )}
                  </div>
                </div>

                {/* Row 4: Notes */}
                <div className="lg:col-span-3">
                  {renderField('Notes', <Type size={12} />, 'notes')}
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="mt-16 pt-10 border-t border-gray-100 flex flex-col sm:flex-row items-center justify-between gap-6">
              {error && (
                <div className="flex-1 p-4 bg-red-50 text-red-600 rounded-xl flex items-center space-x-2 text-xs font-bold w-full">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}
              
              <div className="flex items-center space-x-4 w-full sm:w-auto ml-auto">
                {success ? (
                  <>
                    <button
                      onClick={() => navigate('/dashboard')}
                      className="flex-1 sm:flex-none text-gray-500 font-black uppercase tracking-widest text-xs py-5 px-8 hover:bg-gray-50 rounded-xl transition flex items-center justify-center space-x-2"
                    >
                      <ArrowLeft size={16} />
                      <span>Go to Dashboard</span>
                    </button>
                    <button
                      onClick={resetForm}
                      className="flex-1 sm:flex-none bg-green-600 text-white font-black py-5 px-12 rounded-[1rem] shadow-xl shadow-green-100 hover:bg-green-700 transition flex items-center justify-center space-x-3 active:scale-[0.98] uppercase tracking-[0.2em] text-xs"
                    >
                      <RefreshCcw size={18} />
                      <span>Add Another {activeCategory}</span>
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => navigate('/dashboard')}
                      className="flex-1 sm:flex-none text-gray-400 font-black uppercase tracking-widest text-xs py-5 px-8 hover:text-gray-600 transition"
                    >
                      Discard
                    </button>
                    <button
                      onClick={handleFinalSave}
                      disabled={loading}
                      className="flex-1 sm:flex-none bg-blue-600 text-white font-black py-5 px-12 rounded-[1rem] shadow-xl shadow-blue-100 hover:bg-blue-700 transition flex items-center justify-center space-x-3 active:scale-[0.98] uppercase tracking-[0.2em] text-xs"
                    >
                      {loading ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                      <span>{loading ? 'Processing...' : `Save ${activeCategory}`}</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecordTransaction;
