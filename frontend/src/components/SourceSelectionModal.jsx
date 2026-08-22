import React, { useState, useEffect } from 'react';
import { FileText, Check, X, Shield, Filter, CheckSquare, Square } from 'lucide-react';

export default function SourceSelectionModal({ isOpen, onClose, uploadedFiles, onConfirm, initialSelection = [] }) {
  const [selected, setSelected] = useState(initialSelection);
  
  // Update selection if initialSelection changes or modal opens
  useEffect(() => {
    if (isOpen) {
      setSelected(initialSelection.length > 0 ? initialSelection : []);
    }
  }, [isOpen, initialSelection]);

  if (!isOpen) return null;

  const toggleFile = (filename) => {
    setSelected(prev => 
      prev.includes(filename) 
        ? prev.filter(f => f !== filename) 
        : [...prev, filename]
    );
  };

  const handleSelectAll = () => {
    if (selected.length === uploadedFiles.length) {
      setSelected([]);
    } else {
      setSelected([...uploadedFiles]);
    }
  };

  const isAllSelected = uploadedFiles.length > 0 && selected.length === uploadedFiles.length;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal Card */}
      <div className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden border border-slate-200 animate-in fade-in zoom-in duration-300">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-100 bg-gradient-to-br from-indigo-50/50 to-white">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-200">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">Pick your Knowledge</h2>
                <p className="text-xs text-slate-500 font-medium">Select sources for this conversation</p>
              </div>
            </div>
            <button 
              onClick={onClose}
              className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-slate-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* File List */}
        <div className="max-h-[400px] overflow-y-auto p-4 space-y-2">
          {uploadedFiles.length === 0 ? (
            <div className="py-12 text-center">
              <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-dashed border-slate-200">
                 <FileText className="w-8 h-8 text-slate-300" />
              </div>
              <p className="text-sm text-slate-500 font-medium italic">No documents uploaded yet.</p>
              <p className="text-xs text-slate-400 mt-1">Upload files in the sidebar first.</p>
            </div>
          ) : (
            <>
              {/* Select All Toggle */}
              <button 
                onClick={handleSelectAll}
                className="w-full flex items-center justify-between px-4 py-3 rounded-2xl bg-slate-50 border border-slate-100 hover:bg-slate-100 transition-all font-semibold text-slate-700 text-sm mb-4"
              >
                <div className="flex items-center space-x-3">
                  {isAllSelected ? <CheckSquare className="w-4 h-4 text-indigo-600" /> : <Square className="w-4 h-4 text-slate-400" />}
                  <span>Select All Documents</span>
                </div>
                <span className="text-[10px] bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  {uploadedFiles.length} Total
                </span>
              </button>

              {/* Individual Files */}
              {uploadedFiles.map((file) => {
                const isSelected = selected.includes(file);
                return (
                  <button
                    key={file}
                    onClick={() => toggleFile(file)}
                    className={`w-full flex items-center space-x-4 p-3.5 rounded-2xl border transition-all duration-200 text-left group ${
                      isSelected 
                        ? 'bg-indigo-50/50 border-indigo-200 ring-1 ring-indigo-200' 
                        : 'bg-white border-slate-100 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className={`p-2 rounded-xl border transition-colors ${
                      isSelected ? 'bg-indigo-600 border-indigo-700 shadow-md shadow-indigo-100' : 'bg-slate-100 border-slate-200'
                    }`}>
                      <FileText className={`w-4 h-4 ${isSelected ? 'text-white' : 'text-slate-500'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-semibold truncate ${isSelected ? 'text-indigo-900' : 'text-slate-700'}`}>
                        {file}
                      </p>
                      <p className="text-[10px] text-slate-400 font-medium">Verified Knowledge Source</p>
                    </div>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center border transition-all ${
                      isSelected ? 'bg-emerald-500 border-emerald-600' : 'bg-white border-slate-200 opacity-0 group-hover:opacity-100'
                    }`}>
                      {isSelected && <Check className="w-3.5 h-3.5 text-white stroke-[3px]" />}
                    </div>
                  </button>
                );
              })}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 bg-slate-50/50 border-t border-slate-100 flex items-center justify-between">
          <div className="text-xs font-semibold text-slate-400">
            {selected.length} source{selected.length !== 1 ? 's' : ''} active
          </div>
          <button
            onClick={() => onConfirm(selected)}
            disabled={selected.length === 0}
            className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold text-sm transition-all shadow-lg shadow-indigo-200 disabled:opacity-50 disabled:shadow-none transform active:scale-95"
          >
            Power up Chat
          </button>
        </div>
      </div>
    </div>
  );
}
