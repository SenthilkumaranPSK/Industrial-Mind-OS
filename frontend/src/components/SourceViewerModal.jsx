import { X, FileText, ArrowUpRight } from 'lucide-react';

export default function SourceViewerModal({ source, onClose }) {
  if (!source) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-sm transition-opacity">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-indigo-100 bg-gradient-to-r from-indigo-50/50 to-white">
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-indigo-500" />
            <h3 className="text-base font-semibold text-indigo-950 tracking-tight">
              {source.url ? (
                <a href={source.url} target="_blank" rel="noopener noreferrer" className="hover:text-indigo-600 hover:underline flex items-center decoration-indigo-300">
                  {source.source}
                  <ArrowUpRight className="w-3.5 h-3.5 ml-1.5 text-indigo-400" />
                </a>
              ) : (
                source.source
              )}
            </h3>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50">
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-indigo-400 uppercase tracking-widest">Exact Snippet Used</h4>
              {source.url && (
                <a 
                  href={source.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
                >
                  View original source <ArrowUpRight className="w-3 h-3 ml-1" />
                </a>
              )}
            </div>
            
            <figure className="bg-white border text-slate-700 border-indigo-100 p-5 rounded-2xl shadow-sm relative overflow-hidden">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-400"></div>
              <blockquote className="text-[15px] leading-relaxed italic relative z-10 pl-2">
                "{source.snippet}"
              </blockquote>
            </figure>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Document Context</h4>
            <div className="bg-white border border-slate-200 p-5 rounded-xl shadow-sm text-sm text-slate-500 font-mono leading-relaxed max-h-48 overflow-y-auto">
              [Document Metadata]
              <br/>
              Type: Technical PDF
              <br/>
              Last Indexed: 2 hrs ago
              <br/>
              Status: Verified by Immune System
              <br/><br/>
              ...surrounding context of the document would appear here to give the user a full view of the semantic origin...
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
