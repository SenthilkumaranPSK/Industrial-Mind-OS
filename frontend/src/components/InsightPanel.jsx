import { useState } from 'react';
import { Target, CheckCircle2, ChevronDown, ChevronRight, ListOrdered, FileSearch, ShieldAlert } from 'lucide-react';

export default function InsightPanel({ insights }) {
  const [showSteps, setShowSteps] = useState(false);

  if (!insights) {
    return (
      <div className="w-80 bg-slate-50 border-l border-slate-200 p-6 flex items-center justify-center h-full">
        <p className="text-sm text-slate-400 text-center">Send a query to see reasoning insights.</p>
      </div>
    );
  }

  return (
    <div className="w-80 bg-slate-50/80 border-l border-slate-200 flex flex-col h-full overflow-y-auto">
      <div className="p-4 border-b border-indigo-100 bg-white sticky top-0 z-10 shadow-sm flex items-center justify-between">
        <h2 className="font-semibold text-indigo-950 flex items-center">
          <Target className="w-4 h-4 mr-2 text-indigo-500" />
          {insights.isHistorical ? 'Message Insight' : 'Latest Insight'}
        </h2>
        {insights.isHistorical && (
          <span className="px-2 py-0.5 bg-amber-50 text-amber-600 text-[10px] font-bold rounded-full border border-amber-100 uppercase tracking-tighter">
            Pinned
          </span>
        )}
      </div>

      <div className="p-5 space-y-6">
        
        {/* Confidence Level */}
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
          <div className="flex justify-between items-end mb-2">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Confidence</h3>
            <span className="text-sm font-bold text-slate-700">{insights.confidenceScore}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 mb-2">
            <div 
              className={`h-2 rounded-full ${
                insights.confidenceScore >= 90 ? 'bg-emerald-400' 
                : insights.confidenceScore >= 70 ? 'bg-amber-400' 
                : 'bg-rose-400'
              }`}
              style={{ width: `${insights.confidenceScore}%` }}
            ></div>
          </div>
          <div className="flex items-center text-sm font-medium text-slate-600">
            {insights.confidenceScore >= 90 ? <CheckCircle2 className="w-4 h-4 text-emerald-400 mr-2" /> : <ShieldAlert className="w-4 h-4 text-amber-400 mr-2" />}
            {insights.confidence} Confidence Level
          </div>
        </div>

        {/* Strategy Used */}
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Retrieval Strategy</h3>
          <p className="text-sm text-slate-700 font-medium">{insights.strategy}</p>
        </div>

        {/* Sources Used */}
        <div className="bg-white rounded-xl p-4 border border-indigo-100 shadow-sm">
          <h3 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-3">Sources Utilized</h3>
          <ul className="space-y-2 text-sm text-slate-600">
            {(insights.sources || []).map((src, i) => (
              <li key={i} className="flex flex-col">
                <span className="flex items-center font-medium break-all">
                  <FileSearch className="w-4 h-4 text-indigo-300 mr-2 flex-shrink-0" />
                  {src}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Retrieval Steps (Collapsible) */}
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
          <button 
            onClick={() => setShowSteps(!showSteps)}
            className="flex items-center justify-between w-full focus:outline-none"
          >
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Retrieval Steps</h3>
            {showSteps ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
          </button>
          
          {showSteps && (
            <div className="mt-4 space-y-3 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
              <ul className="space-y-4">
                {(insights.steps || []).map((stepInfo, i) => (
                  <li key={i} className="flex items-start text-sm">
                    <div className="bg-white border border-slate-200 w-5 h-5 rounded-full flex items-center justify-center mr-3 z-10 flex-shrink-0 shadow-sm">
                      <ListOrdered className="w-3 h-3 text-slate-400" />
                    </div>
                    <div className="-mt-0.5">
                      <p className="font-medium text-slate-700">{stepInfo.step}</p>
                      <p className="text-[11px] text-emerald-500 font-medium uppercase tracking-wider">{stepInfo.status}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
