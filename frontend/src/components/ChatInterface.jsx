import { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, FileText, ChevronDown, ChevronRight, Loader2, Square, Search, Brain, Shield, Layers, Zap, CheckCircle2, Lock, Globe, Blend, Filter, Download } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

const MODES = [
  { key: 'Private', label: 'Private Files', icon: Lock, color: 'indigo', desc: 'Uses only your uploaded documents' },
  { key: 'Hybrid', label: 'Hybrid', icon: Blend, color: 'violet', desc: 'Your files + live web search' },
  { key: 'Online', label: 'Live Web', icon: Globe, color: 'emerald', desc: 'Searches the internet only' },
];

const MODE_COLORS = {
  Private: { btn: 'bg-indigo-600 text-white shadow-indigo-200', ring: 'ring-indigo-500' },
  Hybrid: { btn: 'bg-violet-600 text-white shadow-violet-200', ring: 'ring-violet-500' },
  Online: { btn: 'bg-emerald-600 text-white shadow-emerald-200', ring: 'ring-emerald-500' },
};

const AGENT_STEPS_BASE = [
  { key: 'planner', icon: Brain, label: 'Planner', desc: 'Decomposing and routing your query' },
  { key: 'retriever', icon: Search, label: 'Retriever', desc: 'Searching vectors & knowledge graph' },
  { key: 'websearch', icon: Globe, label: 'WebSearch', desc: 'Fetching live internet results', onlineOnly: true },
  { key: 'memory', icon: Layers, label: 'MemoryBuilder', desc: 'Fusing and deduplicating context' },
  { key: 'synth', icon: Zap, label: 'Synthesizer', desc: 'Crafting the final answer' },
  { key: 'verifier', icon: Shield, label: 'Verifier', desc: 'Validating output quality' },
];

