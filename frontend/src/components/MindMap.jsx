import React, { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import * as d3 from 'd3-force';
import { GitBranch, RefreshCw, X, Home, ZoomIn, Search, MessageSquare, Globe, Fingerprint, MousePointer2, ChevronRight, ChevronLeft } from 'lucide-react';
import { API_URL } from '../api';

// --- UTILITIES ---

function extractChatKeywords(messages) {
  const stopWords = new Set([
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves',
    'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
    'this', 'that', 'these', 'those', 'the', 'a', 'an',
    'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
    'will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must', 'ought',
    'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with',
    'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
    'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
    'what', 'which', 'who', 'whom', 'where', 'why', 'how', 'when',
    'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don',
    'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn', 'didn', 'doesn', 'hadn', 'hasn',
    'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn', 'wasn', 'weren', 'won', 'wouldn',
    'etc', 'also', 'like', 'get', 'got', 'getting', 'make', 'made', 'making', 'take', 'took', 'taking', 'know',
    'knew', 'knowing', 'see', 'saw', 'seen', 'seeing', 'come', 'came', 'coming', 'give', 'gave', 'giving',
    'think', 'thought', 'thinking', 'want', 'wanted', 'wanting', 'say', 'said', 'saying', 'tell', 'told', 'telling',
    'well', 'way', 'let', 'even', 'much', 'many', 'really', 'actually', 'basically', 'literally', 'stuff', 'things', 'thing',
    'please', 'thank', 'thanks', 'hello', 'hi', 'hey', 'ok', 'okay', 'sure', 'yes', 'yeah', 'yep', 'no', 'nope',
    'use', 'using', 'used', 'need', 'needs', 'needed', 'will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must', 'ought',
    'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with',
    'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
    'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
    'what', 'which', 'who', 'whom', 'where', 'why', 'how', 'when',
    'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don',
    'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn', 'didn', 'doesn', 'hadn', 'hasn',
    'haven', 'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn', 'wasn', 'weren', 'won', 'wouldn',
    'etc', 'also', 'like', 'get', 'got', 'getting', 'make', 'made', 'making', 'take', 'took', 'taking', 'know',
    'knew', 'knowing', 'see', 'saw', 'seen', 'seeing', 'come', 'came', 'coming', 'give', 'gave', 'giving',
    'think', 'thought', 'thinking', 'want', 'wanted', 'wanting', 'say', 'said', 'saying', 'tell', 'told', 'telling',
    'well', 'way', 'let', 'even', 'much', 'many', 'really', 'actually', 'basically', 'literally', 'stuff', 'things', 'thing',
    'please', 'thank', 'thanks', 'hello', 'hi', 'hey', 'ok', 'okay', 'sure', 'yes', 'yeah', 'yep', 'no', 'nope',
    'use', 'using', 'used', 'need', 'needs', 'needed'
  ]);
  const keywords = new Set();
  messages.forEach(msg => {
    if (!msg.content) return;
    msg.content.toLowerCase()
      .replace(/[^a-z\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 3 && !stopWords.has(w))
      .forEach(w => keywords.add(w));
  });
  return keywords;
}

function buildAdjacency(nodes, links) {
  const adj = {};
  nodes.forEach(n => { adj[n.id] = []; });
  links.forEach(l => {
    const src = typeof l.source === 'object' ? l.source.id : l.source;
    const tgt = typeof l.target === 'object' ? l.target.id : l.target;
    if (adj[src]) adj[src].push(tgt);
    if (adj[tgt]) adj[tgt].push(src);
  });
  return adj;
}

/**
 * Calculates a horizontal tree layout by setting fx and fy
 * Ensuring strict tree structure (one parent per node in view)
 */
function calculateTreeLayout(rootId, nodes, links, depthLimit = 2) {
  const adj = buildAdjacency(nodes, links);
  const visited = new Set();
  const treeNodes = [];
  const treeLinks = [];

  const queue = [{ id: rootId, depth: 0, parent: null }];
  visited.add(rootId);

  const depthGroups = {};

  while (queue.length > 0) {
    const { id, depth, parent } = queue.shift();
    if (depth > depthLimit) continue;

    if (!depthGroups[depth]) depthGroups[depth] = [];
    depthGroups[depth].push(id);

    // Store node with tree metadata
    const originalNode = nodes.find(n => n.id === id);
    const node = { ...originalNode, depth, parentId: parent?.id };
    treeNodes.push(node);

    if (parent) {
      treeLinks.push({ source: parent.id, target: id });
    }

    (adj[id] || []).forEach(childId => {
      if (!visited.has(childId)) {
        visited.add(childId);
        queue.push({ id: childId, depth: depth + 1, parent: node });
      }
    });
  }

  // Adjust coordinates
  const spacingX = 280;
  const spacingY = 70;

  // Group treeNodes by depth for Y-positioning
  const nodesByDepth = {};
  treeNodes.forEach(n => {
    if (!nodesByDepth[n.depth]) nodesByDepth[n.depth] = [];
    nodesByDepth[n.depth].push(n);
  });

  Object.entries(nodesByDepth).forEach(([dStr, nodesAtDepth]) => {
    const d = parseInt(dStr);
    const total = nodesAtDepth.length;
    nodesAtDepth.forEach((node, i) => {
      node.fx = d * spacingX;
      node.fy = (i - (total - 1) / 2) * spacingY;
    });
  });

  return { nodes: treeNodes, links: treeLinks };
}

// --- MAIN COMPONENT ---

export default function MindMap({ onClose, chatMessages = [] }) {
  const [allGraphData, setAllGraphData] = useState({ nodes: [], links: [] });
  const [displayData, setDisplayData] = useState({ nodes: [], links: [] });
  const [rootId, setRootId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('chat'); // 'chat' | 'full'

  const [hoverNode, setHoverNode] = useState(null);
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const [highlightLinks, setHighlightLinks] = useState(new Set());

  const fgRef = useRef();

  useEffect(() => {
    fetchGraphData();
  }, []);

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('imos_token');
      const response = await fetch(`${API_URL}/api/v1/graph/data`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setAllGraphData(data);
      }
    } catch (err) {
      console.error("Graph fetch failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const adjacency = useMemo(() => buildAdjacency(allGraphData.nodes, allGraphData.links), [allGraphData]);

  const processData = useCallback(() => {
    if (allGraphData.nodes.length === 0) return;

    let nodesToUse = allGraphData.nodes;
    let linksToUse = allGraphData.links;

    if (viewMode === 'chat') {
      const keywords = extractChatKeywords(chatMessages);
      if (keywords.size > 0) {
        const matched = new Set(allGraphData.nodes.filter(n => [...keywords].some(kw => (n.name || '').toLowerCase().includes(kw))).map(n => n.id));
        if (matched.size > 0) {
          const expanded = new Set(matched);
          matched.forEach(id => (adjacency[id] || []).forEach(neighbor => expanded.add(neighbor)));
          nodesToUse = allGraphData.nodes.filter(n => expanded.has(n.id));
          linksToUse = allGraphData.links.filter(l => {
            const s = typeof l.source === 'object' ? l.source.id : l.source;
            const t = typeof l.target === 'object' ? l.target.id : l.target;
            return expanded.has(s) && expanded.has(t);
          });
        }
      }
    }

    const localAdj = buildAdjacency(nodesToUse, linksToUse);
    const central = nodesToUse.reduce((best, n) =>
      (localAdj[n.id]?.length || 0) > (localAdj[best.id]?.length || 0) ? n : best
      , nodesToUse[0]);

    if (central) {
      setRootId(central.id);
      const tree = calculateTreeLayout(central.id, nodesToUse, linksToUse, 2);
      setDisplayData(tree);
      if (fgRef.current) setTimeout(() => fgRef.current.zoomToFit(600, 100), 100);
    }
  }, [allGraphData, chatMessages, viewMode, adjacency]);

  useEffect(() => { processData(); }, [processData]);

  const handleNodeClick = useCallback((node) => {
    setRootId(node.id);
    const tree = calculateTreeLayout(node.id, allGraphData.nodes, allGraphData.links, 2);
    setDisplayData(tree);
    if (fgRef.current) {
      fgRef.current.centerAt(node.x, node.y, 600);
      fgRef.current.zoom(1.2, 600);
    }
  }, [allGraphData]);

  const handleNodeHover = useCallback((node) => {
    setHoverNode(node || null);
    const hNodes = new Set();
    const hLinks = new Set();
    if (node) {
      hNodes.add(node.id);
      displayData.links.forEach(l => {
        const s = typeof l.source === 'object' ? l.source.id : l.source;
        const t = typeof l.target === 'object' ? l.target.id : l.target;
        if (s === node.id || t === node.id) {
          hLinks.add(l);
          hNodes.add(s); hNodes.add(t);
        }
      });
    }
    setHighlightNodes(hNodes);
    setHighlightLinks(hLinks);
  }, [displayData.links]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 lg:p-8 animate-in fade-in duration-700">
      <div className="absolute inset-0 bg-slate-200/60 backdrop-blur-xl" onClick={onClose} />

      <div className="relative w-full h-full max-w-7xl bg-white rounded-[2.5rem] shadow-[0_48px_100px_-20px_rgba(0,0,0,0.15)] overflow-hidden flex flex-col border border-slate-200 ring-1 ring-slate-100 font-outfit">

        {/* Header */}
        <div className="flex items-center justify-between px-10 py-8 border-b border-slate-100 bg-white/80 backdrop-blur-xl z-20">
          <div className="flex items-center gap-6">
            <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center border border-indigo-100">
              <GitBranch className="w-8 h-8 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-2xl font-black text-slate-900 tracking-tight">Enterprise Brain Map</h2>
              <div className="flex items-center gap-2 mt-1.5">
                <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                <span className="text-[10px] font-black text-indigo-600 uppercase tracking-[0.2em]">Logical Tree Projection</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-5">
            <div className="flex bg-slate-100 p-1 rounded-2xl border border-slate-200">
              <button onClick={() => setViewMode('chat')} className={`px-5 py-2 rounded-xl text-[11px] font-bold transition-all ${viewMode === 'chat' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-900'}`}>
                <MessageSquare className="w-3.5 h-3.5 inline mr-2" /> Context
              </button>
              <button onClick={() => setViewMode('full')} className={`px-5 py-2 rounded-xl text-[11px] font-bold transition-all ${viewMode === 'full' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-900'}`}>
                <Globe className="w-3.5 h-3.5 inline mr-2" /> Hub Nodes
              </button>
            </div>
            <button onClick={onClose} className="w-12 h-12 flex items-center justify-center bg-slate-100 hover:bg-rose-50 rounded-2xl transition-all border border-slate-200 text-slate-400 hover:text-rose-600">
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 relative bg-[radial-gradient(#e2e8f0_1.5px,transparent_1.5px)] [background-size:40px_40px]">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center flex-col z-30 bg-white/90">
              <RefreshCw className="w-14 h-14 text-indigo-500 animate-spin mb-6" />
              <span className="text-indigo-600 font-bold text-xs uppercase tracking-[0.3em]">Synapsing Logic...</span>
            </div>
          )}

          {!loading && displayData.nodes.length > 0 && (
            <ForceGraph2D
              ref={fgRef}
              graphData={displayData}
              nodeRelSize={0}
              linkCanvasObject={(link, ctx) => {
                const s = link.source;
                const t = link.target;
                if (!s || !t || s.x === undefined || t.x === undefined) return;

                const isHighlight = highlightLinks.has(link);
                ctx.beginPath();
                ctx.strokeStyle = isHighlight ? '#4f46e5' : '#cbd5e1';
                ctx.lineWidth = isHighlight ? 2.5 : 1.2;

                // --- S-CURVE Logic ---
                const startX = s.x + (s.__width || 0) / 2 + 15;
                const endX = t.x - (t.__width || 0) / 2 - 5;

                const cp1x = startX + (endX - startX) / 2;
                const cp2x = endX - (endX - startX) / 2;

                ctx.moveTo(startX, s.y);
                ctx.bezierCurveTo(cp1x, s.y, cp2x, t.y, endX, t.y);
                ctx.stroke();

                if (isHighlight) {
                  const t_flow = (Date.now() % 1500) / 1500;
                  const pos = getBezierPoint(t_flow, startX, s.y, cp1x, s.y, cp2x, t.y, endX, t.y);
                  ctx.fillStyle = '#4f46e5';
                  ctx.beginPath();
                  ctx.arc(pos.x, pos.y, 2.5, 0, 2 * Math.PI);
                  ctx.fill();
                }
              }}
              onNodeHover={handleNodeHover}
              onNodeClick={handleNodeClick}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const isRoot = node.id === rootId;
                const isHover = hoverNode === node;
                const isHighlight = highlightNodes.has(node.id);
                const isDimmed = hoverNode && !isHighlight;

                const label = node.name || 'Concept';
                const fontSize = Math.max(12, 16 / globalScale);
                ctx.font = `${isRoot ? '800' : '600'} ${fontSize}px "Outfit", sans-serif`;

                const textWidth = ctx.measureText(label).width;
                const bWidth = textWidth + fontSize * 2.5;
                const bHeight = fontSize * 2.5;
                const r = 10;

                node.__width = bWidth;
                ctx.globalAlpha = isDimmed ? 0.2 : 1.0;

                const x = node.x - bWidth / 2;
                const y = node.y - bHeight / 2;

                // --- Node Pill ---
                ctx.beginPath();
                ctx.roundRect(x, y, bWidth, bHeight, r);
                ctx.fillStyle = isRoot ? '#4f46e5' : '#ffffff';
                ctx.strokeStyle = isRoot ? '#4338ca' : (isHighlight ? '#6366f1' : '#e2e8f0');
                ctx.lineWidth = 1.5 / globalScale;
                ctx.shadowColor = 'rgba(0,0,0,0.05)';
                ctx.shadowBlur = 10;
                ctx.fill();
                ctx.shadowBlur = 0; // reset
                ctx.stroke();

                // --- BRACKET INDICATOR ---
                const hasChildren = displayData.links.some(l => (typeof l.source === 'object' ? l.source.id : l.source) === node.id);
                if (hasChildren) {
                  const bx = x + bWidth + 15;
                  ctx.beginPath();
                  ctx.arc(bx, node.y, 8, 0, 2 * Math.PI);
                  ctx.fillStyle = '#ffffff';
                  ctx.strokeStyle = '#e2e8f0';
                  ctx.fill();
                  ctx.stroke();

                  // Small < bracket
                  ctx.font = `bold ${8 / globalScale}px monospace`;
                  ctx.fillStyle = '#6366f1';
                  ctx.textAlign = 'center';
                  ctx.fillText('<', bx, node.y + 1);
                }

                // Text
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.font = `${isRoot ? '800' : '600'} ${fontSize}px "Outfit", sans-serif`;
                ctx.fillStyle = isRoot ? '#ffffff' : (isHighlight ? '#1e293b' : '#64748b');
                ctx.fillText(label, node.x, node.y);
                ctx.globalAlpha = 1.0;
              }}
              nodePointerAreaPaint={(node, color, ctx) => {
                const w = (node.__width || 40) + 30;
                ctx.fillStyle = color;
                ctx.fillRect(node.x - w / 2, node.y - 20, w, 40);
              }}
              enableNodeDrag={false}
              cooldownTicks={100}
            />
          )}

          {/* Interaction Instruction Overlay */}
          <div className="absolute top-10 right-10 flex items-center gap-3 bg-white/80 text-indigo-600 px-6 py-4 rounded-3xl border border-indigo-100 shadow-xl backdrop-blur-md">
            <span className="text-[10px] font-black uppercase tracking-[0.15em]">Single-Point Logical Expansion</span>
          </div>
        </div>

        {/* Footer */}
        <div className="px-10 py-6 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-10">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-indigo-600" />
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Selected Focus</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-1 bg-slate-200 rounded-full" />
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Hierarchical Link</span>
            </div>
          </div>
          <div className="text-[10px] font-black text-indigo-600/40 uppercase tracking-[0.4em]">
            Precision Knowledge Mapping v2.5
          </div>
        </div>
      </div>
    </div>
  );
}

function getBezierPoint(t, p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y) {
  const cx = 3 * (p1x - p0x);
  const bx = 3 * (p2x - p1x) - cx;
  const ax = p3x - p0x - cx - bx;
  const cy = 3 * (p1y - p0y);
  const by = 3 * (p2y - p1y) - cy;
  const ay = p3y - p0y - cy - by;
  const x = ax * (t ** 3) + bx * (t ** 2) + cx * t + p0x;
  const y = ay * (t ** 3) + by * (t ** 2) + cy * t + p0y;
  return { x, y };
}
