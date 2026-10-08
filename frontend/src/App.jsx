import { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import InsightPanel from './components/InsightPanel';
import SourceViewerModal from './components/SourceViewerModal';
import SourceSelectionModal from './components/SourceSelectionModal';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import GraphVisualizer from './components/GraphVisualizer';
import ArtifactPanel from './components/ArtifactPanel';
import MindMap from './components/MindMap';
import EightDIncidentStudio from './components/EightDStudio/EightDIncidentStudio';
import { API_URL } from './api';

export default function App() {
  // --- 1. ALL PRIMARY STATE & REFS ---
  const [user, setUser] = useState(null);
  const [chats, setChats] = useState([{ id: Date.now(), title: 'New Chat', messages: [], selectedFiles: [] }]);
  const [currentChatId, setCurrentChatId] = useState(Date.now());
  const [token, setToken] = useState(localStorage.getItem('imos_token') || null);
  const [showRegister, setShowRegister] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [showSourceSelection, setShowSourceSelection] = useState(false);
  const [showMindMap, setShowMindMap] = useState(false);
  const [showEightDStudio, setShowEightDStudio] = useState(false);
  const [activeEightDReport, setActiveEightDReport] = useState(null);
  const [activeArtifact, setActiveArtifact] = useState(null);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true);
  const [activeMessageId, setActiveMessageId] = useState(null);
  const [activeSource, setActiveSource] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const abortControllerRef = useRef(null);

  // --- 2. DERIVED DATA (Initialized AFTER all states) ---
  const activeChat = chats.find(c => c.id === currentChatId) || chats[0];
  const messages = activeChat?.messages || [];
  const currentInsights = activeMessageId 
    ? { ...(messages.find(m => m.id === activeMessageId)?.insights || activeChat?.insights || {}), isHistorical: true }
    : (activeChat?.insights || null);

  // --- 3. UTILITY HANDLERS ---
  const handleLogout = () => {
    localStorage.removeItem('imos_token');
    setToken(null);
    setUser(null);
    setChats([{ id: Date.now(), title: 'New Chat', messages: [], selectedFiles: [] }]);
    setUploadedFiles([]);
  };

  const handleLogin = (newToken) => {
    localStorage.setItem('imos_token', newToken);
    setToken(newToken);
  };

  const handleRegister = (email, password) => {
    setShowRegister(false);
  };

  const setMessages = (updater) => {
    setChats(prevChats => prevChats.map(chat => {
      if (chat.id === currentChatId) {
        const newMessages = typeof updater === 'function' ? updater(chat.messages) : updater;
        let newTitle = chat.title;
        if (newTitle === 'New Chat' && newMessages.length > 0) {
          const firstUserMsg = newMessages.find(m => m.role === 'user');
          if (firstUserMsg) newTitle = firstUserMsg.content;
        }
        return { ...chat, messages: newMessages, title: newTitle };
      }
      return chat;
    }));
  };

  const createNewChat = () => {
    const newId = Date.now();
    setChats(prev => [{ id: newId, title: 'New Chat', messages: [], insights: null, selectedFiles: [] }, ...prev]);
    setCurrentChatId(newId);
    setShowSourceSelection(false);
  };

  const handleUpdateChatFiles = (chatId, files) => {
    setChats(prev => prev.map(c => c.id === chatId ? { ...c, selectedFiles: files } : c));
    setShowSourceSelection(false);
  };

  const handleOpenEightDStudio = async (report = null) => {
    if (report) {
      setActiveEightDReport(report);
      setShowEightDStudio(true);
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/v1/rca/reports`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const summaries = await res.json();
        if (Array.isArray(summaries) && summaries.length > 0) {
          const firstId = summaries[0].report_id;
          const fullRes = await fetch(`${API_URL}/api/v1/rca/reports/${firstId}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {}
          });
          if (fullRes.ok) {
            const fullReport = await fullRes.json();
            setActiveEightDReport(fullReport);
          }
        }
      }
    } catch (err) {
      console.warn('Could not fetch existing 8D reports, using offline defaults:', err);
    }
    setShowEightDStudio(true);
  };

  const handleRenameChat = (id, newTitle) => {
    setChats(prev => prev.map(c => c.id === id ? { ...c, title: newTitle } : c));
  };

  const handleDeleteChat = (id) => {
    setChats(prev => {
      const filtered = prev.filter(c => c.id !== id);
      if (filtered.length === 0) {
        const newChat = { id: Date.now(), title: 'New Chat', messages: [], insights: null };
        setCurrentChatId(newChat.id);
        return [newChat];
      }
      if (id === currentChatId) {
        setCurrentChatId(filtered[0].id);
      }
      return filtered;
    });
  };

  // --- 4. DATA FETCHING HANDLERS ---
  const fetchUploadedFiles = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) {
        const data = await res.json();
        setUploadedFiles(data.files || []);
      }
    } catch (err) {
      console.error('Failed to fetch document list:', err);
    }
  };

  const fetchSuggestions = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/suggestions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) { handleLogout(); return; }
      if (res.ok) {
        const data = await res.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (err) { console.error(err); }
  };

  const fetchAlerts = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/alerts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.reports || []);
      }
    } catch (err) { console.error(err); }
  };

  const dismissAlert = async (alertId) => {
    try {
      await fetch(`${API_URL}/api/v1/alerts/${alertId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchAlerts();
    } catch (err) { console.error(err); }
  };

  const handleUpload = async (file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setIsUploading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (response.status === 401) { handleLogout(); return; }
      if (!response.ok) throw new Error("Upload Failed");
      await response.json();
      await fetchUploadedFiles();
      fetchSuggestions();
      fetchAlerts();
    } catch (err) {
      console.error("Error uploading file:", err);
      alert("Failed to upload the document.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleConfluenceSync = async (config) => {
    if (!config || !config.domain) return;
    setIsUploading(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/confluence/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(config)
      });
      if (response.status === 401) { handleLogout(); return; }
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Sync Failed");
      }
      await fetchUploadedFiles();
      fetchSuggestions();
    } catch (err) {
      console.error("Error syncing Confluence:", err);
      alert(`Failed to sync Space: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteFile = async (filename) => {
    if (!window.confirm("Are you sure?")) return;
    try {
      const response = await fetch(`${API_URL}/api/v1/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 401) { handleLogout(); return; }
      if (!response.ok) throw new Error("Delete Failed");
      await fetchUploadedFiles();
    } catch (err) {
      console.error("Error deleting file:", err);
    }
  };

  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsGenerating(false);
      setMessages(prev => {
        const last = prev[prev.length - 1];
        if (last && last.isTyping) {
          return prev.map((m, i) => i === prev.length - 1 ? { ...m, isTyping: false, content: 'Generation manually stopped.' } : m);
        }
        return prev;
      });
    }
  };

  const handleSendMessage = async (e, input, mode) => {
    e.preventDefault();
    if (!input.trim()) return;

    const newUserMsg = { id: Date.now(), role: 'user', content: input };
    const loadingId = Date.now() + 1;
    const loadingMsg = { id: loadingId, role: 'assistant', isTyping: true, content: '' };

    setMessages(prev => [...prev, newUserMsg, loadingMsg]);
    setIsGenerating(true);
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_URL}/api/v1/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: input,
          mode: mode || "Private",
          files: activeChat.selectedFiles
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        if (response.status === 401) { handleLogout(); return; }
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      const insights = {
        confidence: data.confidence_level,
        confidenceScore: data.confidence_score,
        strategy: data.strategy,
        sources: data.sources || [],
        steps: data.steps || []
      };

      const newAiMsg = { id: loadingId, role: 'assistant', content: data.answer, citations: data.citations, steps: data.steps, insights };
      setMessages(prev => prev.map(m => m.id === loadingId ? newAiMsg : m));
      setChats(prev => prev.map(chat => chat.id === currentChatId ? { ...chat, insights } : chat));

    } catch (error) {
      if (error.name !== 'AbortError') {
        const fallbackAiMsg = { id: loadingId, role: 'assistant', content: "Error reaching API.", citations: [] };
        setMessages(prev => prev.map(m => m.id === loadingId ? fallbackAiMsg : m));
      }
    } finally {
      setIsGenerating(false);
    }
  };

  // --- 5. EFFECTS ---
  useEffect(() => {
    const fetchUser = async () => {
      if (!token) { setUser(null); return; }
      try {
        const res = await fetch(`${API_URL}/api/v1/auth/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) { setUser(await res.json()); }
        else if (res.status === 401) { handleLogout(); }
      } catch (err) { console.error(err); }
    };
    fetchUser();
  }, [token]);

  useEffect(() => {
    if (!user) {
      setChats([{ id: Date.now(), title: 'New Chat', messages: [], selectedFiles: [] }]);
      return;
    }
    const storageKey = `imos_chats_${user.email}`;
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        const parsed = JSON.parse(saved).map(c => ({ ...c, selectedFiles: c.selectedFiles || [] }));
        setChats(parsed);
        const savedId = localStorage.getItem(`imos_current_chat_${user.email}`);
        if (savedId && parsed.find(c => c.id === Number(savedId))) setCurrentChatId(Number(savedId));
        else if (parsed.length > 0) setCurrentChatId(parsed[0].id);
      } catch (e) { console.error(e); }
    }
  }, [user]);

  useEffect(() => {
    if (user && chats.length > 0) localStorage.setItem(`imos_chats_${user.email}`, JSON.stringify(chats));
  }, [chats, user]);

  useEffect(() => {
    if (user && currentChatId) localStorage.setItem(`imos_current_chat_${user.email}`, currentChatId.toString());
  }, [currentChatId, user]);

  useEffect(() => {
    // Reset active message insights when switching chats to prevent undefined crashes
    setActiveMessageId(null);
  }, [currentChatId]);

  useEffect(() => { fetchUploadedFiles(); }, [token]);
  useEffect(() => { fetchSuggestions(); }, [token]);
  useEffect(() => { fetchAlerts(); }, [token]);

  // Periodically poll for alerts
  useEffect(() => {
    if (!token) return;
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, [token]);

  // --- 6. RENDER ---
  if (!token) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#f8fafc]">
        {showRegister ? (
          <Register onRegister={handleRegister} onNavigateLogin={() => setShowRegister(false)} />
        ) : (
          <Login onLogin={handleLogin} onNavigateRegister={() => setShowRegister(true)} />
        )}
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#0f172a] overflow-hidden font-sans text-slate-800">
      {isSidebarOpen && <div className="fixed inset-0 bg-slate-900/50 z-20 md:hidden backdrop-blur-sm" onClick={() => setIsSidebarOpen(false)} />}
      
      <div className={`fixed md:relative z-30 h-full transition-all duration-300 ease-in-out border-r border-slate-800 ${isSidebarOpen ? 'translate-x-0 w-72' : '-translate-x-full w-0 md:translate-x-0 md:w-0 overflow-hidden'}`}>
        <div className="w-72 h-full">
          <Sidebar
            user={user}
            onLogout={handleLogout} onUpload={handleUpload} onConfluenceSync={handleConfluenceSync} onDeleteFile={handleDeleteFile}
            isUploading={isUploading} uploadedFiles={uploadedFiles} chats={chats} currentChatId={currentChatId}
            onSelectChat={setCurrentChatId} onNewChat={createNewChat} onRenameChat={handleRenameChat} onDeleteChat={handleDeleteChat}
            onShowGraph={() => setShowGraph(true)} onShowMindMap={() => setShowMindMap(true)} onOpenSourceSelection={() => setShowSourceSelection(true)}
            onClose={() => setIsSidebarOpen(false)}
            alerts={alerts} onDismissAlert={dismissAlert}
            onShowEightDStudio={() => handleOpenEightDStudio()}
          />
        </div>
      </div>

      <div className="flex-1 flex bg-[#f8fafc] w-full transition-all duration-300 min-w-0 overflow-hidden">
        <div className="flex-1 flex flex-col h-full overflow-hidden border-r border-slate-100 relative">
          <div className="flex-1 min-h-0 relative">
            {!isSidebarOpen && <button onClick={() => setIsSidebarOpen(true)} className="absolute top-4 left-4 z-50 p-2.5 bg-white border border-slate-200 rounded-xl shadow-sm"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M4 6h16M4 12h16M4 18h7"></path></svg></button>}
            {!isRightSidebarOpen && !activeArtifact && <button onClick={() => setIsRightSidebarOpen(true)} className="absolute top-4 right-4 z-50 p-2.5 bg-white border border-slate-200 rounded-xl shadow-sm"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M20 6h-16M13 12h7M10 18h10"></path></svg></button>}
            
            <ChatInterface
              messages={messages} setMessages={setMessages} setActiveMessageId={setActiveMessageId} onSourceClick={setActiveSource}
              isSidebarOpen={isSidebarOpen} suggestions={suggestions} onSendMessage={handleSendMessage} isGenerating={isGenerating}
              onStopGenerating={handleStopGenerating} onOpenSourceSelection={() => setShowSourceSelection(true)}
              chats={chats} currentChatId={currentChatId} onArtifactOpen={setActiveArtifact}
            />
          </div>
        </div>

        <div className={`transition-all duration-500 bg-white flex flex-col border-l border-slate-200 ${activeArtifact ? 'absolute inset-0 z-40 lg:relative lg:inset-auto lg:w-1/2 w-full' : isRightSidebarOpen ? 'absolute inset-0 z-40 lg:relative lg:inset-auto lg:w-[360px] w-full' : 'w-0 overflow-hidden hidden lg:flex'}`}>
          <div className="h-full w-full relative overflow-hidden flex flex-col">
            {activeArtifact ? <ArtifactPanel artifact={activeArtifact} onClose={() => setActiveArtifact(null)} onSourceClick={setActiveSource} /> : (
              <div className="h-full flex flex-col bg-slate-50/50">
                <div className="p-4 border-b border-slate-100 bg-white flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />Retrieval Context</h3>
                  <button onClick={() => setIsRightSidebarOpen(false)} className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12"></path></svg></button>
                </div>
                <div className="flex-1 overflow-auto p-4"><InsightPanel insights={currentInsights} /></div>
              </div>
            )}
          </div>
        </div>
      </div>

      {activeSource && <SourceViewerModal source={activeSource} onClose={() => setActiveSource(null)} />}
      {showGraph && <GraphVisualizer onClose={() => setShowGraph(false)} />}
      {showMindMap && <MindMap onClose={() => setShowMindMap(false)} chatMessages={messages} />}
      <SourceSelectionModal isOpen={showSourceSelection} onClose={() => setShowSourceSelection(false)} uploadedFiles={uploadedFiles} initialSelection={activeChat?.selectedFiles || []} onConfirm={(files) => handleUpdateChatFiles(currentChatId, files)} />
      {showEightDStudio && (
        <EightDIncidentStudio
          report={activeEightDReport}
          onClose={() => setShowEightDStudio(false)}
          onSourceClick={setActiveSource}
          isModal={true}
        />
      )}
    </div>
  );
}