function LiveAgentLoader({ mode = 'Private' }) {
  const AGENT_STEPS = AGENT_STEPS_BASE.filter(s => !s.onlineOnly || mode !== 'Private');
  const modeColor = mode === 'Online' ? 'text-emerald-500' : mode === 'Hybrid' ? 'text-violet-500' : 'text-indigo-500';
  const activeBg = mode === 'Online' ? 'bg-emerald-600' : mode === 'Hybrid' ? 'bg-violet-600' : 'bg-indigo-600';
  const activeRing = mode === 'Online' ? 'shadow-[0_0_10px_rgba(16,185,129,0.5)]' : mode === 'Hybrid' ? 'shadow-[0_0_10px_rgba(139,92,246,0.5)]' : 'shadow-[0_0_10px_rgba(99,102,241,0.5)]';
  const activeBorder = mode === 'Online' ? 'bg-emerald-50 border-emerald-200' : mode === 'Hybrid' ? 'bg-violet-50 border-violet-200' : 'bg-indigo-50 border-indigo-200';
  const dotColor = mode === 'Online' ? 'bg-emerald-400' : mode === 'Hybrid' ? 'bg-violet-400' : 'bg-indigo-400';
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep(prev => (prev < AGENT_STEPS.length - 1 ? prev + 1 : prev));
    }, 2200);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="w-full py-2">
      <p className={`text-[11px] uppercase tracking-widest font-semibold ${modeColor} mb-3 flex items-center gap-1.5`}>
        <Loader2 className="w-3 h-3 animate-spin" /> Industrial Mind OS — {mode} Mode Running
      </p>
      <div className="space-y-2">
        {AGENT_STEPS.map((step, idx) => {
          const Icon = step.icon;
          const isDone = idx < activeStep;
          const isActive = idx === activeStep;
          return (
            <div key={step.key} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-500 ${isActive ? `${activeBorder} border shadow-sm` :
                isDone ? 'bg-emerald-50/60 border border-emerald-100' :
                  'bg-slate-50/40 border border-slate-100 opacity-40'
              }`}>
              <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${isActive ? `${activeBg} ${activeRing}` :
                  isDone ? 'bg-emerald-500' : 'bg-slate-200'
                }`}>
                {isDone
                  ? <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                  : <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white animate-pulse' : 'text-slate-400'}`} />}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-semibold ${isActive ? 'text-indigo-700' : isDone ? 'text-emerald-700' : 'text-slate-400'}`}>
                  {step.label} {isActive && <span className="font-normal">...</span>}
                </p>
                {(isActive || isDone) && (
                  <p className={`text-[10px] mt-0.5 ${isActive ? 'text-indigo-400' : 'text-emerald-600'}`}>
                    {isDone ? '✓ Complete' : step.desc}
                  </p>
                )}
              </div>
              {isActive && (
                <div className="flex gap-0.5">
                  {[0, 1, 2].map(i => (
                    <div key={i} className={`w-1 h-1 rounded-full ${dotColor} animate-bounce`} style={{ animationDelay: `${i * 150}ms` }} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function ChatInterface({ messages, setMessages, setActiveMessageId, onSourceClick, isSidebarOpen, suggestions, onSendMessage, isGenerating, onStopGenerating, onOpenSourceSelection, chats, currentChatId, onArtifactOpen }) {
  const [input, setInput] = useState('');
  const [queryMode, setQueryMode] = useState('Private');
  const bottomRef = useRef(null);
  const [openThoughts, setOpenThoughts] = useState({});
  const toggleThought = (id) => setOpenThoughts(prev => ({ ...prev, [id]: !prev[id] }));

  const handleDownloadReport = (e, msg) => {
    e.stopPropagation();
    const date = new Date().toISOString().split('T')[0];
    
    // Strip Artifacts from content
    const cleanContent = msg.content.replace(/\[ARTIFACT:.*?\][\s\S]*?\[\/ARTIFACT\]/g, '').trim();

    // Convert basic markdown to HTML for the report
    const htmlContent = cleanContent
      .replace(/### (.*)/g, '<h3>$1</h3>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '<br/><br/>')
      .replace(/- (.*)/g, '<li>$1</li>');

    let citationsHtml = '';
    if (msg.citations && msg.citations.length > 0) {
      const uniqueSources = {};
      msg.citations.forEach(cite => {
        if (!uniqueSources[cite.source]) uniqueSources[cite.source] = cite;
      });
      citationsHtml = '<h3>--- COMPLIANCE / EVIDENCE SOURCES ---</h3><ul>';
      Object.values(uniqueSources).forEach((cite) => {
        citationsHtml += `<li>${cite.source}</li>`;
      });
      citationsHtml += '</ul>';
    }

    const reportHtml = `
      <html>
        <head>
          <title>Audit_Report_${date}</title>
          <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #1e293b; line-height: 1.6; }
            h2 { color: #3730a3; border-bottom: 2px solid #e0e7ff; padding-bottom: 10px; margin-bottom: 5px; }
            h3 { color: #334155; margin-top: 25px; border-bottom: 1px solid #f1f5f9; padding-bottom: 5px; }
            .header { text-align: center; margin-bottom: 40px; }
            .meta { font-size: 13px; color: #64748b; margin-bottom: 20px; font-weight: bold; letter-spacing: 1px; }
            .content { font-size: 14px; }
            li { margin-bottom: 8px; }
            .footer { margin-top: 40px; font-size: 11px; text-align: center; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 20px; font-weight: 500; }
          </style>
        </head>
        <body>
          <div class="header">
            <h2>CONFIDENTIAL: INDUSTRIAL AUDIT EVIDENCE</h2>
            <div class="meta">DATE: ${date} | SYSTEM: Industrial Mind OS Unified Asset Brain</div>
          </div>
          
          <div class="content">
            ${htmlContent}
          </div>
          
          <div class="citations">
            ${citationsHtml}
          </div>

          <div class="footer">
            Generated by Industrial Mind OS • Certified Audit Trail
          </div>
        </body>
      </html>
    `;

    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    document.body.appendChild(iframe);
    
    iframe.contentDocument.write(reportHtml);
    iframe.contentDocument.close();

    // Wait for images/styles to load then print
    setTimeout(() => {
      iframe.contentWindow.focus();
      iframe.contentWindow.print();
      
      // Cleanup
      setTimeout(() => {
        document.body.removeChild(iframe);
      }, 1000);
    }, 250);
  };

  // Initialize with welcome message - re-runs when switching chats
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: 'Hello. I am connected to your Industrial Mind OS enterprise knowledge base. How can I assist you today?'
      }]);
    }
  }, [currentChatId]); // re-fire on chat switch

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    if (onSendMessage) {
      onSendMessage(e, input, queryMode);
      setInput('');
      return;
    }
  };

  return (
    <div className="flex flex-col h-full bg-white relative">

      {/* Header */}
      <div className={`p-4 border-b border-indigo-100 bg-gradient-to-r from-indigo-50/50 to-white sticky top-0 z-10 flex items-center justify-between shadow-sm transition-all duration-300 ${!isSidebarOpen ? 'pl-20' : ''}`}>
        <h2 className="font-semibold text-indigo-950 flex items-center space-x-2">
          <Bot className="w-5 h-5 text-indigo-500" />
          <span>Knowledge Chat</span>
        </h2>
      </div>

      {/* Selection Gate Overlay — only when chat has welcome msg OR is empty and no files selected */}
      {(messages.length === 0 || (messages.length === 1 && messages[0]?.id === 'welcome')) &&
        (chats?.find(c => c.id === currentChatId)?.selectedFiles?.length === 0) && (
        <div className="absolute inset-x-0 bottom-[100px] top-[73px] z-50 bg-white/80 backdrop-blur-md flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-500">
          <div className="w-20 h-20 bg-indigo-50 rounded-3xl flex items-center justify-center mb-6 border border-indigo-100 shadow-xl shadow-indigo-500/10">
            <Brain className="w-10 h-10 text-indigo-600 animate-pulse" />
          </div>
          <h3 className="text-2xl font-bold text-slate-900 mb-2 tracking-tight">Activate your Knowledge</h3>
          <p className="text-slate-500 max-w-sm mb-8 leading-relaxed font-medium">
            This chat needs a target focus. Select which uploaded documents I should look into for answers.
          </p>
          <button
            onClick={() => onOpenSourceSelection && onOpenSourceSelection()}
            className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold text-sm shadow-xl shadow-indigo-200 transition-all transform active:scale-95 flex items-center gap-2"
          >
            <Filter className="w-4 h-4" /> Pick Data Sources
          </button>
        </div>
      )}

      {/* Message List — Claude-style layout */}
      <div className="flex-1 overflow-y-auto bg-[#f8fafc]">
        <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id}>
              {msg.role === 'user' ? (
                /* ── User message: right-aligned compact pill ── */
                <div className="flex justify-end">
                  <div className="max-w-[75%] bg-indigo-600 text-white px-4 py-3 rounded-2xl rounded-br-sm shadow-md shadow-indigo-200 text-[15px] leading-relaxed">
                    {msg.content}
                  </div>
                </div>
              ) : (
                /* ── Assistant message: full-width Claude-style card ── */
                <div className="flex gap-3 group" onClick={() => setActiveMessageId(msg.id)}>
                  {/* Avatar */}
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm shadow-indigo-200">
                    <Bot className="w-4 h-4 text-white" />
                  </div>

                  {/* Content card */}
                  <div className="flex-1 min-w-0">
                    {/* Model label */}
                    <p className="text-[11px] font-bold text-indigo-500 uppercase tracking-widest mb-2">Industrial Mind OS</p>

                    {msg.isTyping ? (
                      <div className="bg-white rounded-2xl border border-slate-200/80 px-5 py-4 shadow-sm">
                        <LiveAgentLoader mode={queryMode} />
                      </div>
                    ) : (
                      <>
                        {/* Thought Process (collapsible) */}
                        {msg.steps && msg.steps.length > 0 && (
                          <div className="mb-3">
                            <button
                              onClick={(e) => { e.stopPropagation(); toggleThought(msg.id); }}
                              className="flex items-center gap-2 text-xs text-slate-400 hover:text-indigo-600 transition-colors font-semibold px-3 py-1.5 rounded-lg border border-slate-200 hover:border-indigo-200 bg-white hover:bg-indigo-50 shadow-sm"
                            >
                              <Bot className="w-3.5 h-3.5" />
                              <span>View Thought Process</span>
                              {openThoughts[msg.id] ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                            </button>
                            {openThoughts[msg.id] && (
                              <div className="mt-2 p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-600 text-xs space-y-1.5 shadow-inner">
                                {msg.steps.map((step, idx) => (
                                  <div key={idx} className="flex items-start gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0" />
                                    <span>{step.step} — <span className="text-emerald-600 font-semibold">{step.status}</span></span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Main response — no bubble constraint, clean prose */}
                        <div className="bg-white rounded-2xl border border-slate-200/80 px-5 py-4 shadow-sm text-[15px] leading-relaxed text-slate-800">
                          <MarkdownRenderer content={msg.content} onArtifactOpen={onArtifactOpen} />
                        </div>

                        {/* Citations & Export Actions */}
                        <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
                          <div className="flex flex-wrap gap-2">
                            {msg.citations && msg.citations.length > 0 && (() => {
                              const uniqueSources = {};
                              msg.citations.forEach(cite => {
                                if (!uniqueSources[cite.source]) uniqueSources[cite.source] = cite;
                              });
                              return Object.values(uniqueSources).map((cite, idx) => (
                                <button
                                  key={idx}
                                  onClick={(e) => { e.stopPropagation(); onSourceClick(cite); }}
                                  className="flex items-center gap-1.5 text-xs bg-white border border-indigo-100 text-slate-600 px-3 py-1.5 rounded-full hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700 transition-colors shadow-sm"
                                >
                                  <FileText className="w-3.5 h-3.5 text-indigo-400" />
                                  <span className="font-medium">{cite.source}</span>
                                </button>
                              ));
                            })()}
                          </div>
                          
                          {/* Export Audit Report Button */}
                          <button
                            onClick={(e) => handleDownloadReport(e, msg)}
                            className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 hover:text-white bg-emerald-50 hover:bg-emerald-600 border border-emerald-200 hover:border-emerald-600 px-3 py-1.5 rounded-lg transition-all shadow-sm flex-shrink-0"
                            title="Generate Compliance Evidence Package"
                          >
                            <Download className="w-3.5 h-3.5" />
                            Export Audit Report
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input Box Area */}
      <div className="p-4 bg-white border-t border-slate-200">
        <div className="max-w-4xl mx-auto relative">

          {/* Mode Selector */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">Source:</span>
            {MODES.map(m => {
              const Icon = m.icon;
              const isActive = queryMode === m.key;
              return (
                <button
                  key={m.key}
                  onClick={() => setQueryMode(m.key)}
                  title={m.desc}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-200 border ${isActive
                      ? `${MODE_COLORS[m.key].btn} shadow-md border-transparent`
                      : 'bg-slate-50 text-slate-500 border-slate-200 hover:border-slate-300 hover:text-slate-700'
                    }`}
                >
                  <Icon className="w-3 h-3" />
                  {m.label}
                </button>
              );
            })}
          </div>

          {/* Dynamic Suggestions */}
          {suggestions && suggestions.length > 0 && messages.length <= 1 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {suggestions.map((sug, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(sug)}
                  className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full cursor-pointer transition-colors border border-indigo-200 shadow-sm text-left"
                >
                  {sug}
                </button>
              ))}
            </div>
          )}

          <form onSubmit={handleSubmit} className="relative flex shadow-md shadow-indigo-100/50 rounded-xl border border-slate-200 bg-white focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-indigo-500 transition-all">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask across all your documents..."
              className="w-full bg-transparent pl-5 pr-14 py-3.5 focus:outline-none text-slate-800 text-[15px] placeholder-slate-400"
            />
            {isGenerating ? (
              <button
                type="button"
                onClick={onStopGenerating}
                className="absolute right-2 top-2 p-2 bg-rose-500 hover:bg-rose-600 text-white rounded-lg transition-colors flex items-center justify-center"
                title="Stop Generating"
              >
                <div className="w-5 h-5 flex items-center justify-center">
                  <Square className="w-3.5 h-3.5 fill-current" />
                </div>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                className="absolute right-2 top-2 p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Send Message"
              >
                <Send className="w-5 h-5 pointer-events-none p-0.5" />
              </button>
            )}
          </form>
          <div className="text-center mt-3">
            <p className="text-[11px] text-slate-400">AI answers can vary. Always review cited sources.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
