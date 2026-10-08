import { useState, useEffect, useRef } from 'react';
import { X, Copy, ExternalLink, Code2, Globe, Table2, ChevronRight, ShieldAlert } from 'lucide-react';
import EightDIncidentStudio from './EightDStudio/EightDIncidentStudio';

function parse8DReport(artifact) {
  if (!artifact) return null;
  if (artifact.type === '8d_report' || artifact.type === 'rca') {
    if (artifact.report && typeof artifact.report === 'object') return artifact.report;
    if (artifact.data && typeof artifact.data === 'object') return artifact.data;
  }
  if (artifact.data && typeof artifact.data === 'object' && (artifact.data.d1_team || artifact.data.report_id)) {
    return artifact.data;
  }
  if (artifact.report && typeof artifact.report === 'object') {
    return artifact.report;
  }
  if (typeof artifact.content === 'string') {
    const trimmed = artifact.content.trim();
    if (trimmed.startsWith('{') && (trimmed.includes('d1_team') || trimmed.includes('d2_problem') || trimmed.includes('report_id'))) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed.d1_team || parsed.d2_problem || parsed.report_id) {
          return parsed;
        }
      } catch {
        // Not valid JSON
      }
    }
  }
  return null;
}

function detectArtifactType(content) {
  const trimmed = typeof content === 'string' ? content.trim() : '';
  if (/^\s*<(html|!DOCTYPE|div|section|main|article)/i.test(trimmed)) return 'html';
  if (/^\s*```(\w+)?/.test(trimmed) || /^(import |from |def |class |function |const |let |var |#include|package )/.test(trimmed)) return 'code';
  if (/^\|.+\|/.test(trimmed) || trimmed.includes('\n|')) return 'table';
  if (/^\s*</.test(trimmed)) return 'html';
  return 'code';
}

function detectLanguage(content) {
  if (/^\s*</.test(content.trim())) return 'html';
  if (/import React|jsx|tsx/.test(content)) return 'jsx';
  if (/def |import |from |print\(/.test(content)) return 'python';
  if (/public class|System\.out/.test(content)) return 'java';
  if (/const |let |var |function |=>/.test(content)) return 'javascript';
  if (/SELECT|INSERT|CREATE TABLE/i.test(content)) return 'sql';
  return 'text';
}

function CodeView({ content }) {
  const [copied, setCopied] = useState(false);
  const lang = detectLanguage(content);

  // Strip markdown code fences if present
  const cleanContent = content.replace(/^```\w*\n?/, '').replace(/\n?```$/, '');

  const handleCopy = () => {
    navigator.clipboard.writeText(cleanContent).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">{lang}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white px-3 py-1.5 rounded-lg hover:bg-slate-700 transition-all"
        >
          <Copy className="w-3.5 h-3.5" />
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        <pre className="p-5 text-sm text-slate-200 font-mono leading-relaxed whitespace-pre-wrap min-h-full bg-slate-900">
          <code>{cleanContent}</code>
        </pre>
      </div>
    </div>
  );
}

function HtmlView({ content, title }) {
  const iframeRef = useRef(null);
  const [copied, setCopied] = useState(false);

  const cleanContent = content.replace(/^```\w*\n?/, '').replace(/\n?```$/, '');

  const handleCopy = () => {
    navigator.clipboard.writeText(cleanContent).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleOpenNewTab = () => {
    const fullHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${title || 'Industrial Mind OS Design'}</title>
          <script src="https://cdn.tailwindcss.com"></script>
          <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
          <style>
            body { font-family: 'Inter', sans-serif; background: #f8fafc; margin: 0; min-height: 100vh; padding: 40px; }
            .container { max-width: 1000px; margin: 0 auto; }
            ::-webkit-scrollbar { width: 10px; }
            ::-webkit-scrollbar-track { background: #f8fafc; }
            ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 5px; }
          </style>
        </head>
        <body>
          <div class="container">${cleanContent}</div>
        </body>
      </html>
    `;
    const blob = new Blob([fullHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  };

  useEffect(() => {
    if (iframeRef.current) {
      const doc = iframeRef.current.contentDocument || iframeRef.current.contentWindow.document;
      doc.open();
      doc.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
              body { font-family: 'Inter', sans-serif; background: #f8fafc; margin: 0; padding: 20px; }
              ::-webkit-scrollbar { width: 8px; }
              ::-webkit-scrollbar-track { background: #f8fafc; }
              ::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 4px; }
              ::-webkit-scrollbar-thumb:hover { background: #cbd5e1; }
            </style>
          </head>
          <body>
            ${cleanContent}
          </body>
        </html>
      `);
      doc.close();
    }
  }, [cleanContent]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-slate-200">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
          <Globe className="w-3.5 h-3.5 text-emerald-500" /> Live Preview
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-all"
          >
            <Copy className="w-3.5 h-3.5" />
            {copied ? 'Copied!' : 'Copy HTML'}
          </button>
          <button
            onClick={handleOpenNewTab}
            className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 px-3 py-1.5 rounded-lg hover:bg-indigo-50 transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Open Full
          </button>
        </div>
      </div>
      <div className="flex-1 relative bg-white">
        <iframe
          ref={iframeRef}
          sandbox="allow-scripts allow-same-origin"
          title="Artifact Preview"
          className="w-full h-full border-none"
        />
      </div>
    </div>
  );
}

function TableView({ content }) {
  // Parse simple markdown tables
  const lines = content.trim().split('\n').filter(l => l.trim().startsWith('|'));
  const headers = lines[0]?.split('|').filter(c => c.trim()) || [];
  const separator = lines[1]; // skip separator row
  const rows = lines.slice(2).map(l => l.split('|').filter(c => c.trim()));

  if (headers.length === 0) {
    return <CodeView content={content} />;
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-4 py-2 bg-slate-50 border-b border-slate-200">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
          <Table2 className="w-3.5 h-3.5 text-violet-500" /> Interactive Table
        </span>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <table className="min-w-full divide-y divide-slate-200 rounded-xl overflow-hidden shadow-sm border border-slate-200">
          <thead className="bg-indigo-50">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className="px-4 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider">
                  {h.trim()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100">
            {rows.map((row, ri) => (
              <tr key={ri} className="hover:bg-indigo-50/30 transition-colors">
                {headers.map((_, ci) => (
                  <td key={ci} className="px-4 py-3 text-sm text-slate-700">
                    {row[ci]?.trim() || ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ArtifactPanel({ artifact, onClose, onSourceClick }) {
  const [isVisible, setIsVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('preview');

  useEffect(() => {
    if (artifact) {
      setTimeout(() => setIsVisible(true), 10);
    } else {
      setIsVisible(false);
    }
  }, [artifact]);

  if (!artifact) return null;

  const eightDReport = parse8DReport(artifact);
  const is8D = Boolean(eightDReport);

  const type = is8D ? '8d_report' : detectArtifactType(artifact.content);
  const isHtml = type === 'html';
  const isTable = type === 'table';
  const isCode = type === 'code';

  const TypeIcon = is8D ? ShieldAlert : isHtml ? Globe : isTable ? Table2 : Code2;
  const typeLabel = is8D ? '8D Incident Studio' : isHtml ? 'Designer UI' : isTable ? 'Data View' : 'Code';
  const typeBadgeColor = is8D
    ? 'bg-rose-100 text-rose-700'
    : isHtml
    ? 'bg-emerald-100 text-emerald-700'
    : isTable
    ? 'bg-violet-100 text-violet-700'
    : 'bg-slate-100 text-slate-700';

  // Determine available tabs
  const tabs = [];
  if (is8D) {
    tabs.push('studio');
    if (typeof artifact.content === 'string' && artifact.content.trim()) tabs.push('code');
  } else if (isHtml) {
    tabs.push('preview', 'code');
  } else if (isTable) {
    tabs.push('preview', 'table', 'code');
  } else {
    tabs.push('code');
  }

  // Default tab fallback
  useEffect(() => {
    if (is8D) setActiveTab('studio');
    else if (isHtml) setActiveTab('preview');
    else if (isTable) setActiveTab('preview');
    else setActiveTab('code');
  }, [artifact, is8D, isHtml, isTable]);

  return (
    <div className="w-full h-full flex flex-col bg-white border-l border-slate-200">
      <div className="flex flex-col h-full w-full bg-white shadow-2xl shadow-indigo-900/10">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-200 bg-gradient-to-r from-indigo-50/60 to-white flex-shrink-0">
          <div className="w-9 h-9 rounded-xl bg-indigo-600/10 flex items-center justify-center border border-indigo-200 flex-shrink-0">
            <TypeIcon className="w-4.5 h-4.5 text-indigo-600" size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-bold text-slate-900 truncate">{artifact.title || (is8D ? '8D Incident Report' : 'Artifact')}</h3>
            <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full ${typeBadgeColor}`}>
              {typeLabel}
            </span>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-slate-700 flex-shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Improved Universal Tab Bar */}
        {tabs.length > 1 && (
          <div className="flex border-b border-slate-200 bg-slate-50 flex-shrink-0">
            {tabs.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2.5 text-xs font-semibold uppercase tracking-widest transition-all relative ${
                  activeTab === tab ? 'text-indigo-600 font-bold' : 'text-slate-400 hover:text-slate-600'
                }`}
              >
                {tab === 'studio' ? '🛡️ 8D Studio' : tab === 'preview' ? '🌐 Preview' : tab === 'code' ? '</> Code' : '📋 Table'}
                {activeTab === tab && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600" />}
              </button>
            ))}
          </div>
        )}

        {/* Content Area */}
        <div className="flex-1 overflow-hidden relative">
          {activeTab === 'studio' && is8D && (
            <EightDIncidentStudio
              report={eightDReport}
              onSourceClick={onSourceClick}
              onClose={onClose}
              isModal={false}
            />
          )}
          {activeTab === 'preview' && isHtml && <HtmlView content={artifact.content} title={artifact.title} />}
          {activeTab === 'preview' && isTable && <TableView content={artifact.content} />}
          {activeTab === 'code' && (
            <CodeView
              content={
                typeof artifact.content === 'string'
                  ? artifact.content
                  : JSON.stringify(artifact.content || eightDReport, null, 2)
              }
            />
          )}
          {activeTab === 'table' && isTable && <TableView content={artifact.content} />}
        </div>
      </div>
    </div>
  );
}
