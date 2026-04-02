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
  Trash2,
  Plus,
  Box,
  FileText
} from 'lucide-react';
import axios from 'axios';
import { useUser } from '../context/UserContext';

const RecordTransaction = () => {
  const navigate = useNavigate();
  const { whatsappId, fetchUserStats } = useUser();
  
  const [activeCategory, setActiveCategory] = useState('Sale'); // 'Sale', 'Purchase', 'Expense', 'Payment'
  const [entryMethod, setEntryMethod] = useState('manual'); 
  const [activeTab, setActiveTab] = useState('upload'); 
  
  const [loading, setLoading] = useState(false);
  const [processingFile, setProcessingFile] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState({ title: '', body: '' });
  
  // Modern Table-based Form State
  const [formData, setFormData] = useState({
    transaction_type: 'Sale',
    date: new Date().toISOString().split('T')[0],
    party_name: '',
    party_gstin: '',
    invoice_no: '',
    place_of_supply: '',
    reverse_charge: 'N',
    items: [
      { 
        hsn_code: '', 
        hsn_description: '', 
        uqc: 'PCS', 
        quantity: 1, 
        unit_price: 0, 
        gst_rate: 18, 
        taxable_value: 0, 
        cgst: 0, 
        sgst: 0, 
        igst: 0, 
        total_amount: 0 
      }
    ],
    total_amount: 0,
    category: '', 
    payment_mode: 'Cash',
    payment_type: 'Incoming', 
    reference_id: '', 
    notes: ''
  });

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

  // Recalculate totals whenever items change
  useEffect(() => {
    const total = formData.items.reduce((sum, item) => sum + (parseFloat(item.total_amount) || 0), 0);
    setFormData(prev => ({ ...prev, total_amount: total.toFixed(2) }));
  }, [formData.items]);

  const handleItemChange = (index, field, value) => {
    const newItems = [...formData.items];
    const item = { ...newItems[index], [field]: value };
    
    // Auto-calculate values based on change
    if (field === 'unit_price' || field === 'quantity' || field === 'gst_rate') {
      const qty = parseFloat(item.quantity) || 0;
      const price = parseFloat(item.unit_price) || 0;
      const rate = parseFloat(item.gst_rate) || 0;
      
      const lineTaxable = price * qty;
      const totalTax = (lineTaxable * rate) / 100;
      
      item.taxable_value = lineTaxable.toFixed(2);
      item.cgst = (totalTax / 2).toFixed(2);
      item.sgst = (totalTax / 2).toFixed(2);
      item.igst = 0;
      item.total_amount = (lineTaxable + totalTax).toFixed(2);
    } else if (field === 'taxable_value') {
      // If user edits total taxable value directly, update total_amount
      const taxableVal = parseFloat(value) || 0;
      const rate = parseFloat(item.gst_rate) || 0;
      const totalTax = (taxableVal * rate) / 100;
      item.total_amount = (taxableVal + totalTax).toFixed(2);
    } else if (field === 'total_amount') {
      // Reverse calculate if total is entered
      const total = parseFloat(value) || 0;
      const rate = parseFloat(item.gst_rate) || 0;
      item.taxable_value = (total / (1 + rate/100)).toFixed(2);
      const totalTax = total - parseFloat(item.taxable_value);
      item.cgst = (totalTax / 2).toFixed(2);
      item.sgst = (totalTax / 2).toFixed(2);
      item.igst = 0;
    }

    newItems[index] = item;
    setFormData({ ...formData, items: newItems });
  };

  const addItem = () => {
    setFormData({
      ...formData,
      items: [...formData.items, { 
        hsn_code: '', hsn_description: '', uqc: 'PCS', quantity: 1, 
        unit_price: 0, gst_rate: 18, taxable_value: 0, cgst: 0, sgst: 0, igst: 0, total_amount: 0 
      }]
    });
  };

  const removeItem = (index) => {
    if (formData.items.length > 1) {
      const newItems = formData.items.filter((_, i) => i !== index);
      setFormData({ ...formData, items: newItems });
    }
  };

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
      setError("Microphone access denied.");
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
      const fd = new FormData();
      fd.append('file', audioBlob, 'recording.webm');
      const res = await axios.post(`/api/transactions/process-voice?whatsapp_id=${whatsappId}`, fd);
      populateFromAI(res.data.extraction);
      setText(res.data.transcript);
      setEntryMethod('ai');
    } catch (err) {
      setError('Voice processing failed.');
    } finally {
      setLoading(false);
    }
  };

  const populateFromAI = (data) => {
    if (!data) return;
    
    // Smart party mapping based on transaction category
    let pName = '';
    let pGstin = '';
    
    if (activeCategory === 'Sale') {
      // For sales, the bill's recipient is our customer
      pName = data.recipient_name || data.customer_name || '';
      pGstin = data.recipient_gstin || '';
    } else if (activeCategory === 'Purchase') {
      // For purchases, the bill's vendor is our supplier
      pName = data.vendor_name || data.party_name || '';
      pGstin = data.vendor_gstin || data.party_gstin || '';
    } else {
      // Fallback for Expense/Payment
      pName = data.vendor_name || data.recipient_name || data.party_name || data.customer_name || '';
      pGstin = data.vendor_gstin || data.recipient_gstin || data.party_gstin || '';
    }

    setFormData(prev => ({
      ...prev,
      party_name: pName,
      party_gstin: pGstin,
      invoice_no: data.invoice_no || '',
      date: data.date ? data.date.split('-').reverse().join('-') : prev.date,
      place_of_supply: data.place_of_supply || '',
      reverse_charge: data.reverse_charge || 'N',
      items: data.items && data.items.length > 0 ? data.items.map(item => {
        const qty = item.quantity || 1;
        const totalTaxable = item.taxable_value || 0;
        return {
          hsn_code: item.hsn_code || '',
          hsn_description: item.hsn_description || '',
          uqc: item.uqc || 'PCS',
          quantity: qty,
          unit_price: (totalTaxable / qty).toFixed(2),
          gst_rate: item.gst_rate || 18,
          taxable_value: totalTaxable,
          cgst: item.cgst || 0,
          sgst: item.sgst || 0,
          igst: item.igst || 0,
          total_amount: item.total_amount || 0
        };
      }) : prev.items,
      total_amount: data.total_amount || 0,
      notes: data.notes || ''
    }));
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    setProcessingFile(file.name);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await axios.post(`/api/transactions/process-image?whatsapp_id=${whatsappId}`, fd);
      populateFromAI(res.data.extraction);
      setMediaUrl(res.data.media_url);
      setEntryMethod('ai');
      setToastMessage({ title: 'AI Extraction Complete', body: 'The form has been populated with data from your bill.' });
      setShowToast(true);
      setTimeout(() => setShowToast(false), 5000);
    } catch (err) {
      setError('AI scanning failed. Please try manual entry.');
    } finally {
      setLoading(false);
      setProcessingFile(null);
      // Reset input value to allow re-uploading the same file
      if (e.target) e.target.value = '';
    }
  };

  const handleTextSubmit = async () => {
    if (!text) return;
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`/api/transactions/process-text?whatsapp_id=${whatsappId}&text=${encodeURIComponent(text)}`);
      populateFromAI(res.data.extraction);
      setEntryMethod('ai');
    } catch (err) {
      setError('AI text analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleFinalSave = async () => {
    if (!whatsappId) return;
    if (!formData.party_name || !formData.total_amount) {
      setError('Please fill Name and Amount');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = {
        extraction: {
          ...formData,
          transaction_type: activeCategory
        },
        media_url: mediaUrl
      };
      await axios.post(`/api/transactions/save?whatsapp_id=${whatsappId}`, payload);
      setSuccess(true);
      setToastMessage({ title: 'Success', body: `Recorded to ${activeCategory}s` });
      setShowToast(true);
      fetchUserStats();
      
      // Auto-reset after 3 seconds
      setTimeout(() => {
        setShowToast(false);
        resetForm();
      }, 3000);
    } catch (err) {
      setError('Save failed.');
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
      place_of_supply: '',
      reverse_charge: 'N',
      items: [{ hsn_code: '', hsn_description: '', uqc: 'PCS', quantity: 1, unit_price: 0, gst_rate: 18, taxable_value: 0, cgst: 0, sgst: 0, igst: 0, total_amount: 0 }],
      total_amount: 0,
      category: '',
      payment_mode: 'Cash',
      payment_type: 'Incoming',
      reference_id: '',
      notes: ''
    });
    setMediaUrl(null);
    setText('');
    setSuccess(false);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const categories = [
    { id: 'Sale', label: 'Sale', icon: <ShoppingBag size={20} />, color: 'blue' },
    { id: 'Purchase', label: 'Purchase', icon: <ShoppingCart size={20} />, color: 'indigo' },
    { id: 'Expense', label: 'Expense', icon: <Wallet size={20} />, color: 'orange' },
    { id: 'Payment', label: 'Payment', icon: <ArrowUpRight size={20} />, color: 'green' },
  ];

  return (
    <div className="max-w-7xl mx-auto pb-20 px-4 sm:px-6">
      {/* Toast Notification */}
      {showToast && (
        <div className="fixed top-24 right-4 sm:right-10 z-[110] animate-in slide-in-from-right duration-500">
          <div className="bg-green-600 text-white px-8 py-4 rounded-xl shadow-2xl flex items-center space-x-3 border border-green-500">
            <CheckCircle2 size={24} />
            <div>
              <p className="font-black uppercase tracking-widest text-xs">{toastMessage.title}</p>
              <p className="font-bold">{toastMessage.body}</p>
            </div>
          </div>
        </div>
      )}

      {/* Box 1: AI Controls & Scanner */}
      <div className="bg-white rounded-3xl border border-gray-100 shadow-sm mb-12 p-8 lg:p-12">
        <div className="flex flex-col lg:flex-row items-center justify-between gap-8 mb-12">
          <div className="flex bg-gray-100 p-1.5 rounded-2xl w-full lg:w-auto">
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => { setActiveCategory(cat.id); resetForm(); }}
                className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-black uppercase tracking-widest text-[10px] transition-all duration-300 ${activeCategory === cat.id ? 'bg-white text-blue-600 shadow-sm ring-1 ring-gray-200' : 'text-gray-400 hover:text-gray-600'}`}
              >
                {cat.icon}
                <span>{cat.label}</span>
              </button>
            ))}
          </div>

          <div className="flex bg-gray-100 p-1.5 rounded-2xl w-full lg:w-auto">
            <button 
              onClick={() => setActiveTab('upload')} 
              className={`px-8 py-3 text-[10px] font-black uppercase tracking-widest rounded-xl transition ${activeTab === 'upload' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-400'}`}
            >
              File Upload
            </button>
            <button 
              onClick={() => setActiveTab('text')} 
              className={`px-8 py-3 text-[10px] font-black uppercase tracking-widest rounded-xl transition ${activeTab === 'text' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-400'}`}
            >
              Natural Text
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center bg-blue-50/50 rounded-3xl p-8 border border-blue-100/50">
          <div>
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-200">
                <Sparkles size={20} />
              </div>
              <h2 className="text-xl font-black text-gray-900 uppercase tracking-widest italic">AI Magic Scanner</h2>
            </div>
            <p className="text-gray-600 font-medium mb-8 leading-relaxed max-w-sm">
              Upload a photo of your receipt or type a natural sentence. Our AI will automatically extract the party name, items, and taxes for you.
            </p>
            <div className="flex items-center space-x-6 text-[10px] font-black uppercase tracking-[0.2em] text-blue-600/60">
              <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div> No Manual Entry</span>
              <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div> GSTR-1 Ready</span>
            </div>
          </div>

          <div className="space-y-4">
            {activeTab === 'upload' ? (
              <div 
                onClick={() => fileInputRef.current?.click()}
                className="group relative border-2 border-dashed border-blue-200 rounded-2xl p-10 flex flex-col items-center justify-center cursor-pointer hover:border-blue-400 transition bg-white hover:bg-blue-50/50"
              >
                <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept="image/*,.pdf" />
                <div className="w-14 h-14 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition duration-500">
                  {loading && processingFile ? <Loader2 className="animate-spin" size={24} /> : <Upload size={24} />}
                </div>
                <p className="text-sm font-black text-blue-600 uppercase tracking-widest text-center px-4">
                  {loading && processingFile ? `Processing ${processingFile}...` : 'Click to Scan Bill'}
                </p>
                {!loading && (
                  <p className="text-[10px] text-gray-400 mt-2 font-bold uppercase tracking-widest">Supports JPEG, PNG, PDF</p>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <textarea 
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="e.g. Sold 10 units of Widget A to Apollo Pharma for 5000 with 18% GST"
                  className="w-full h-32 p-4 bg-white border border-blue-100 rounded-2xl focus:ring-2 focus:ring-blue-500 outline-none font-bold text-sm resize-none"
                />
                <div className="flex space-x-3">
                  <button 
                    onMouseDown={startRecording}
                    onMouseUp={stopRecording}
                    className={`flex-none p-4 rounded-xl transition flex items-center justify-center ${isRecording ? 'bg-red-500 text-white animate-pulse shadow-lg shadow-red-200' : 'bg-blue-50 text-blue-600 hover:bg-blue-100'}`}
                  >
                    {isRecording ? <Square size={20} /> : <Mic size={20} />}
                  </button>
                  <button 
                    onClick={handleTextSubmit}
                    disabled={loading || !text}
                    className="flex-1 bg-blue-600 text-white font-black py-4 rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center space-x-2 uppercase tracking-widest text-xs"
                  >
                    {loading ? <Loader2 className="animate-spin" size={16} /> : <Sparkles size={16} />}
                    <span>AI Analysis</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Form - Invoice Style */}
      <div className="bg-white rounded-[2rem] border border-gray-100 shadow-xl overflow-hidden">
        <div className="bg-gray-50/50 p-8 sm:p-12 border-b border-gray-100">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-2"><Calendar size={12}/> Date</label>
              <input type="date" value={formData.date} onChange={(e) => setFormData({...formData, date: e.target.value})} className="w-full p-4 bg-white border border-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 font-bold" />
            </div>
            <div className="space-y-2 lg:col-span-2">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-2"><User size={12}/> {activeCategory === 'Sale' ? 'Customer Name' : 'Supplier Name'}</label>
              <input type="text" value={formData.party_name} onChange={(e) => setFormData({...formData, party_name: e.target.value})} placeholder="Search or add new contact" className="w-full p-4 bg-white border border-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 font-bold" />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-2"><Hash size={12}/> GSTIN</label>
              <input type="text" value={formData.party_gstin} onChange={(e) => setFormData({...formData, party_gstin: e.target.value.toUpperCase()})} placeholder="Optional for B2C" className="w-full p-4 bg-white border border-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 font-bold uppercase" />
            </div>
          </div>
        </div>

        <div className="p-4 sm:p-12">
          {/* Items Table */}
          <div className="overflow-x-auto -mx-4 sm:mx-0">
            <table className="w-full min-w-[1000px]">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="pb-6 text-[10px] font-black text-gray-400 uppercase tracking-widest text-left px-4">Description</th>
                  <th className="pb-6 text-[10px] font-black text-gray-400 uppercase tracking-widest text-left px-4 w-32">HSN</th>
                  <th className="pb-6 text-[10px] font-black text-gray-400 uppercase tracking-widest text-right px-4 w-24">Qty</th>
                  <th className="pb-6 text-[10px] font-black text-gray-400 uppercase tracking-widest text-right px-4 w-40">Unit Price</th>
                  <th className="pb-6 text-[10px] font-black text-gray-400 uppercase tracking-widest text-right px-4 w-40">Taxable Val</th>
                  <th className="pb-6 text-[10px] font-black text-gray-400 uppercase tracking-widest text-right px-4 w-32">GST %</th>
                  <th className="pb-6 text-[10px] font-black text-gray-400 uppercase tracking-widest text-right px-4 w-40">Total (Inc. Tax)</th>
                  <th className="pb-6 w-16"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {formData.items.map((item, idx) => (
                  <tr key={idx} className="group">
                    <td className="py-6 px-4">
                      <input 
                        type="text" 
                        value={item.hsn_description} 
                        onChange={(e) => handleItemChange(idx, 'hsn_description', e.target.value)} 
                        placeholder="Item name / service" 
                        className="w-full bg-transparent font-bold outline-none placeholder:text-gray-300 focus:text-blue-600" 
                      />
                    </td>
                    <td className="py-6 px-4">
                      <input 
                        type="text" 
                        value={item.hsn_code} 
                        onChange={(e) => handleItemChange(idx, 'hsn_code', e.target.value)} 
                        placeholder="8802" 
                        className="w-full bg-transparent font-bold outline-none placeholder:text-gray-300" 
                      />
                    </td>
                    <td className="py-6 px-4 text-right">
                      <input 
                        type="number" 
                        value={item.quantity} 
                        onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)} 
                        className="w-full bg-transparent font-bold outline-none text-right" 
                      />
                    </td>
                    <td className="py-6 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1">
                        <span className="text-gray-400 text-xs">₹</span>
                        <input 
                          type="number" 
                          value={item.unit_price} 
                          onChange={(e) => handleItemChange(idx, 'unit_price', e.target.value)} 
                          className="w-24 bg-transparent font-black outline-none text-right" 
                        />
                      </div>
                    </td>
                    <td className="py-6 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1">
                        <span className="text-gray-400 text-xs">₹</span>
                        <input 
                          type="number" 
                          value={item.taxable_value} 
                          onChange={(e) => handleItemChange(idx, 'taxable_value', e.target.value)} 
                          className="w-24 bg-transparent font-medium text-gray-500 outline-none text-right" 
                        />
                      </div>
                    </td>
                    <td className="py-6 px-4 text-right">
                      <select 
                        value={item.gst_rate} 
                        onChange={(e) => handleItemChange(idx, 'gst_rate', e.target.value)} 
                        className="bg-gray-100 px-3 py-1.5 rounded-lg font-bold text-xs outline-none appearance-none cursor-pointer"
                      >
                        {[0, 5, 12, 18, 28].map(r => <option key={r} value={r}>{r}%</option>)}
                      </select>
                    </td>
                    <td className="py-6 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1 font-black text-blue-600">
                        <span>₹</span>
                        <input 
                          type="number" 
                          value={item.total_amount} 
                          onChange={(e) => handleItemChange(idx, 'total_amount', e.target.value)} 
                          className="w-24 bg-transparent outline-none text-right" 
                        />
                      </div>
                    </td>
                    <td className="py-6 px-4 text-right">
                      <button 
                        onClick={() => removeItem(idx)} 
                        className="opacity-0 group-hover:opacity-100 text-red-300 hover:text-red-500 transition p-2"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button 
            onClick={addItem}
            className="mt-8 flex items-center space-x-2 text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] bg-blue-50 hover:bg-blue-100 px-6 py-3 rounded-xl transition active:scale-95"
          >
            <Plus size={14} />
            <span>Add Row</span>
          </button>

          {/* Totals Section */}
          <div className="mt-12 flex flex-col lg:flex-row gap-12 pt-12 border-t border-gray-100">
            <div className="flex-1 space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-2"><Tag size={12}/> Invoice No.</label>
                  <input type="text" value={formData.invoice_no} onChange={(e) => setFormData({...formData, invoice_no: e.target.value})} placeholder="INV-001" className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 font-bold" />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-2"><CreditCard size={12}/> Payment Mode</label>
                  <select value={formData.payment_mode} onChange={(e) => setFormData({...formData, payment_mode: e.target.value})} className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 font-bold outline-none appearance-none">
                    {['Cash', 'Online', 'Bank', 'Credit'].map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-2"><FileText size={12}/> Internal Notes</label>
                <textarea value={formData.notes} onChange={(e) => setFormData({...formData, notes: e.target.value})} placeholder="Any additional info..." className="w-full h-32 p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 font-bold resize-none" />
              </div>
            </div>

            <div className="lg:w-96 bg-gray-50 rounded-[1.5rem] p-8 space-y-6 h-fit">
              <div className="flex justify-between items-center text-sm font-bold text-gray-500">
                <span>Total Taxable Value</span>
                <span className="text-gray-900">₹{formData.items.reduce((sum, i) => sum + (parseFloat(i.taxable_value) || 0), 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-center text-sm font-bold text-gray-500">
                <span>Tax Amount (GST)</span>
                <span className="text-gray-900">₹{formData.items.reduce((sum, i) => sum + (parseFloat(i.cgst) + parseFloat(i.sgst) + parseFloat(i.igst) || 0), 0).toFixed(2)}</span>
              </div>
              <div className="pt-6 border-t border-gray-200 flex justify-between items-end">
                <div>
                  <p className="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] mb-1">Grand Total</p>
                  <p className="text-4xl font-black text-gray-900 italic tracking-tighter">₹{formData.total_amount}</p>
                </div>
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
                  <button onClick={() => navigate('/dashboard')} className="flex-1 sm:flex-none text-gray-500 font-black uppercase tracking-widest text-[10px] py-5 px-8 hover:bg-gray-50 rounded-2xl transition flex items-center justify-center space-x-2">
                    <ArrowLeft size={16} />
                    <span>Dashboard</span>
                  </button>
                  <button onClick={resetForm} className="flex-1 sm:flex-none bg-green-600 text-white font-black py-5 px-12 rounded-2xl shadow-xl shadow-green-100 hover:bg-green-700 transition flex items-center justify-center space-x-3 active:scale-95 uppercase tracking-widest text-[10px]">
                    <RefreshCcw size={18} />
                    <span>Add Another {activeCategory}</span>
                  </button>
                </>
              ) : (
                <>
                  <button onClick={(e) => { e.preventDefault(); resetForm(); }} className="flex-1 sm:flex-none text-gray-400 font-black uppercase tracking-widest text-[10px] py-5 px-8 hover:text-gray-600 transition">Discard</button>
                  <button 
                    onClick={handleFinalSave} 
                    disabled={loading}
                    className="flex-1 sm:flex-none bg-blue-600 text-white font-black py-5 px-16 rounded-2xl shadow-2xl shadow-blue-100 hover:bg-blue-700 transition flex items-center justify-center space-x-3 active:scale-95 uppercase tracking-[0.2em] text-[10px]"
                  >
                    {loading ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
                    <span>{loading ? 'Saving...' : `Record ${activeCategory}`}</span>
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecordTransaction;
