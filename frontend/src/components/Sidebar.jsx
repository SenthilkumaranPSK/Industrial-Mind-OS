import React, { useRef, useState, useEffect } from 'react';
import {
  Target, CheckCircle, FileText, UploadCloud, Link as LinkIcon,
  LogOut, X, User as UserIcon, ShieldCheck, PanelLeftClose,
  Trash2, Plus, MoreHorizontal, Edit2, Share, Archive, Check,
  Share2, Filter, GitBranch, Clock, ChevronDown, ChevronUp, Bell, AlertTriangle
} from 'lucide-react';

export default function Sidebar({
  onLogout, onUpload, onConfluenceSync, onDeleteFile, isUploading,
  uploadedFiles, chats, currentChatId, onSelectChat, onNewChat,
  onRenameChat, onDeleteChat, onClose, onShowGraph, onShowMindMap,
  onOpenSourceSelection, alerts = [], onDismissAlert
}) {
  const fileInputRef = useRef(null);
  const [showProfile, setShowProfile] = useState(false);
  const profileRef = useRef(null);
  const [showConfluenceModal, setShowConfluenceModal] = useState(false);
  const [confluenceConfig, setConfluenceConfig] = useState({ domain: '', spaceKey: '', email: '', apiToken: '' });
  const [isConnecting, setIsConnecting] = useState(false);
  const [openDropdownId, setOpenDropdownId] = useState(null);
  const [editingChatId, setEditingChatId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [showFiles, setShowFiles] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  const alertsRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (!event.target.closest('.chat-options-menu') && !event.target.closest('.chat-options-trigger')) {
        setOpenDropdownId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    function handleClickOutside(event) {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setShowProfile(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    function handleClickOutside(event) {
      if (alertsRef.current && !alertsRef.current.contains(event.target)) {
        setShowAlerts(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const startEditing = (chat) => {
    setEditingChatId(chat.id);
    setEditingTitle(chat.title);
    setOpenDropdownId(null);
  };

  const saveEditing = (id) => {
    if (editingTitle.trim()) onRenameChat(id, editingTitle.trim());
    setEditingChatId(null);
  };

  return (
    <div className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col h-full flex-shrink-0 text-slate-300 relative">

      {/* ── Top Header ── */}
      <div className="px-4 pt-4 pb-3 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 flex-shrink-0">
            <Target className="w-4.5 h-4.5 text-white" size={18} />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight leading-none">Industrial Mind OS</h1>
            <p className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest mt-0.5">Knowledge Engine</p>
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          {/* Notification Bell */}
          <div className="relative" ref={alertsRef}>
            <button
              onClick={() => setShowAlerts(!showAlerts)}
              className="text-slate-400 hover:text-white transition-colors p-1.5 hover:bg-slate-800 rounded-lg relative"
              title="Proactive Alerts"
            >
              <Bell className="w-4 h-4" />
              {alerts.length > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-rose-500 rounded-full animate-ping"></span>
              )}
              {alerts.length > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-rose-500 rounded-full"></span>
              )}
            </button>
            
            {showAlerts && (
              <div className="absolute top-full left-0 mt-2 w-80 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl z-[100] overflow-hidden">
                <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between bg-slate-900/50">
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Proactive Alerts</h3>
                  <span className="text-[10px] bg-rose-500/20 text-rose-400 px-2 py-0.5 rounded-full font-semibold">{alerts.length} New</span>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {alerts.length === 0 ? (
                    <div className="p-4 text-center text-slate-500 text-xs">No proactive alerts. System is fully compliant.</div>
                  ) : (
                    alerts.map(alert => (
                      <div key={alert.id} className="p-3 border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                        <div className="flex gap-2">
                          <AlertTriangle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${alert.type === 'compliance' ? 'text-rose-400' : 'text-amber-400'}`} />
                          <div>
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                              {alert.type === 'compliance' ? 'Compliance Gap' : 'Historical Pattern'}
                            </p>
                            <p className="text-xs text-slate-200 leading-snug">{alert.message}</p>
                            <p className="text-[9px] text-slate-500 mt-1">Source: {alert.source}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
          
          <button
            onClick={onClose}
            className="text-slate-600 hover:text-white transition-colors p-1.5 hover:bg-slate-800 rounded-lg"
            title="Collapse Sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Data Sources ── */}
      <div className="px-3 py-3 border-b border-slate-800 flex-shrink-0">
        <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-2 px-1">Data Sources</p>

        {/* Upload + Confluence row */}
        <div className="flex gap-2 mb-2">
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={(e) => {
              if (e.target.files.length > 0) { onUpload(e.target.files[0]); e.target.value = null; }
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg text-xs font-semibold transition-all ${isUploading ? 'bg-indigo-400 text-white cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 text-white'}`}
          >
            <UploadCloud className={`w-3.5 h-3.5 flex-shrink-0 ${isUploading ? 'animate-pulse' : ''}`} />
            <span className="truncate">{isUploading ? 'Indexing...' : 'Upload'}</span>
          </button>
          <button
            onClick={() => setShowConfluenceModal(true)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            <LinkIcon className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
            <span className="truncate">Confluence</span>
          </button>
        </div>

        {/* Visualizer buttons row */}
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <button
              onClick={onShowGraph}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg text-xs font-bold bg-slate-800/80 hover:bg-indigo-900/40 text-indigo-300 border border-indigo-500/20 hover:border-indigo-500/40 transition-all group"
            >
              <Share2 className="w-3.5 h-3.5 group-hover:scale-110 transition-transform flex-shrink-0" />
              <span className="truncate">Data Graph</span>
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse flex-shrink-0" />
            </button>
            <button
              onClick={onShowMindMap}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg text-xs font-bold bg-slate-800/80 hover:bg-violet-900/40 text-violet-300 border border-violet-500/20 hover:border-violet-500/40 transition-all group"
            >
              <GitBranch className="w-3.5 h-3.5 group-hover:scale-110 transition-transform flex-shrink-0" />
              <span className="truncate">Asset Topology</span>
              <div className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse flex-shrink-0" />
            </button>
          </div>
        </div>

        {/* Files collapsible */}
        {uploadedFiles && uploadedFiles.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowFiles(f => !f)}
              className="w-full flex items-center justify-between px-1 py-1.5 text-[10px] font-bold text-slate-500 hover:text-slate-300 uppercase tracking-widest transition-colors"
            >
              <span>{uploadedFiles.length} Indexed {uploadedFiles.length === 1 ? 'File' : 'Files'}</span>
              {showFiles ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {showFiles && (
              <div className="space-y-1 mt-1 max-h-[120px] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 pr-0.5">
                {uploadedFiles.map((filename, idx) => (
                  <div key={idx} className="flex items-center justify-between py-1.5 px-2 bg-slate-800/50 rounded-lg border border-slate-700/40 group">
                    <div className="flex items-center gap-2 overflow-hidden">
                      <FileText className="w-3 h-3 text-indigo-400 flex-shrink-0" />
                      <span className="truncate text-xs text-slate-300 font-medium">{filename}</span>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={() => onDeleteFile && onDeleteFile(filename)}
                        className="p-0.5 rounded text-slate-600 hover:text-rose-400 transition-colors hidden group-hover:block"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                      <CheckCircle className="w-3 h-3 text-emerald-400 flex-shrink-0 group-hover:hidden" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Recent Chats ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 pt-3 pb-2 flex-shrink-0">
          <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Recent Chats</p>
          <button
            onClick={onNewChat}
            className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-500 hover:text-white transition-colors border border-transparent hover:border-slate-700"
            title="New Chat"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5 scrollbar-thin scrollbar-thumb-slate-700">
          {chats && chats.length > 0 ? (
            chats.map((chat) => (
              <div key={chat.id} className="relative group">
                {editingChatId === chat.id ? (
                  <div className="w-full flex items-center p-2 rounded-lg bg-slate-800 border-2 border-indigo-500">
                    <input
                      autoFocus
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') saveEditing(chat.id);
                        if (e.key === 'Escape') { setEditingChatId(null); setEditingTitle(''); }
                      }}
                      onBlur={() => saveEditing(chat.id)}
                      className="w-full bg-transparent text-white text-sm focus:outline-none"
                    />
                    <button className="text-emerald-400 p-1 flex-shrink-0" onClick={() => saveEditing(chat.id)}>
                      <Check className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => onSelectChat(chat.id)}
                    className={`w-full text-left px-2.5 py-2 rounded-lg transition-colors flex items-start gap-2.5 pr-8 ${chat.id === currentChatId ? 'bg-slate-800' : 'hover:bg-slate-800/50'}`}
                  >
                    <Clock className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${chat.id === currentChatId ? 'text-indigo-400' : 'text-slate-600 group-hover:text-slate-400'}`} />
                    <div className="flex-1 overflow-hidden min-w-0">
                      <p className={`text-xs truncate font-medium ${chat.id === currentChatId ? 'text-white' : 'text-slate-400 group-hover:text-slate-200'}`}>
                        {chat.title}
                      </p>
                      {chat.id === currentChatId && (
                        <div className="flex items-center gap-2 mt-1">
                          <div className="flex items-center gap-1">
                            <div className="w-1 h-1 rounded-full bg-emerald-400" />
                            <span className="text-[9px] text-slate-500 font-medium">Active</span>
                          </div>
                          {(chat.selectedFiles?.length || 0) > 0 && (
                            <span className="text-[9px] bg-slate-700 text-indigo-300 px-1.5 py-0.5 rounded font-bold">
                              {chat.selectedFiles.length} src
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </button>
                )}

                {editingChatId !== chat.id && (
                  <button
                    className={`absolute right-1.5 top-2 p-1 rounded text-slate-500 hover:text-white transition-colors chat-options-trigger ${openDropdownId === chat.id ? 'opacity-100 bg-slate-700' : 'opacity-0 group-hover:opacity-100 hover:bg-slate-700/50'}`}
                    onClick={(e) => { e.stopPropagation(); setOpenDropdownId(openDropdownId === chat.id ? null : chat.id); }}
                  >
                    <MoreHorizontal className="w-3.5 h-3.5" />
                  </button>
                )}

                {openDropdownId === chat.id && (
                  <div className="chat-options-menu absolute z-50 right-1.5 top-8 w-44 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl py-1.5 animate-in fade-in zoom-in duration-150">
                    <button onClick={(e) => { e.stopPropagation(); setOpenDropdownId(null); onOpenSourceSelection(); }} className="w-full flex items-center px-3 py-2 text-xs font-medium text-indigo-300 hover:bg-slate-700">
                      <Filter className="w-3.5 h-3.5 mr-2" /> Change Knowledge
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); startEditing(chat); }} className="w-full flex items-center px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700">
                      <Edit2 className="w-3.5 h-3.5 mr-2" /> Rename
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); setOpenDropdownId(null); }} className="w-full flex items-center px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700">
                      <Share className="w-3.5 h-3.5 mr-2" /> Share
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); setOpenDropdownId(null); }} className="w-full flex items-center px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-700">
                      <Archive className="w-3.5 h-3.5 mr-2" /> Archive
                    </button>
                    <div className="h-px bg-slate-700 my-1" />
                    <button onClick={(e) => { e.stopPropagation(); setOpenDropdownId(null); if (window.confirm("Delete this chat?")) onDeleteChat(chat.id); }} className="w-full flex items-center px-3 py-2 text-xs font-medium text-rose-400 hover:bg-rose-500/10">
                      <Trash2 className="w-3.5 h-3.5 mr-2" /> Delete
                    </button>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="text-xs text-slate-600 italic p-3">No chats yet.</div>
          )}
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="px-3 py-3 border-t border-slate-800 flex-shrink-0" ref={profileRef}>
        {showProfile && (
          <div className="absolute bottom-[calc(100%+8px)] left-3 right-3 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl p-4 z-50 animate-in fade-in slide-in-from-bottom-2 duration-200">
            <div className="flex items-center gap-3 mb-3 border-b border-slate-700/50 pb-3">
              <div className="w-9 h-9 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
                <UserIcon className="w-4 h-4 text-indigo-400" />
              </div>
              <div>
                <p className="text-sm font-bold text-white">System Node</p>
                <p className="text-[10px] uppercase text-indigo-300 font-semibold tracking-wider">Secured Workspace</p>
              </div>
            </div>
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 flex items-center font-medium"><ShieldCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />Immune System</span>
                <span className="text-emerald-400 font-bold bg-emerald-400/10 px-2 py-0.5 rounded text-[10px] uppercase">Active</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 flex items-center font-medium"><Target className="w-3.5 h-3.5 mr-1.5 text-indigo-400" />Intelligence Router</span>
                <span className="text-indigo-400 font-bold bg-indigo-400/10 px-2 py-0.5 rounded text-[10px] uppercase">Auto</span>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowProfile(!showProfile)}
            className={`flex items-center gap-2.5 flex-1 overflow-hidden p-2 rounded-xl hover:bg-slate-800 transition-all text-left ${showProfile ? 'bg-slate-800 ring-1 ring-slate-700' : ''}`}
          >
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-[10px] flex-shrink-0 shadow shadow-indigo-500/30 ring-2 ring-indigo-900">
              ME
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-xs font-bold text-slate-200 truncate">My Workspace</p>
              <p className="text-[9px] text-slate-500 font-semibold tracking-wider uppercase">Industrial Mind OS</p>
            </div>
          </button>
          <button
            onClick={onLogout}
            className="p-2 text-slate-600 hover:text-rose-400 hover:bg-slate-800 rounded-xl transition-all flex-shrink-0"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Confluence Modal */}
      {showConfluenceModal && (
        <div className="fixed inset-0 z-[100] bg-slate-900/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md p-8 relative animate-in fade-in zoom-in-95 duration-200 font-sans text-slate-800">
            <button onClick={() => setShowConfluenceModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors">
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center border border-blue-100">
                <LinkIcon className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-800">Confluence Sync</h3>
                <p className="text-xs text-slate-500 font-medium mt-0.5">Securely bridge your enterprise wiki.</p>
              </div>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Domain URL</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800 text-xs placeholder-slate-400"
                    placeholder="company.atlassian.net"
                    value={confluenceConfig.domain}
                    onChange={(e) => setConfluenceConfig(c => ({ ...c, domain: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Space Key</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800 text-xs placeholder-slate-400"
                    placeholder="e.g. ENG"
                    value={confluenceConfig.spaceKey}
                    onChange={(e) => setConfluenceConfig(c => ({ ...c, spaceKey: e.target.value }))}
                  />
                </div>
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Atlassian Email</label>
                <input
                  type="email"
                  className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800 text-xs placeholder-slate-400"
                  placeholder="admin@company.com"
                  value={confluenceConfig.email}
                  onChange={(e) => setConfluenceConfig(c => ({ ...c, email: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">API Token</label>
                <input
                  type="password"
                  className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800 text-xs placeholder-slate-400"
                  placeholder="••••••••••••••••••••••••"
                  value={confluenceConfig.apiToken}
                  onChange={(e) => setConfluenceConfig(c => ({ ...c, apiToken: e.target.value }))}
                />
              </div>
              <button
                onClick={async () => {
                  setIsConnecting(true);
                  try {
                    await onConfluenceSync(confluenceConfig);
                    setShowConfluenceModal(false);
                    setConfluenceConfig({ domain: '', spaceKey: '', email: '', apiToken: '' });
                  } catch (err) {
                    console.error(err);
                  } finally {
                    setIsConnecting(false);
                  }
                }}
                disabled={isConnecting || !confluenceConfig.domain || !confluenceConfig.spaceKey || !confluenceConfig.email || !confluenceConfig.apiToken}
                className="w-full flex justify-center items-center py-3.5 px-4 rounded-xl shadow text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 transition-all disabled:opacity-50 mt-2"
              >
                {isConnecting ? 'Syncing Space...' : 'Sync Entire Space'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
