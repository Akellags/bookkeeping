import React, { useState, useRef, useEffect } from 'react';
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
  ArrowUpRight,
  Sparkles,
  ChevronRight,
  Calendar,
  User,
  Hash,
  IndianRupee,
  Percent,
  Tag,
  CreditCard,
  ArrowDownLeft
} from 'lucide-react';
import axios from 'axios';

const TransactionDrawer = ({ isOpen, onClose, onRefresh, whatsappId, initialCategory }) => {
  const [activeCategory, setActiveCategory] = useState(initialCategory); // 'Sale', 'Purchase', 'Expense', 'Payment'

  useEffect(() => {
    if (initialCategory) {
      setActiveCategory(initialCategory);
    }
  }, [initialCategory]);

  const [entryMethod, setEntryMethod] = useState(null); // 'ai' or 'manual'
  const [activeTab, setActiveTab] = useState('upload'); // for AI: 'upload' or 'text'
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
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

  const categories = [
    { id: 'Sale', label: 'Sale', icon: <ShoppingBag size={24} />, color: 'blue', desc: 'Money coming in' },
    { id: 'Purchase', label: 'Purchase', icon: <ShoppingCart size={24} />, color: 'indigo', desc: 'Stock or inventory' },
    { id: 'Expense', label: 'Expense', icon: <Wallet size={24} />, color: 'orange', desc: 'Rent, bills, staff' },
    { id: 'Payment', label: 'Payment', icon: <ArrowUpRight size={24} />, color: 'green', desc: 'Balance settlement' },
  ];

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
      reset();
    }
  }, [isOpen]);

  const reset = () => {
    setActiveCategory(null);
    setEntryMethod(null);
    setActiveTab('upload');
    setExtraction(null);
    setMediaUrl(null);
    setText('');
    setError(null);
    setSuccess(false);
    setFormData({
      transaction_type: 'Sale',
      date: new Date().toISOString().split('T')[0],
      party_name: '',
      party_gstin: '',
      invoice_no: '',
      total_amount: '',
      gst_rate: '18',
      category: '',
      payment_mode: 'Cash',
      payment_type: 'Incoming',
      reference_id: '',
      notes: ''
    });
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !whatsappId) return;

    setLoading(true);
    setError(null);
    const data = new FormData();
    data.append('file', file);

    try {
      const res = await axios.post(`/api/transactions/process-image?whatsapp_id=${whatsappId}`, data);
      setExtraction(res.data.extraction);
      setMediaUrl(res.data.media_url || `temp_${res.data.transaction_id}.jpg`);
    } catch (err) {
      setError('AI Extraction failed. Please try a clearer image.');
    } finally {
      setLoading(false);
    }
  };

  const handleTextSubmit = async () => {
    if (!text || !whatsappId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`/api/transactions/process-text?whatsapp_id=${whatsappId}&text=${text}`);
      setExtraction(res.data.extraction);
    } catch (err) {
      setError('Failed to process text. Try a natural sentence.');
    } finally {
      setLoading(false);
    }
  };

  const handleFinalSave = async () => {
    if (!whatsappId) return;
    
    // Simple Validation
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
      setTimeout(() => {
        onRefresh();
        onClose();
      }, 1500);
    } catch (err) {
      setError('Failed to save. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const renderField = (label, icon, key, type = 'text', options = null) => {
    const value = extraction ? extraction[key] : formData[key];
    const onChange = (val) => extraction ? setExtraction({...extraction, [key]: val}) : setFormData({...formData, [key]: val});

    return (
      <div className="space-y-1.5">
        <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
          {icon} {label}
        </label>
        {options ? (
          <select 
            value={value || options[0]} 
            onChange={(e) => onChange(e.target.value)}
            className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none font-bold appearance-none cursor-pointer"
          >
            {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        ) : (
          <input 
            type={type}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={`Enter ${label.toLowerCase()}`}
            className="w-full p-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none font-bold"
          />
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-[100] flex justify-end overflow-hidden">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px] transition-opacity animate-in fade-in"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="relative w-full max-w-lg bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-black text-gray-900 tracking-tight">
              {activeCategory ? `Add ${activeCategory}` : 'New Record'}
            </h2>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mt-0.5">
              {activeCategory ? activeCategory : 'Select Type'}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition text-gray-400">
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {success ? (
            <div className="h-full flex flex-col items-center justify-center space-y-4 animate-in zoom-in">
              <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center">
                <CheckCircle2 size={40} />
              </div>
              <div className="text-center">
                <h3 className="text-xl font-bold text-gray-900">Recorded Successfully</h3>
                <p className="text-gray-500">Google Sheet has been updated.</p>
              </div>
            </div>
          ) : !activeCategory ? (
            /* Step 1: Select Category */
            <div className="grid grid-cols-1 gap-4">
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className="group flex items-center p-5 rounded-2xl border border-gray-100 hover:border-blue-500 hover:bg-blue-50/30 transition text-left"
                >
                  <div className={`p-4 rounded-xl bg-${cat.color}-100 text-${cat.color}-600 group-hover:scale-110 transition`}>
                    {cat.icon}
                  </div>
                  <div className="ml-4 flex-1">
                    <h3 className="font-bold text-gray-900 text-lg">{cat.label}</h3>
                    <p className="text-sm text-gray-500 font-medium">{cat.desc}</p>
                  </div>
                  <ChevronRight size={20} className="text-gray-300 group-hover:text-blue-500 group-hover:translate-x-1 transition" />
                </button>
              ))}
            </div>
          ) : !entryMethod ? (
            /* Step 2: Select Method */
            <div className="space-y-6">
               <button
                  onClick={() => setEntryMethod('ai')}
                  className="w-full flex items-center p-6 rounded-[1rem] bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-xl shadow-blue-100 hover:scale-[1.02] transition"
                >
                  <div className="p-4 bg-white/20 rounded-xl mr-4">
                    <Sparkles size={28} />
                  </div>
                  <div className="text-left">
                    <h3 className="font-black text-lg leading-tight tracking-tight">Magic Add with AI</h3>
                    <p className="text-blue-100 text-xs font-bold uppercase tracking-wider">Snap Photo or Send Text</p>
                  </div>
                </button>

                <div className="relative py-2 flex items-center">
                  <div className="flex-grow border-t border-gray-100"></div>
                  <span className="flex-shrink mx-4 text-xs font-black text-gray-300 uppercase tracking-widest">OR</span>
                  <div className="flex-grow border-t border-gray-100"></div>
                </div>

                <button
                  onClick={() => setEntryMethod('manual')}
                  className="w-full flex items-center p-6 rounded-[1rem] border-2 border-dashed border-gray-200 text-gray-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50/50 transition"
                >
                  <div className="p-4 bg-gray-100 rounded-xl mr-4 text-gray-400 group-hover:text-blue-500">
                    <Type size={28} />
                  </div>
                  <div className="text-left">
                    <h3 className="font-bold text-lg leading-tight">Manual Entry</h3>
                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Fill details yourself</p>
                  </div>
                </button>
                
                <button onClick={() => setActiveCategory(null)} className="w-full py-4 text-gray-400 font-bold text-sm">
                  Back to selection
                </button>
            </div>
          ) : entryMethod === 'ai' && !extraction ? (
            /* AI Entry View */
            <div className="space-y-6">
              <div className="flex bg-gray-100 p-1.5 rounded-xl">
                <button 
                  onClick={() => setActiveTab('upload')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-3 rounded-lg font-bold text-sm transition ${activeTab === 'upload' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  <Upload size={18} />
                  <span>Scan Receipt</span>
                </button>
                <button 
                  onClick={() => setActiveTab('text')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-3 rounded-lg font-bold text-sm transition ${activeTab === 'text' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                >
                  <Type size={18} />
                  <span>Voice/Text</span>
                </button>
              </div>

              {activeTab === 'upload' ? (
                <div 
                  onClick={() => fileInputRef.current.click()}
                  className="border-2 border-dashed border-gray-200 rounded-[1.25rem] p-12 flex flex-col items-center justify-center space-y-4 hover:border-blue-400 hover:bg-blue-50/50 cursor-pointer transition group"
                >
                  <div className="w-20 h-20 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition">
                    {loading ? <Loader2 className="animate-spin" size={40} /> : <Upload size={40} />}
                  </div>
                  <div className="text-center">
                    <p className="font-bold text-gray-900 text-lg">Upload {activeCategory} Receipt</p>
                    <p className="text-gray-500 text-sm">PNG, JPG or PDF</p>
                  </div>
                  <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} accept="image/*,application/pdf" />
                </div>
              ) : (
                <div className="space-y-4">
                  <textarea 
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder={`E.g. Paid ${activeCategory === 'Sale' ? 'from' : 'to'} Rahul ₹2500 for ${activeCategory}...`}
                    className="w-full h-40 p-6 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none font-medium"
                  />
                  <button 
                    onClick={handleTextSubmit}
                    disabled={loading || !text}
                    className="w-full bg-blue-600 text-white font-bold py-4 rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center space-x-2"
                  >
                    {loading ? <Loader2 className="animate-spin" size={20} /> : <Sparkles size={20} />}
                    <span>AI Analysis</span>
                  </button>
                </div>
              )}
              <button onClick={() => setEntryMethod(null)} className="w-full text-gray-400 font-bold text-sm">Change method</button>
            </div>
          ) : (
            /* Form View (Manual or AI Review) */
            <div className="space-y-8 pb-32">
              {extraction && (
                <div className="bg-blue-50 p-4 rounded-xl flex items-center justify-between border border-blue-100">
                  <div className="flex items-center space-x-3 text-blue-700 font-bold text-xs uppercase tracking-tight">
                    <Sparkles size={14} />
                    <span>AI Review Mode</span>
                  </div>
                  <button onClick={() => setExtraction(null)} className="text-blue-600 text-xs font-bold underline">Manual Form</button>
                </div>
              )}

              <div className="space-y-6">
                {/* Common Field: Date */}
                {renderField('Transaction Date', <Calendar size={12} />, 'date', 'date')}

                {/* category Specific Fields */}
                {activeCategory === 'Sale' && (
                  <>
                    {renderField('Customer Name', <User size={12} />, 'party_name')}
                    <div className="grid grid-cols-2 gap-4">
                      {renderField('Invoice #', <Hash size={12} />, 'invoice_no')}
                      {renderField('Customer GSTIN', <Hash size={12} />, 'party_gstin')}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      {renderField('HSN Code', <Hash size={12} />, 'hsn_code')}
                      {renderField('HSN Description', <Tag size={12} />, 'hsn_description')}
                    </div>
                  </>
                )}

                {activeCategory === 'Purchase' && (
                  <>
                    {renderField('Supplier Name', <User size={12} />, 'party_name')}
                    <div className="grid grid-cols-2 gap-4">
                      {renderField('Bill / Inv #', <Hash size={12} />, 'invoice_no')}
                      {renderField('Supplier GSTIN', <Hash size={12} />, 'party_gstin')}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      {renderField('HSN Code', <Hash size={12} />, 'hsn_code')}
                      {renderField('HSN Description', <Tag size={12} />, 'hsn_description')}
                    </div>
                  </>
                )}

                {activeCategory === 'Expense' && (
                  <>
                    {renderField('Payee / Vendor', <User size={12} />, 'party_name')}
                    {renderField('Expense category', <Tag size={12} />, 'category', 'text', ['Rent', 'Utilities', 'Salary', 'Office Supplies', 'Marketing', 'Repairs', 'Other'])}
                    <div className="grid grid-cols-2 gap-4">
                      {renderField('HSN Code', <Hash size={12} />, 'hsn_code')}
                      {renderField('HSN Description', <Tag size={12} />, 'hsn_description')}
                    </div>
                  </>
                )}

                {activeCategory === 'Payment' && (
                  <>
                    <div className="bg-gray-100 p-1 rounded-2xl flex">
                      <button 
                        onClick={() => setFormData({...formData, payment_type: 'Incoming'})}
                        className={`flex-1 py-2 text-xs font-bold rounded-xl transition ${formData.payment_type === 'Incoming' ? 'bg-white text-green-600 shadow-sm' : 'text-gray-400'}`}
                      >
                        Payment In
                      </button>
                      <button 
                        onClick={() => setFormData({...formData, payment_type: 'Outgoing'})}
                        className={`flex-1 py-2 text-xs font-bold rounded-xl transition ${formData.payment_type === 'Outgoing' ? 'bg-white text-red-600 shadow-sm' : 'text-gray-400'}`}
                      >
                        Payment Out
                      </button>
                    </div>
                    {renderField(formData.payment_type === 'Incoming' ? 'Received From' : 'Paid To', <User size={12} />, 'party_name')}
                    {renderField('Reference / Trans ID', <Hash size={12} />, 'reference_id')}
                  </>
                )}

                {/* Common Amount and Mode */}
                <div className="grid grid-cols-2 gap-4">
                  {renderField('Amount', <IndianRupee size={12} />, 'total_amount', 'number')}
                  {activeCategory !== 'Payment' ? 
                    renderField('GST Rate', <Percent size={12} />, 'gst_rate', 'select', ['0', '5', '12', '18', '28']) :
                    renderField('Payment Mode', <CreditCard size={12} />, 'payment_mode', 'select', ['Cash', 'UPI', 'Bank Transfer', 'Cheque'])
                  }
                </div>

                {activeCategory !== 'Payment' && renderField('Payment Status', <Wallet size={12} />, 'payment_mode', 'select', ['Cash', 'Online', 'Bank', 'Credit'])}

                {renderField('Notes', <Type size={12} />, 'notes')}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {(activeCategory && (entryMethod === 'manual' || extraction)) && !success && (
          <div className="p-6 border-t border-gray-100 bg-white absolute bottom-0 left-0 right-0 z-10 shadow-[0_-10px_30px_-15px_rgba(0,0,0,0.1)]">
            {error && (
              <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-xl flex items-center space-x-2 text-xs font-bold animate-in slide-in-from-bottom-2">
                <AlertCircle size={14} />
                <span>{error}</span>
              </div>
            )}
            <button
              onClick={handleFinalSave}
              disabled={loading}
              className="w-full bg-blue-600 text-white font-bold py-5 rounded-[2rem] shadow-xl shadow-blue-100 hover:bg-blue-700 transition flex items-center justify-center space-x-2 active:scale-[0.98]"
            >
              {loading ? <Loader2 className="animate-spin" size={20} /> : <Save size={20} />}
              <span>{loading ? 'Processing...' : `Save ${activeCategory}`}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TransactionDrawer;
