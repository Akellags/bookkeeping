import React, { useState, useEffect, useMemo } from 'react';
import { 
  Plus, 
  Trash2, 
  Save, 
  Upload, 
  Search, 
  Loader2, 
  AlertCircle,
  CheckCircle2,
  Package,
  FileSpreadsheet,
  RefreshCcw,
  X,
  ChevronLeft,
  ChevronRight,
  Edit2
} from 'lucide-react';
import axios from 'axios';
import { useUser } from '../context/UserContext';

const ProductMaster = () => {
  const { whatsappId } = useUser();
  
  // Data States
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  
  // UI States
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [importMode, setImportMode] = useState(false);
  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [verificationIssues, setVerificationIssues] = useState([]);
  
  // Search & Drilldown States
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [drillDownLoading, setDrillDownLoading] = useState(false);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [activeSearchContext, setActiveSearchContext] = useState(null); // 'quickAdd' or {idx}
  
  // Filter & Pagination States
  const [filterQuery, setFilterQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Quick Add State (Multiple rows allowed)
  const initialNewItem = { shortcode: '', description: '', hsn_code: '', gst_rate: 18, uqc: 'PCS', unit_price: 0 };
  const [pendingItems, setPendingItems] = useState([{ ...initialNewItem }]);

  // Constants
  const uqcOptions = ['PCS', 'BOX', 'NOS', 'KGS', 'LTR', 'MTR', 'SET', 'OTH'];
  const gstRates = [0, 5, 12, 18, 28];

  useEffect(() => {
    fetchProducts();
  }, [whatsappId]);

  const fetchProducts = async () => {
    setInitialLoading(true);
    try {
      const res = await axios.get(`/api/user/product-master?whatsapp_id=${whatsappId}`);
      if (res.data) {
        setProducts(res.data);
      }
    } catch (err) {
      console.error("Failed to fetch products", err);
      // If error is 404, it might just mean no products yet
      if (err.response?.status !== 404) {
        setError("Failed to load existing products.");
      }
    } finally {
      setInitialLoading(false);
    }
  };

  // --- Search Logic ---
  const handleGSTSearch = async (context) => {
    const item = context.type === 'pending' ? pendingItems[context.idx] : products[context.idx];
    const query = item.hsn_code || item.description;
    
    if (!query || query.length < 2) {
      setError("Please enter an HSN code or Description to search.");
      return;
    }

    setActiveSearchContext(context);
    setSearching(true);
    setShowSearchModal(true);
    try {
      const res = await axios.get(`/api/gst/lookup?q=${encodeURIComponent(query)}`);
      setSearchResults(res.data);
    } catch (err) {
      console.error("GST Lookup failed", err);
      setError("Search failed. Please try again.");
    } finally {
      setSearching(false);
    }
  };

  const handleDrillDown = async (hsnCode) => {
    setDrillDownLoading(true);
    try {
      const res = await axios.get(`/api/gst/lookup?q=${hsnCode}`);
      setSearchResults(res.data);
    } catch (err) {
      console.error("Drill down failed", err);
    } finally {
      setDrillDownLoading(false);
    }
  };

  const selectHSN = (result) => {
    if (activeSearchContext.type === 'pending') {
      const idx = activeSearchContext.idx;
      const updated = [...pendingItems];
      updated[idx] = {
        ...updated[idx],
        hsn_code: result.hsn_code,
        description: result.description,
        gst_rate: result.gst_rate || updated[idx].gst_rate,
        uqc: result.uqc || updated[idx].uqc
      };
      setPendingItems(updated);
    } else {
      const idx = activeSearchContext.idx;
      const updated = [...products];
      updated[idx].hsn_code = result.hsn_code;
      updated[idx].description = result.description;
      updated[idx].gst_rate = result.gst_rate || updated[idx].gst_rate;
      updated[idx].uqc = result.uqc || updated[idx].uqc;
      setProducts(updated);
    }
    setSearchResults([]);
    setActiveSearchContext(null);
    setShowSearchModal(false);
  };

  // --- CRUD Operations ---
  const addPendingRow = () => {
    setPendingItems([...pendingItems, { ...initialNewItem }]);
  };

  const removePendingRow = (idx) => {
    if (pendingItems.length > 1) {
      setPendingItems(pendingItems.filter((_, i) => i !== idx));
    } else {
      setPendingItems([{ ...initialNewItem }]);
    }
  };

  const handlePendingRowChange = (idx, field, value) => {
    const updated = [...pendingItems];
    updated[idx][field] = value;
    setPendingItems(updated);
  };

  const handleRemoveItem = (shortcode) => {
    setProducts(products.filter(p => p.shortcode !== shortcode));
  };

  const handleRowChange = (idx, field, value) => {
    const updated = [...products];
    updated[idx][field] = value;
    setProducts(updated);
  };

  // --- Bulk Operations ---
  const handleCSVImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      const rows = text.split('\n').filter(row => row.trim());
      
      const splitCSV = (str) => {
        const result = [];
        let cur = '';
        let inQuotes = false;
        for (let i = 0; i < str.length; i++) {
          const char = str[i];
          if (char === '"') inQuotes = !inQuotes;
          else if (char === ',' && !inQuotes) {
            result.push(cur);
            cur = '';
          } else {
            cur += char;
          }
        }
        result.push(cur);
        return result;
      };

      const imported = rows.slice(1).map(row => {
        const r = splitCSV(row);
        return {
          shortcode: r[0]?.trim().toUpperCase() || '',
          description: r[1]?.trim() || '',
          hsn_code: r[2]?.trim() || '',
          gst_rate: parseFloat(r[3]) || 18,
          uqc: r[4]?.trim() || 'PCS',
          unit_price: parseFloat(r[5]) || 0
        };
      }).filter(p => p.shortcode && p.description);

      // Merge with existing (keeping imported as priority)
      const existingShortcodes = new Set(imported.map(p => p.shortcode));
      const filteredExisting = products.filter(p => !existingShortcodes.has(p.shortcode));
      setProducts([...imported, ...filteredExisting]);
      setImportMode(false);
    };
    reader.readAsText(file);
  };

  const handleSaveToCloud = async (force = false) => {
    setLoading(true);
    setError(null);
    setVerificationIssues([]);

    // 1. Identify valid pending items (must have shortcode and description)
    const validPending = pendingItems
      .filter(item => item.shortcode.trim() && item.description.trim())
      .map(item => ({ ...item, shortcode: item.shortcode.trim().toUpperCase() }));

    // 2. Check for duplicates between pending and existing
    const existingShortcodes = new Set(products.map(p => p.shortcode));
    const duplicates = validPending.filter(p => existingShortcodes.has(p.shortcode));
    if (duplicates.length > 0) {
      setError(`Duplicate shortcodes found in pending items: ${duplicates.map(d => d.shortcode).join(', ')}`);
      setLoading(false);
      return;
    }

    const finalProducts = [...validPending, ...products];

    try {
      if (!force) {
        const verifyRes = await axios.post('/api/gst/verify-bulk', { products: finalProducts });
        if (verifyRes.data.length > 0) {
          setVerificationIssues(verifyRes.data);
          setShowVerifyModal(true);
          setLoading(false);
          return;
        }
      }

      await axios.post(`/api/user/product-master/bulk?whatsapp_id=${whatsappId}`, {
        products: finalProducts
      });
      
      setProducts(finalProducts);
      setPendingItems([{ ...initialNewItem }]); // Reset staging area
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update Product Master");
    } finally {
      setLoading(false);
    }
  };

  // --- Filter & Pagination Logic ---
  const filteredProducts = useMemo(() => {
    if (!filterQuery) return products;
    const q = filterQuery.toLowerCase();
    return products.filter(p => 
      p.shortcode.toLowerCase().includes(q) || 
      p.description.toLowerCase().includes(q) || 
      p.hsn_code.includes(q)
    );
  }, [products, filterQuery]);

  const totalPages = Math.ceil(filteredProducts.length / itemsPerPage);
  const paginatedProducts = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredProducts.slice(start, start + itemsPerPage);
  }, [filteredProducts, currentPage]);

  if (initialLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <Loader2 className="animate-spin text-blue-600" size={48} />
        <p className="text-gray-500 font-bold">Loading your Product Master...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-black text-gray-900 flex items-center space-x-2">
            <Package className="text-blue-600" />
            <span>Product Master</span>
          </h1>
          <p className="text-gray-500 text-sm font-semibold">Manage your shortcodes and GST compliance data</p>
        </div>
        <div className="flex space-x-3">
          <button 
            onClick={() => setImportMode(!importMode)}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition font-bold text-sm text-gray-600"
          >
            <Upload size={16} />
            <span>{importMode ? 'Cancel' : 'Import CSV'}</span>
          </button>
          <button 
            onClick={() => handleSaveToCloud(false)}
            disabled={loading || products.length === 0}
            className="flex items-center space-x-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-black shadow-lg shadow-blue-200 disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            <span>{loading ? 'Updating...' : 'Save to Google Sheets'}</span>
          </button>
        </div>
      </div>

      {/* CSV Import Section */}
      {importMode && (
        <div className="p-6 bg-blue-50 border border-blue-100 rounded-xl flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <FileSpreadsheet className="text-blue-600" size={32} />
            <div>
              <p className="font-bold text-blue-900">Bulk Import Products</p>
              <p className="text-sm text-blue-700">Upload a CSV file with columns: Shortcode, Description, HSN, Rate, UQC, Price</p>
            </div>
          </div>
          <input 
            type="file" 
            accept=".csv" 
            onChange={handleCSVImport}
            className="block text-sm text-blue-600 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
          />
        </div>
      )}

      {/* Feedback Messages */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-lg flex items-center justify-between text-red-700 font-bold">
          <div className="flex items-center space-x-3">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)}><X size={16}/></button>
        </div>
      )}
      {success && (
        <div className="p-4 bg-green-50 border border-green-100 rounded-lg flex items-center space-x-3 text-green-700 font-bold animate-pulse">
          <CheckCircle2 size={20} />
          <span>Product Master updated successfully in Google Sheets!</span>
        </div>
      )}

      {/* 1. Quick Add Section (Staging Area) */}
      <div className="bg-white p-6 border border-gray-200 rounded-2xl shadow-sm space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center space-x-2">
            <Plus size={16} className="text-blue-600" />
            <span>Quick Add Staging</span>
          </h2>
          <button 
            onClick={addPendingRow}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-black hover:bg-blue-700 transition shadow-lg shadow-blue-100"
          >
            <Plus size={18} />
            <span className="text-xs uppercase">Add New Row</span>
          </button>
        </div>
        
        <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
          {pendingItems.map((item, pIdx) => (
            <div key={pIdx} className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end bg-gray-50/50 p-4 rounded-xl border border-gray-100 relative group">
              <div className="col-span-2">
                <label className="text-[10px] font-black text-gray-400 uppercase">Shortcode</label>
                <input 
                  type="text" 
                  placeholder="e.g. LAPTOP"
                  value={item.shortcode}
                  onChange={(e) => handlePendingRowChange(pIdx, 'shortcode', e.target.value)}
                  className="w-full mt-1 p-2 bg-white border border-gray-200 rounded-lg font-bold text-gray-700 focus:outline-none focus:border-blue-300"
                />
              </div>
              <div className="col-span-3">
                <label className="text-[10px] font-black text-gray-400 uppercase">Description</label>
                <input 
                  type="text" 
                  placeholder="Product Name"
                  value={item.description}
                  onChange={(e) => handlePendingRowChange(pIdx, 'description', e.target.value)}
                  className="w-full mt-1 p-2 bg-white border border-gray-200 rounded-lg font-semibold text-gray-700 focus:outline-none focus:border-blue-300"
                />
              </div>
              <div className="col-span-2">
                <label className="text-[10px] font-black text-gray-400 uppercase">HSN/SAC</label>
                <div className="relative flex items-center">
                  <input 
                    type="text" 
                    placeholder="Code"
                    value={item.hsn_code}
                    onChange={(e) => handlePendingRowChange(pIdx, 'hsn_code', e.target.value)}
                    className="w-full mt-1 p-2 bg-white border border-gray-200 rounded-lg font-semibold text-gray-700 focus:outline-none focus:border-blue-300 pr-8"
                  />
                  <button 
                    onClick={() => handleGSTSearch({ type: 'pending', idx: pIdx })}
                    className="absolute right-2 top-3 text-gray-300 hover:text-blue-600 transition"
                  >
                    <Search size={14} />
                  </button>
                </div>
              </div>
              <div className="col-span-3 grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-black text-gray-400 uppercase">GST %</label>
                  <select 
                    value={item.gst_rate}
                    onChange={(e) => handlePendingRowChange(pIdx, 'gst_rate', parseFloat(e.target.value))}
                    className="w-full mt-1 p-2 bg-white border border-gray-200 rounded-lg font-bold text-blue-600 focus:outline-none cursor-pointer"
                  >
                    {gstRates.map(r => <option key={r} value={r}>{r}%</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-black text-gray-400 uppercase">UQC</label>
                  <select 
                    value={item.uqc}
                    onChange={(e) => handlePendingRowChange(pIdx, 'uqc', e.target.value)}
                    className="w-full mt-1 p-2 bg-white border border-gray-200 rounded-lg font-bold text-gray-600 focus:outline-none cursor-pointer"
                  >
                    {uqcOptions.map(u => <option key={u} value={u}>{u}</option>)}
                  </select>
                </div>
              </div>
              <div className="col-span-1">
                <label className="text-[10px] font-black text-gray-400 uppercase">Price</label>
                <div className="relative flex items-center">
                  <span className="absolute left-2 top-3.5 text-gray-400 font-bold">₹</span>
                  <input 
                    type="number" 
                    value={item.unit_price}
                    onChange={(e) => handlePendingRowChange(pIdx, 'unit_price', parseFloat(e.target.value))}
                    className="w-full mt-1 p-2 pl-5 bg-white border border-gray-200 rounded-lg font-bold text-gray-700 focus:outline-none focus:border-blue-300"
                  />
                </div>
              </div>
              <div className="col-span-1 flex justify-end pb-1">
                <button 
                  onClick={() => removePendingRow(pIdx)}
                  className="p-2 text-gray-300 hover:text-red-500 transition"
                  title="Remove row"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
        
        {pendingItems.some(item => item.shortcode.trim() && item.description.trim()) && (
          <div className="pt-2 flex justify-center">
            <p className="text-[11px] font-bold text-blue-600 animate-pulse uppercase tracking-wider">
              Items in staging will be saved when you click "Save to Google Sheets" at the top
            </p>
          </div>
        )}
      </div>

      {/* 2. Search & Filter Bar */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input 
            type="text"
            placeholder="Search by Shortcode, Description or HSN..."
            value={filterQuery}
            onChange={(e) => { setFilterQuery(e.target.value); setCurrentPage(1); }}
            className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-100 font-medium text-gray-600 shadow-sm"
          />
        </div>
        <div className="bg-gray-100 px-4 py-2 rounded-xl text-xs font-black text-gray-500 uppercase tracking-widest">
          {filteredProducts.length} Products
        </div>
      </div>

      {/* 3. Paginated Product List */}
      <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">Shortcode</th>
              <th className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest w-1/3">Description</th>
              <th className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">HSN/SAC</th>
              <th className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">GST Rate</th>
              <th className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">UQC</th>
              <th className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">Price</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {paginatedProducts.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-6 py-12 text-center text-gray-400 font-bold">
                  No products found matching your search.
                </td>
              </tr>
            ) : (
              paginatedProducts.map((product) => {
                const globalIdx = products.findIndex(p => p.shortcode === product.shortcode);
                return (
                  <tr key={product.shortcode} className="hover:bg-gray-50 transition group">
                    <td className="px-6 py-4">
                      <span className="font-black text-gray-900 bg-gray-100 px-2 py-1 rounded text-xs">{product.shortcode}</span>
                    </td>
                    <td className="px-6 py-4">
                      <input 
                        type="text" 
                        value={product.description}
                        onChange={(e) => handleRowChange(globalIdx, 'description', e.target.value)}
                        className="w-full bg-transparent font-semibold text-gray-700 focus:outline-none focus:bg-white focus:px-2 rounded border-transparent focus:border-blue-200 border"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <input 
                          type="text" 
                          value={product.hsn_code}
                          onChange={(e) => handleRowChange(globalIdx, 'hsn_code', e.target.value)}
                          className="w-20 bg-transparent font-semibold text-gray-600 focus:outline-none focus:bg-white focus:px-2 rounded border-transparent focus:border-blue-200 border"
                        />
                        <button 
                          onClick={() => handleGSTSearch({ idx: globalIdx })}
                          className="p-1 text-gray-300 hover:text-blue-600 transition"
                        >
                          <Search size={12} />
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <select 
                        value={product.gst_rate}
                        onChange={(e) => handleRowChange(globalIdx, 'gst_rate', parseFloat(e.target.value))}
                        className="bg-transparent font-bold text-blue-600 focus:outline-none cursor-pointer"
                      >
                        {gstRates.map(r => <option key={r} value={r}>{r}%</option>)}
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <select 
                        value={product.uqc}
                        onChange={(e) => handleRowChange(globalIdx, 'uqc', e.target.value)}
                        className="bg-transparent font-bold text-gray-600 focus:outline-none cursor-pointer"
                      >
                        {uqcOptions.map(u => <option key={u} value={u}>{u}</option>)}
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-1">
                        <span className="text-gray-300 font-bold">₹</span>
                        <input 
                          type="number" 
                          value={product.unit_price}
                          onChange={(e) => handleRowChange(globalIdx, 'unit_price', parseFloat(e.target.value))}
                          className="w-20 bg-transparent font-bold text-gray-700 focus:outline-none focus:bg-white focus:px-2 rounded border-transparent focus:border-blue-200 border"
                        />
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => handleRemoveItem(product.shortcode)}
                        className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
        
        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
            <span className="text-xs font-bold text-gray-500 uppercase">
              Page {currentPage} of {totalPages}
            </span>
            <div className="flex space-x-2">
              <button 
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="p-2 border border-gray-200 rounded-lg hover:bg-white transition disabled:opacity-30"
              >
                <ChevronLeft size={18} />
              </button>
              <button 
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="p-2 border border-gray-200 rounded-lg hover:bg-white transition disabled:opacity-30"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* GST Search Modal (Global) */}
      {showSearchModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[110] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 bg-blue-600 border-b border-blue-700 flex items-center justify-between">
              <div className="flex items-center space-x-3 text-white">
                <Search size={24} />
                <h2 className="text-xl font-black">GST Intelligence Search</h2>
              </div>
              <button onClick={() => setShowSearchModal(false)} className="text-blue-200 hover:text-white transition">
                <X size={24} />
              </button>
            </div>
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              {searching ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <Loader2 className="animate-spin text-blue-600" size={48} />
                  <p className="text-gray-500 font-bold text-center">Scanning HSN/SAC Registry...</p>
                </div>
              ) : searchResults.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <AlertCircle className="text-gray-300" size={48} />
                  <p className="text-gray-500 font-bold text-center">No exact matches found. Try a broader term.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {searchResults.map((res, ridx) => (
                    <div key={ridx} className="flex items-center space-x-2 p-2 hover:bg-blue-50 rounded-xl border border-transparent hover:border-blue-100 transition group">
                      <button
                        onClick={() => selectHSN(res)}
                        className="flex-1 text-left p-3 flex justify-between items-center min-w-0"
                      >
                        <div className="min-w-0 pr-4">
                          <p className="text-sm font-bold text-gray-900 leading-snug">{res.description}</p>
                          <div className="flex items-center space-x-3 mt-1">
                            <span className="text-[10px] font-black text-blue-600 uppercase bg-blue-50 px-2 py-0.5 rounded">
                              {res.type || 'HSN'}: {res.hsn_code}
                            </span>
                            {res.is_parent && (
                              <span className="text-[9px] font-black bg-amber-100 text-amber-700 px-2 py-0.5 rounded uppercase">Parent Category</span>
                            )}
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-lg font-black text-blue-600">{res.gst_rate}%</p>
                          <p className="text-[10px] font-bold text-gray-400 uppercase">GST Rate</p>
                        </div>
                      </button>
                      {res.is_parent && (
                        <button 
                          onClick={() => handleDrillDown(res.hsn_code)}
                          disabled={drillDownLoading}
                          className="w-12 h-12 flex items-center justify-center text-gray-400 hover:text-blue-600 hover:bg-white rounded-xl transition border border-transparent hover:border-gray-200"
                          title="Explore sub-categories"
                        >
                          {drillDownLoading ? <Loader2 size={20} className="animate-spin" /> : <RefreshCcw size={20} />}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-end">
              <button onClick={() => setShowSearchModal(false)} className="px-6 py-2 bg-white text-gray-600 border border-gray-200 rounded-lg font-bold hover:bg-gray-50">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* HSN Verification Modal */}
      {showVerifyModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[110] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 bg-amber-50 border-b border-amber-100 flex items-center justify-between">
              <div className="flex items-center space-x-3 text-amber-700">
                <AlertCircle size={24} />
                <h2 className="text-xl font-black">GST Compliance Warning</h2>
              </div>
              <button onClick={() => setShowVerifyModal(false)} className="text-amber-400 hover:text-amber-600"><X size={24} /></button>
            </div>
            <div className="p-6 max-h-[60vh] overflow-y-auto space-y-4">
              <p className="text-gray-600 font-bold">We found some potential issues with your product data:</p>
              {verificationIssues.map((issue, idx) => (
                <div key={idx} className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                  <div className="flex justify-between items-start mb-2">
                    <span className="bg-white px-2 py-1 rounded border border-gray-200 text-[10px] font-black text-gray-500">{issue.shortcode}</span>
                    <span className="text-xs font-black text-red-600 uppercase tracking-tighter">{issue.issue}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <div>
                      <p className="text-[10px] font-black text-gray-400 uppercase">Your Entry</p>
                      <p className="text-sm font-bold text-gray-700">{issue.user_description}</p>
                    </div>
                    {issue.official_description && (
                      <div>
                        <p className="text-[10px] font-black text-blue-400 uppercase">GST Match</p>
                        <p className="text-sm font-bold text-blue-700">{issue.official_description}</p>
                        <p className="text-[10px] font-bold text-blue-500">Official Rate: {issue.official_rate}%</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-100 flex flex-col space-y-3">
              <button onClick={() => handleSaveToCloud(true)} className="w-full py-4 bg-amber-600 text-white rounded-xl font-black hover:bg-amber-700 transition">Save Anyway (I am sure)</button>
              <button onClick={() => setShowVerifyModal(false)} className="w-full py-4 bg-white text-gray-600 border border-gray-200 rounded-xl font-black hover:bg-gray-50">Wait, let me fix it</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductMaster;
