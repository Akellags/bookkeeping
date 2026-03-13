import React, { useState, useEffect } from 'react';
import { 
  MessageCircle, 
  ShieldCheck, 
  Zap, 
  Database, 
  Mic, 
  FileText,
  Bell,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';

const LandingPage = () => {
  const [isRegistered, setIsRegistered] = useState(false);

  useEffect(() => {
    const whatsappId = localStorage.getItem('whatsapp_id');
    if (whatsappId) {
      setIsRegistered(true);
    }
  }, []);

  return (
    <div className="bg-white font-inter text-gray-900 overflow-x-hidden">
      {/* Navigation */}
      <nav className="max-w-7xl mx-auto px-6 py-6 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <div className="bg-blue-600 text-white p-2 rounded-lg font-bold">HU</div>
          <span className="text-2xl font-bold tracking-tight text-blue-600">Help U</span>
        </div>
        <div className="hidden md:flex items-center space-x-8 text-sm font-semibold text-gray-600">
          <a href="#features" className="hover:text-blue-600 transition tracking-tight uppercase text-xs font-bold">Features</a>
          <a href="#compliance" className="hover:text-blue-600 transition tracking-tight uppercase text-xs font-bold">GSTR-1</a>
          <a href="#pricing" className="hover:text-blue-600 transition tracking-tight uppercase text-xs font-bold">Pricing</a>
        </div>
        <div className="flex items-center space-x-4">
          {isRegistered ? (
            <a href="/dashboard" className="bg-blue-600 text-white px-6 py-3 rounded-xl text-sm font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition transform hover:scale-105 active:scale-95">
              Dashboard
            </a>
          ) : (
            <>
              <a href="/dashboard" className="text-sm font-bold text-gray-700 hover:text-blue-600 transition">Sign In</a>
              <a href="/auth/google?whatsapp_id=new_user" className="bg-blue-600 text-white px-6 py-3 rounded-xl text-sm font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition transform hover:scale-105 active:scale-95">
                Sign Up
              </a>
            </>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <header className="max-w-7xl mx-auto px-6 py-16 md:py-24 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <div className="space-y-8">
          <div className="inline-block bg-blue-50 text-blue-600 px-4 py-2 rounded-full text-xs font-bold tracking-wider uppercase animate-fade-in border border-blue-100">
            🇮🇳 Built for Indian Traders
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold leading-tight tracking-tighter">
            Bookkeeping, <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">via WhatsApp.</span>
          </h1>
          <p className="text-xl text-gray-500 max-w-lg leading-relaxed font-medium">
            Stop manually entering bills. Photo, Voice, or Text—let AI handle your GSTR-1 compliance, PDF invoices, and Google Drive storage instantly.
          </p>
          <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
            <a href={isRegistered ? "/dashboard" : "/auth/google?whatsapp_id=new_user"} className="flex items-center justify-center space-x-2 bg-blue-600 text-white px-8 py-5 rounded-2xl text-lg font-bold shadow-xl shadow-blue-200 hover:bg-blue-700 transition transform hover:scale-105">
              <span>{isRegistered ? "Open Dashboard" : "Try Help U Now"}</span>
              <ArrowRight size={20} />
            </a>
            <div className="flex items-center space-x-3 text-gray-400 font-medium px-4">
              <ShieldCheck className="text-green-500" />
              <span className="text-sm">GST Portal Ready JSON</span>
            </div>
          </div>
        </div>
        <div className="relative">
          <div className="absolute -inset-4 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-full blur-3xl opacity-50"></div>
          
          {/* Custom Mock UI Visual */}
          <div className="relative transform lg:rotate-3 hover:rotate-0 transition duration-500">
            {/* Phone Frame */}
            <div className="bg-gray-900 rounded-[3rem] p-4 shadow-2xl border-4 border-gray-800 w-[320px] mx-auto overflow-hidden">
              {/* WhatsApp Interface */}
              <div className="bg-[#0b141a] h-[500px] rounded-[2rem] flex flex-col font-sans">
                {/* Header */}
                <div className="bg-[#202c33] p-4 flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-[10px] font-bold text-white">HU</div>
                  <div>
                    <p className="text-white text-xs font-bold">Help U Bookkeeper</p>
                    <p className="text-[#8696a0] text-[10px]">Online</p>
                  </div>
                </div>
                {/* Chat Body */}
                <div className="flex-1 p-4 space-y-4 overflow-y-auto">
                  <div className="bg-[#202c33] text-[#e9edef] p-3 rounded-2xl rounded-tl-none text-[11px] max-w-[80%] leading-relaxed shadow-sm">
                    Welcome to Help U! 🚀 Send me a photo of your bill to start.
                  </div>
                  <div className="bg-[#005c4b] text-[#e9edef] p-2 rounded-2xl rounded-tr-none text-[11px] max-w-[70%] ml-auto shadow-sm">
                    <div className="bg-white/10 rounded-lg p-2 mb-1 border border-white/5">
                      <div className="flex items-center justify-center h-20 bg-gray-800/50 rounded text-gray-400">
                        📸 Bill Photo
                      </div>
                    </div>
                    <span>Photo sent</span>
                  </div>
                  <div className="bg-[#202c33] text-[#e9edef] p-3 rounded-2xl rounded-tl-none text-[11px] max-w-[85%] shadow-sm space-y-2 border border-blue-500/30">
                    <p className="font-bold text-blue-400 underline uppercase tracking-tighter text-[9px]">GSTR-1 Extraction Complete</p>
                    <div className="grid grid-cols-2 gap-1 text-[9px] text-[#8696a0]">
                      <p>GSTIN: 27ABC...</p>
                      <p>Rate: 18%</p>
                      <p>Taxable: ₹1,271</p>
                      <p>Total: ₹1,500</p>
                    </div>
                    <div className="flex space-x-2 pt-1">
                      <div className="bg-white/10 px-2 py-1 rounded text-[8px] border border-white/10 font-bold">Sale</div>
                      <div className="bg-white/10 px-2 py-1 rounded text-[8px] border border-white/10 font-bold">Purchase</div>
                    </div>
                  </div>
                </div>
                {/* Input Area */}
                <div className="bg-[#202c33] p-3 mt-auto">
                  <div className="bg-[#2a3942] rounded-full px-4 py-2 text-[#8696a0] text-[10px]">
                    Type a message
                  </div>
                </div>
              </div>
            </div>

            {/* Float Element: PDF Invoice */}
            <div className="absolute -bottom-6 -left-6 bg-white p-4 rounded-2xl shadow-xl border border-gray-100 flex items-center space-x-3 transform -rotate-6 animate-bounce-slow">
              <div className="w-10 h-10 bg-red-50 text-red-600 rounded-lg flex items-center justify-center">
                <FileText size={20} />
              </div>
              <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase">Latest Invoice</p>
                <p className="text-sm font-extrabold text-gray-900">INV-2026-001.pdf</p>
              </div>
            </div>

            {/* Float Element: GST Status */}
            <div className="absolute -top-6 -right-6 bg-white p-4 rounded-2xl shadow-xl border border-gray-100 flex items-center space-x-3 transform rotate-6">
              <div className="w-10 h-10 bg-green-50 text-green-600 rounded-lg flex items-center justify-center">
                <ShieldCheck size={20} />
              </div>
              <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase">Compliance</p>
                <p className="text-sm font-extrabold text-gray-900">GSTR-1 Ready ✅</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Inputs Section */}
      <section className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-[2rem] border border-gray-100 shadow-sm space-y-4">
              <div className="w-12 h-12 bg-green-100 text-green-600 rounded-xl flex items-center justify-center">
                <MessageCircle size={24} />
              </div>
              <h3 className="text-lg font-bold">Snap a Bill</h3>
              <p className="text-gray-500 text-sm leading-relaxed">Send a photo of any purchase or sale. Our AI extracts GSTIN, HSN, Tax splits, and POS instantly.</p>
            </div>
            <div className="bg-white p-8 rounded-[2rem] border border-gray-100 shadow-sm space-y-4">
              <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center">
                <Mic size={24} />
              </div>
              <h3 className="text-lg font-bold">Voice Entry</h3>
              <p className="text-gray-500 text-sm leading-relaxed">Speak naturally: "Sold item worth 500 at 18% GST". Multilingual support including Hinglish.</p>
            </div>
            <div className="bg-white p-8 rounded-[2rem] border border-gray-100 shadow-sm space-y-4">
              <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center">
                <FileText size={24} />
              </div>
              <h3 className="text-lg font-bold">Instant PDFs</h3>
              <p className="text-gray-500 text-sm leading-relaxed">Type "Send invoice INV-101" and get a professional PDF tax invoice sent back to you in seconds.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Compliance Section */}
      <section id="compliance" className="py-24">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div className="space-y-8">
            <h2 className="text-4xl font-bold tracking-tight">Direct Upload to GST Portal</h2>
            <p className="text-gray-500 text-lg leading-relaxed">
              We generate 100% compliant GSTR-1 JSON files including:
            </p>
            <ul className="space-y-4">
              {[
                "B2B & B2CS Transaction Grouping",
                "Mandatory HSN Summary (Table 12)",
                "Document Issue Tracker (Table 13)",
                "Automatic POS (Place of Supply) State Codes"
              ].map((item, i) => (
                <li key={i} className="flex items-center space-x-3 text-gray-700 font-semibold">
                  <CheckCircle2 className="text-blue-600" size={20} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <div className="pt-4">
              <a href="/reports" className="text-blue-600 font-bold flex items-center space-x-2 group">
                <span>View GST Reports Dashboard</span>
                <ArrowRight size={18} className="group-hover:translate-x-1 transition" />
              </a>
            </div>
          </div>
          <div className="bg-gradient-to-br from-gray-900 to-blue-900 p-8 rounded-[2.5rem] shadow-2xl border border-gray-800 text-white">
            <div className="bg-gray-800/50 p-6 rounded-2xl border border-gray-700 space-y-4">
              <div className="flex items-center justify-between border-b border-gray-700 pb-4">
                <span className="text-sm font-bold text-gray-400">GSTR-1 JSON Export</span>
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              </div>
              <div className="font-mono text-xs space-y-2 text-blue-300 overflow-hidden">
                <p>{'"{ "ctin": "37ABCDE1234F1Z5", "inv": ["'}</p>
                <p className="pl-4">{'"{ "inum": "INV/001", "idt": "12-03-2026", "val": 1500.00 }"'}</p>
                <p>{'"] }"'}</p>
                <p>{'"{ "hsn": { "data": [{ "hsn_sc": "8471", "uqc": "NOS" }] } }"'}</p>
              </div>
            </div>
            <div className="mt-8 text-center text-sm font-bold text-gray-400">
              Download. Upload. Done.
            </div>
          </div>
        </div>
      </section>

      {/* Privacy & Reminders */}
      <section className="py-24 bg-blue-600 text-white rounded-[3rem] mx-6 mb-24 overflow-hidden relative">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-32 -mt-32 blur-3xl"></div>
        <div className="max-w-7xl mx-auto px-12 relative z-10 grid grid-cols-1 md:grid-cols-2 gap-16 items-center">
          <div className="space-y-6">
            <h2 className="text-4xl font-bold tracking-tight leading-tight">Your Data. Your Storage. Your Privacy.</h2>
            <p className="text-blue-100 text-lg leading-relaxed">
              We connect directly to your Google Drive. All bills, spreadsheets, and invoices live in your private storage. We don't keep your data on our servers.
            </p>
            <div className="flex items-center space-x-4 pt-4">
              <div className="bg-white/20 p-3 rounded-xl border border-white/10">
                <Database size={24} />
              </div>
              <div>
                <p className="font-bold">Private Google Drive Storage</p>
                <p className="text-sm text-blue-200">Help U folder created automatically</p>
              </div>
            </div>
          </div>
          <div className="space-y-8 bg-white/5 p-8 rounded-3xl border border-white/10 backdrop-blur-sm">
            <div className="flex items-start space-x-4">
              <div className="bg-white p-3 rounded-xl text-blue-600 mt-1">
                <Bell size={24} />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2">Monthly Reminders</h3>
                <p className="text-blue-100 text-sm leading-relaxed">Receive a WhatsApp notification on the 5th of every month. Never miss a GSTR-1 filing deadline again.</p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="bg-white p-3 rounded-xl text-blue-600 mt-1">
                <CheckCircle2 size={24} />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2">Interactive Validation</h3>
                <p className="text-blue-100 text-sm leading-relaxed">Our AI asks for clarification via WhatsApp buttons if a bill is unclear. No more guessing.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-6 py-12 border-t border-gray-100">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center space-x-2">
            <div className="bg-gray-900 text-white p-1 rounded font-bold text-xs uppercase">HU</div>
            <span className="font-bold">Help U Bookkeeper</span>
          </div>
          <div className="text-gray-400 text-sm font-medium">
            © 2026 Help U Inc. All Intellectual rights belong to Sriram Prasad Munnangi.
          </div>
          <div className="flex space-x-6 text-xs font-bold text-gray-500 uppercase tracking-widest">
            <a href="#" className="hover:text-blue-600">Privacy</a>
            <a href="#" className="hover:text-blue-600">Terms</a>
            <a href="#" className="hover:text-blue-600">Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
