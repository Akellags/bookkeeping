import React, { useState, useEffect } from 'react';
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
  FileJson
} from 'lucide-react';
import axios from 'axios';
import { useUser } from '../context/UserContext';

const ProductMaster = () => {
  const { whatsappId } = useUser();
  const [products, setProducts] = useState([
    { shortcode: '', description: '', hsn_code: '', gst_rate: 18, uqc: 'PCS', unit_price: 0 }
  ]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [activeSearchIdx, setActiveSearchIdx] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [importMode, setImportMode] = useState(false);

  const uqcOptions = ['PCS', 'BOX', 'NOS', 'KGS', 'LTR', 'MTR', 'SET', 'OTH'];
  const gstRates = [0, 5, 12, 18, 28];

  const handleAddRow = () => {
    setProducts([...products, { shortcode: '', description: '', hsn_code: '', gst_rate: 18, uqc: 'PCS', unit_price: 0 }]);
  };

  const handleRemoveRow = (idx) => {
    if (products.length > 1) {
      setProducts(products.filter((_, i) => i !== idx));
    }
  };

  const handleChange = (idx, field, value) => {
    const updated = [...products];
    updated[idx][field] = value;
    setProducts(updated);
  };

  const handleGSTSearch = async (idx, query) => {
    if (!query || query.length < 3) return;
    setActiveSearchIdx(idx);
    setSearching(true);
    try {
      const res = await axios.get(`/api/gst/lookup?q=${query}`);
      setSearchResults(res.data);
    } catch (err) {
      console.error("GST Lookup failed", err);
    } finally {
      setSearching(false);
    }
  };

  const selectHSN = (idx, result) => {
    const updated = [...products];
    updated[idx].hsn_code = result.hsn_code;
    updated[idx].description = result.description;
    updated[idx].gst_rate = result.gst_rate || updated[idx].gst_rate;
    updated[idx].uqc = result.uqc || updated[idx].uqc;
    setProducts(updated);
    setSearchResults([]);
    setActiveSearchIdx(null);
  };

  const handleCSVImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;
      const rows = text.split('\n').filter(row => row.trim());
      
      // Better CSV split that handles commas within quotes
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
          shortcode: r[0]?.trim() || '',
          description: r[1]?.trim() || '',
          hsn_code: r[2]?.trim() || '',
          gst_rate: parseFloat(r[3]) || 18,
          uqc: r[4]?.trim() || 'PCS',
          unit_price: parseFloat(r[5]) || 0
        };
      }).filter(p => p.shortcode || p.description);

      setProducts(imported);
      setImportMode(false);
    };
    reader.readAsText(file);
  };

  const handleSave = async () => {
    if (products.some(p => !p.shortcode || !p.description)) {
      setError("Shortcode and Description are mandatory for all rows.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await axios.post(`/api/user/product-master/bulk?whatsapp_id=${whatsappId}`, {
        products: products
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update Product Master");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
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
            onClick={handleSave}
            disabled={loading}
            className="flex items-center space-x-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-black shadow-lg shadow-blue-200 disabled:opacity-50"
          >
            {loading ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
            <span>{loading ? 'Updating...' : 'Save to Google Sheets'}</span>
          </button>
        </div>
      </div>

      {importMode && (
        <div className="mb-6 p-6 bg-blue-50 border border-blue-100 rounded-xl flex items-center justify-between">
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

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-lg flex items-center space-x-3 text-red-700 font-bold">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-green-50 border border-green-100 rounded-lg flex items-center space-x-3 text-green-700 font-bold animate-bounce">
          <CheckCircle2 size={20} />
          <span>Product Master updated successfully in Google Sheets!</span>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest">Shortcode</th>
              <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest w-1/3">Description</th>
              <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest">HSN Code</th>
              <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest">GST Rate</th>
              <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest">UQC</th>
              <th className="px-6 py-4 text-xs font-black text-gray-400 uppercase tracking-widest">Unit Price</th>
              <th className="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {products.map((product, idx) => (
              <tr key={idx} className="hover:bg-gray-50 transition group">
                <td className="px-6 py-4">
                  <input 
                    type="text" 
                    value={product.shortcode}
                    placeholder="e.g. LAPTOP"
                    onChange={(e) => handleChange(idx, 'shortcode', e.target.value.toUpperCase())}
                    className="w-full bg-transparent font-bold text-gray-700 focus:outline-none placeholder:text-gray-300"
                  />
                </td>
                <td className="px-6 py-4 relative">
                  <div className="flex items-center space-x-2">
                    <input 
                      type="text" 
                      value={product.description}
                      placeholder="Product Description"
                      onChange={(e) => handleChange(idx, 'description', e.target.value)}
                      className="flex-1 bg-transparent font-semibold text-gray-600 focus:outline-none placeholder:text-gray-300"
                    />
                    <button 
                      onClick={() => handleGSTSearch(idx, product.description)}
                      className="p-1 text-gray-300 hover:text-blue-600 transition"
                      title="Search GST Database"
                    >
                      <Search size={14} />
                    </button>
                  </div>
                  {activeSearchIdx === idx && searchResults.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 shadow-2xl rounded-xl z-50 max-h-60 overflow-y-auto p-2">
                      <div className="flex justify-between items-center px-2 py-1 mb-1 border-b border-gray-50">
                        <span className="text-[10px] font-black text-gray-400 uppercase tracking-tighter">GST Intelligence Suggestions</span>
                        <button onClick={() => setActiveSearchIdx(null)}><X size={10} /></button>
                      </div>
                      {searchResults.map((res, ridx) => (
                        <button
                          key={ridx}
                          onClick={() => selectHSN(idx, res)}
                          className="w-full text-left p-3 hover:bg-blue-50 rounded-lg transition flex justify-between items-center group"
                        >
                          <div className="min-w-0 pr-4">
                            <p className="text-xs font-bold text-gray-900 truncate">{res.description}</p>
                            <p className="text-[10px] font-semibold text-gray-400 uppercase">HSN: {res.hsn_code}</p>
                          </div>
                          <span className="bg-blue-100 text-blue-700 text-[10px] font-black px-2 py-1 rounded">{res.gst_rate}%</span>
                        </button>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <input 
                    type="text" 
                    value={product.hsn_code}
                    placeholder="HSN"
                    onChange={(e) => handleChange(idx, 'hsn_code', e.target.value)}
                    className="w-full bg-transparent font-semibold text-gray-600 focus:outline-none placeholder:text-gray-300"
                  />
                </td>
                <td className="px-6 py-4">
                  <select 
                    value={product.gst_rate}
                    onChange={(e) => handleChange(idx, 'gst_rate', parseFloat(e.target.value))}
                    className="bg-transparent font-bold text-blue-600 focus:outline-none cursor-pointer"
                  >
                    {gstRates.map(r => <option key={r} value={r}>{r}%</option>)}
                  </select>
                </td>
                <td className="px-6 py-4">
                  <select 
                    value={product.uqc}
                    onChange={(e) => handleChange(idx, 'uqc', e.target.value)}
                    className="bg-transparent font-bold text-gray-600 focus:outline-none cursor-pointer"
                  >
                    {uqcOptions.map(u => <option key={u} value={u}>{u}</option>)}
                  </select>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-1">
                    <span className="text-gray-400 font-bold">₹</span>
                    <input 
                      type="number" 
                      value={product.unit_price}
                      onChange={(e) => handleChange(idx, 'unit_price', parseFloat(e.target.value))}
                      className="w-20 bg-transparent font-bold text-gray-700 focus:outline-none"
                    />
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <button 
                    onClick={() => handleRemoveRow(idx)}
                    className="text-gray-300 hover:text-red-500 transition p-1"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="p-6 bg-gray-50/50 flex justify-center">
          <button 
            onClick={handleAddRow}
            className="flex items-center space-x-2 text-blue-600 font-black text-sm hover:text-blue-700 transition"
          >
            <Plus size={18} />
            <span>Add New Product</span>
          </button>
        </div>
      </div>
      
      <div className="mt-8 flex items-start space-x-4 p-6 bg-gray-100 rounded-2xl border border-gray-200">
        <div className="p-3 bg-white rounded-xl border border-gray-200 shadow-sm text-blue-600">
          <RefreshCcw size={24} />
        </div>
        <div>
          <h3 className="font-black text-gray-900">What happens next?</h3>
          <p className="text-sm text-gray-500 font-medium mt-1 leading-relaxed">
            When you save these products, they are synced with your **Google Sheets Product Master**. 
            On WhatsApp, you can simply use the **Shortcode** (e.g. `LAPTOP`) to record sales, and we will 
            automatically pull the Description, HSN, Rate, and Price.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ProductMaster;
