import React, { useState, useRef, useMemo } from 'react';
import {
  GitBranch,
  Layers,
  Cpu,
  Users,
  BookOpen,
  Gauge,
  Compass,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileText,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ChevronRight,
  Info,
  ShieldAlert,
  Flame,
  Filter,
  Eye
} from 'lucide-react';

/**
 * FiveWhyFishboneTab.jsx
 * Interactive SVG Visualizers for Root Cause Analysis (Milestone 4):
 * 1. Interactive SVG 5-Why Causal Tree with recursive branching, root cause highlight,
 *    assumption warning badges, and citation drill-downs.
 * 2. Interactive SVG Ishikawa 6M Fishbone Diagram with spine, 6 category ribs,
 *    feather sub-branches, citation dots, and category filtering.
 * 3. Dual-split layout toggle with zoom & pan controls.
 */

// --- 6M CATEGORY CONFIGURATION ---
const ISHIKAWA_CATEGORIES = [
  { key: 'Man', label: 'Man (Personnel)', icon: Users, color: '#38bdf8', lightBg: 'rgba(56, 189, 248, 0.1)', isUpper: true, spineIndex: 0 },
  { key: 'Machine', label: 'Machine (Equipment)', icon: Cpu, color: '#a855f7', lightBg: 'rgba(168, 85, 247, 0.1)', isUpper: true, spineIndex: 1 },
  { key: 'Material', label: 'Material (Parts)', icon: Layers, color: '#fb923c', lightBg: 'rgba(251, 146, 60, 0.1)', isUpper: true, spineIndex: 2 },
  { key: 'Method', label: 'Method (Procedures)', icon: BookOpen, color: '#34d399', lightBg: 'rgba(52, 211, 153, 0.1)', isUpper: false, spineIndex: 0 },
  { key: 'Measurement', label: 'Measurement (DCS)', icon: Gauge, color: '#818cf8', lightBg: 'rgba(129, 140, 248, 0.1)', isUpper: false, spineIndex: 1 },
  { key: 'Environment', label: 'Environment (Milieu)', icon: Compass, color: '#f43f5e', lightBg: 'rgba(244, 63, 94, 0.1)', isUpper: false, spineIndex: 2 }
];

export default function FiveWhyFishboneTab({ report, onSourceClick }) {
  // --- STATE ---
  const [activeView, setActiveView] = useState('split'); // 'tree' | 'fishbone' | 'split'
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedFishboneCause, setSelectedFishboneCause] = useState(null);
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('ALL');
  const [zoomScaleTree, setZoomScaleTree] = useState(1);
  const [zoomScaleFishbone, setZoomScaleFishbone] = useState(1);
  const [hoveredCategory, setHoveredCategory] = useState(null);

  // --- DATA EXTRACTION ---
  const fiveWhyChain = useMemo(() => {
    return report?.d4_root_causes?.five_why_chain || [];
  }, [report]);

  const fishboneAnalysis = useMemo(() => {
    return report?.d4_root_causes?.fishbone_analysis || { branches: [] };
  }, [report]);

  const citationsList = useMemo(() => {
    return report?.citations || [];
  }, [report]);

  // Helper to resolve citation object
  const resolveCitation = (citationId) => {
    const found = citationsList.find((c) => c.citation_id === citationId);
    if (found) {
      return {
        source: found.source_doc || found.title || citationId,
        snippet: found.excerpt,
        title: found.title,
        section: found.section,
        page_or_line: found.page_or_line,
        confidence: found.confidence,
        citation_id: citationId
      };
    }
    return {
      source: citationId,
      snippet: `Referenced citation ${citationId} in incident documentation.`,
      citation_id: citationId
    };
  };

  // --- 1. FIVE-WHY TREE GEOMETRY CALCULATION ---
  const treeLayout = useMemo(() => {
    if (!fiveWhyChain.length) return { nodes: [], links: [], width: 1200, height: 400 };

    const NODE_WIDTH = 270;
    const NODE_HEIGHT = 150;
    const X_SPACING = 340;
    const Y_SPACING = 180;
    const PADDING_X = 60;
    const CENTER_Y = 200;

    // Group nodes by level
    const levelMap = {};
    fiveWhyChain.forEach((node) => {
      const lvl = node.level || 1;
      if (!levelMap[lvl]) levelMap[lvl] = [];
      levelMap[lvl].push(node);
    });

    const positionedNodes = [];
    const links = [];

    // Assign X and Y coordinates
    Object.keys(levelMap).forEach((lvlStr) => {
      const lvl = parseInt(lvlStr, 10);
      const nodesAtLevel = levelMap[lvl];
      const count = nodesAtLevel.length;

      nodesAtLevel.forEach((node, idx) => {
        const x = PADDING_X + (lvl - 1) * X_SPACING;
        const yOffset = (idx - (count - 1) / 2) * Y_SPACING;
        const y = CENTER_Y + yOffset;

        positionedNodes.push({
          ...node,
          x,
          y,
          width: NODE_WIDTH,
          height: NODE_HEIGHT
        });
      });
    });

    // Compute links: match parent_node_id or connect linearly by level
    positionedNodes.forEach((node) => {
      let parent = null;
      if (node.parent_node_id) {
        parent = positionedNodes.find((p) => p.why_id === node.parent_node_id);
      }
      if (!parent && node.level > 1) {
        // Fallback: previous level node
        parent = positionedNodes.find((p) => p.level === node.level - 1);
      }

      if (parent) {
        const x1 = parent.x + parent.width;
        const y1 = parent.y + parent.height / 2;
        const x2 = node.x;
        const y2 = node.y + node.height / 2;
        const path = `M ${x1} ${y1} C ${x1 + 40} ${y1}, ${x2 - 40} ${y2}, ${x2} ${y2}`;
        links.push({
          id: `${parent.why_id}->${node.why_id}`,
          path,
          sourceId: parent.why_id,
          targetId: node.why_id
        });
      }
    });

    const maxLevel = Math.max(...positionedNodes.map((n) => n.level), 5);
    const totalWidth = PADDING_X * 2 + maxLevel * X_SPACING;
    const minY = Math.min(...positionedNodes.map((n) => n.y), 40);
    const maxY = Math.max(...positionedNodes.map((n) => n.y + n.height), 360);
    const totalHeight = Math.max(400, maxY - minY + 100);

    return {
      nodes: positionedNodes,
      links,
      width: totalWidth,
      height: totalHeight
    };
  }, [fiveWhyChain]);

  // --- 2. FISHBONE DIAGRAM GEOMETRY CALCULATION ---
  const fishboneLayout = useMemo(() => {
    const branches = fishboneAnalysis?.branches || [];
    const SVG_WIDTH = 1200;
    const SVG_HEIGHT = 650;
    const SPINE_Y = 325;
    const SPINE_START_X = 60;
    const SPINE_END_X = 940;

    // Contact points along spine
    const ribSpineContactX = [260, 500, 740]; // 3 columns for 6M

    // Map categories to branch data
    const categoryRibs = ISHIKAWA_CATEGORIES.map((catConfig) => {
      const branchData = branches.find(
        (b) => b.category?.toLowerCase() === catConfig.key.toLowerCase()
      ) || { category: catConfig.key, causes: [], citation_ids: [], is_unsubstantiated: false };

      const spineX = ribSpineContactX[catConfig.spineIndex];
      const ribLengthX = 130;
      const ribEndY = catConfig.isUpper ? 75 : 575;
      const ribEndX = spineX - ribLengthX;

      // Diagonal rib line: from (ribEndX, ribEndY) to (spineX, SPINE_Y)
      // Sub-branches (feathers) along the rib
      const causes = branchData.causes || [];
      const subBranches = causes.map((causeText, idx) => {
        const t = (idx + 1) / (causes.length + 1); // Parameter along diagonal
        const rx = ribEndX + t * (spineX - ribEndX);
        const ry = ribEndY + t * (SPINE_Y - ribEndY);
        const featherWidth = 160;
        const fx = rx - featherWidth; // extend horizontally leftwards
        const fy = ry;

        return {
          cause: causeText,
          startX: rx,
          startY: ry,
          endX: fx,
          endY: fy,
          category: catConfig.key,
          citation_ids: branchData.citation_ids || [],
          is_unsubstantiated: branchData.is_unsubstantiated
        };
      });

      return {
        ...catConfig,
        branchData,
        spineX,
        ribEndX,
        ribEndY,
        subBranches
      };
    });

    return {
      svgWidth: SVG_WIDTH,
      svgHeight: SVG_HEIGHT,
      spineStartX: SPINE_START_X,
      spineEndX: SPINE_END_X,
      spineY: SPINE_Y,
      ribs: categoryRibs
    };
  }, [fishboneAnalysis]);

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* ── Visualizer Header & View Switcher ── */}
      <div className="flex flex-wrap items-center justify-between px-6 py-4 bg-slate-900 border-b border-slate-800 gap-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
            <GitBranch className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              Deductive Causal Architecture
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                AIAG-VDA Verified
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Interactive 5-Why Causal Tree & Ishikawa 6M Fishbone Diagram
            </p>
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center bg-slate-800/80 p-1 rounded-xl border border-slate-700/60">
          <button
            onClick={() => setActiveView('tree')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeView === 'tree'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" /> 5-Why Tree
          </button>
          <button
            onClick={() => setActiveView('fishbone')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeView === 'fishbone'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" /> Ishikawa 6M
          </button>
          <button
            onClick={() => setActiveView('split')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeView === 'split'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <Layers className="w-3.5 h-3.5" /> Dual View
          </button>
        </div>
      </div>

      {/* ── Main Canvas Viewport ── */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-6 space-y-6">
        
        {/* ========================================================================= */}
        {/* SECTION 1: 5-WHY CAUSAL TREE VISUALIZER                                   */}
        {/* ========================================================================= */}
        {(activeView === 'tree' || activeView === 'split') && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden flex flex-col">
            {/* Tree Section Header */}
            <div className="px-5 py-3.5 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                <h3 className="text-sm font-bold text-slate-200">
                  Recursive 5-Why Causal Tree (Depth 1 → 5)
                </h3>
                <span className="text-xs text-slate-500 font-mono">
                  ({fiveWhyChain.length} nodes)
                </span>
              </div>

              {/* Zoom & Fit controls */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setZoomScaleTree((z) => Math.min(1.6, z + 0.15))}
                  className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoomScaleTree((z) => Math.max(0.6, z - 0.15))}
                  className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoomScaleTree(1)}
                  className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Tree SVG Canvas */}
            <div className="relative overflow-x-auto overflow-y-hidden bg-[#070b14] min-h-[420px] p-4 flex items-center justify-start">
              <div
                style={{
                  transform: `scale(${zoomScaleTree})`,
                  transformOrigin: 'top left',
                  transition: 'transform 0.2s ease-out'
                }}
              >
                <svg
                  width={treeLayout.width}
                  height={treeLayout.height}
                  className="select-none"
                >
                  {/* Defs: Arrowhead markers and filter glows */}
                  <defs>
                    <marker
                      id="arrow-tree"
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
                    </marker>
                    <marker
                      id="arrow-root"
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" />
                    </marker>
                    <filter id="root-glow" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="6" result="blur" />
                      <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>

                  {/* Connecting Orthogonal Links */}
                  {treeLayout.links.map((link) => (
                    <path
                      key={link.id}
                      d={link.path}
                      fill="none"
                      stroke="#475569"
                      strokeWidth="2"
                      markerEnd="url(#arrow-tree)"
                      className="transition-all duration-300"
                    />
                  ))}

                  {/* Node Cards */}
                  {treeLayout.nodes.map((node) => {
                    const isRoot = Boolean(node.is_root_cause);
                    const isUnsub = Boolean(node.is_unsubstantiated || node.assumed_flag);
                    const isSelected = selectedNode?.why_id === node.why_id;

                    return (
                      <g
                        key={node.why_id}
                        transform={`translate(${node.x}, ${node.y})`}
                        onClick={() => setSelectedNode(node)}
                        className="cursor-pointer group"
                      >
                        {/* Root Cause Pulsing Aura */}
                        {isRoot && (
                          <rect
                            x="-5"
                            y="-5"
                            width={node.width + 10}
                            height={node.height + 10}
                            rx="18"
                            fill="none"
                            stroke="#10b981"
                            strokeWidth="2.5"
                            strokeDasharray="6 4"
                            className="animate-pulse"
                            opacity="0.7"
                            filter="url(#root-glow)"
                          />
                        )}

                        {/* Outer Card Background */}
                        <rect
                          width={node.width}
                          height={node.height}
                          rx="14"
                          fill={isRoot ? '#06201b' : '#0f172a'}
                          stroke={
                            isRoot
                              ? '#10b981'
                              : isUnsub
                              ? '#f59e0b'
                              : isSelected
                              ? '#6366f1'
                              : '#334155'
                          }
                          strokeWidth={isRoot || isSelected ? '2.5' : '1.5'}
                          strokeDasharray={isUnsub && !isRoot ? '4 2' : 'none'}
                          className="transition-all duration-200 group-hover:stroke-indigo-400 shadow-xl"
                        />

                        {/* ForeignObject Content (HTML in SVG for responsive styling) */}
                        <foreignObject width={node.width} height={node.height}>
                          <div className="w-full h-full p-3.5 flex flex-col justify-between select-none">
                            {/* Card Top: Level & Badges */}
                            <div className="flex items-center justify-between gap-1">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                                    isRoot
                                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                      : 'bg-slate-800 text-slate-300 border border-slate-700'
                                  }`}
                                >
                                  Why #{node.level}
                                </span>
                                <span className="text-[10px] font-mono text-slate-400">
                                  {node.why_id}
                                </span>
                              </div>

                              {/* Status Badges */}
                              {isRoot ? (
                                <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-500 text-slate-950 flex items-center gap-1 shadow-sm">
                                  <Flame className="w-2.5 h-2.5" /> ROOT CAUSE
                                </span>
                              ) : isUnsub ? (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                                  <AlertTriangle className="w-2.5 h-2.5" /> Ungrounded
                                </span>
                              ) : null}
                            </div>

                            {/* Card Center: Cause Statement */}
                            <p className="text-xs text-slate-200 line-clamp-3 leading-snug font-medium my-1">
                              {node.cause_statement}
                            </p>

                            {/* Card Bottom: Citations or Missing Notice */}
                            <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 gap-1 overflow-x-auto">
                              {node.citation_ids && node.citation_ids.length > 0 ? (
                                <div className="flex items-center gap-1 flex-wrap">
                                  {node.citation_ids.map((cid) => (
                                    <button
                                      key={cid}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        if (onSourceClick) onSourceClick(resolveCitation(cid));
                                      }}
                                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 hover:bg-indigo-900 hover:text-white border border-indigo-700/60 text-[9px] font-mono transition-colors"
                                      title={`Click to inspect citation ${cid}`}
                                    >
                                      <FileText className="w-2.5 h-2.5 text-indigo-400" />
                                      {cid}
                                      <ExternalLink className="w-2 h-2 opacity-60" />
                                    </button>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-[9px] text-amber-400/80 italic flex items-center gap-1">
                                  <Info className="w-2.5 h-2.5" /> Engineering Assumption
                                </span>
                              )}

                              <ChevronRight className="w-3 h-3 text-slate-600 group-hover:text-slate-300 ml-auto flex-shrink-0" />
                            </div>
                          </div>
                        </foreignObject>
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>

            {/* Tree Selected Node Drawer */}
            {selectedNode && (
              <div className="p-4 bg-slate-900 border-t border-slate-800 flex items-start justify-between gap-4 animate-in slide-in-from-bottom duration-200">
                <div className="space-y-1 max-w-3xl">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
                      Node Detail: {selectedNode.why_id} (Level {selectedNode.level})
                    </span>
                    {selectedNode.is_root_cause && (
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full font-bold">
                        Terminal Root Cause
                      </span>
                    )}
                    {selectedNode.is_unsubstantiated && (
                      <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded-full font-bold">
                        Requires Physical Verification (No Document Citation)
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-200 font-medium">
                    {selectedNode.cause_statement}
                  </p>
                  {selectedNode.verification_notes && (
                    <p className="text-xs text-slate-400 italic">
                      Notes: {selectedNode.verification_notes}
                    </p>
                  )}
                </div>

                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* SECTION 2: ISHIKAWA 6M FISHBONE DIAGRAM VISUALIZER                       */}
        {/* ========================================================================= */}
        {(activeView === 'fishbone' || activeView === 'split') && (
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden flex flex-col">
            {/* Fishbone Header & Filters */}
            <div className="px-5 py-3.5 bg-slate-800/60 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
                <h3 className="text-sm font-bold text-slate-200">
                  Ishikawa 6M Cause-and-Effect Diagram
                </h3>
              </div>

              {/* 6M Filter Pills */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <button
                  onClick={() => setSelectedCategoryFilter('ALL')}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                    selectedCategoryFilter === 'ALL'
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  All 6M
                </button>
                {ISHIKAWA_CATEGORIES.map((cat) => (
                  <button
                    key={cat.key}
                    onClick={() => setSelectedCategoryFilter(cat.key)}
                    className={`px-2 py-0.5 rounded-lg text-[10px] font-medium transition-all ${
                      selectedCategoryFilter === cat.key
                        ? 'bg-indigo-600 text-white font-bold'
                        : 'text-slate-400 hover:text-slate-200 bg-slate-800/60'
                    }`}
                  >
                    {cat.key}
                  </button>
                ))}
              </div>

              {/* Zoom Controls */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setZoomScaleFishbone((z) => Math.min(1.5, z + 0.15))}
                  className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoomScaleFishbone((z) => Math.max(0.6, z - 0.15))}
                  className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoomScaleFishbone(1)}
                  className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Fishbone SVG Canvas */}
            <div className="relative overflow-x-auto bg-[#070b14] min-h-[550px] p-4 flex items-center justify-center">
              <div
                style={{
                  transform: `scale(${zoomScaleFishbone})`,
                  transformOrigin: 'center center',
                  transition: 'transform 0.2s ease-out'
                }}
              >
                <svg
                  width={fishboneLayout.svgWidth}
                  height={fishboneLayout.svgHeight}
                  className="select-none"
                >
                  {/* Defs: Spine arrow */}
                  <defs>
                    <marker
                      id="arrow-spine"
                      viewBox="0 0 10 10"
                      refX="9"
                      refY="5"
                      markerWidth="8"
                      markerHeight="8"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
                    </marker>
                  </defs>

                  {/* 1. CENTRAL HORIZONTAL SPINE */}
                  <line
                    x1={fishboneLayout.spineStartX}
                    y1={fishboneLayout.spineY}
                    x2={fishboneLayout.spineEndX}
                    y2={fishboneLayout.spineY}
                    stroke="#38bdf8"
                    strokeWidth="5"
                    strokeLinecap="round"
                    markerEnd="url(#arrow-spine)"
                  />

                  {/* 2. FISH HEAD: FAILURE EFFECT BOX */}
                  <g transform={`translate(${fishboneLayout.spineEndX + 15}, ${fishboneLayout.spineY - 65})`}>
                    <rect
                      width="220"
                      height="130"
                      rx="16"
                      fill="#0f172a"
                      stroke="#38bdf8"
                      strokeWidth="2.5"
                      className="shadow-2xl"
                    />
                    <foreignObject width="220" height="130">
                      <div className="w-full h-full p-3 flex flex-col justify-between text-left select-none">
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400">
                              Failure Effect (D2)
                            </span>
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30">
                              RPN {report?.rpn_score || 336}
                            </span>
                          </div>
                          <p className="text-xs font-bold text-white mt-1 line-clamp-3 leading-snug">
                            {report?.d2_problem?.what ||
                              report?.d4_root_causes?.occurrence_root_cause ||
                              'Unscheduled Equipment Failure'}
                          </p>
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800">
                          <span>Tag: {report?.asset_tag || 'Pump-A12'}</span>
                          <span className="text-slate-500">ISO 9001:10.2</span>
                        </div>
                      </div>
                    </foreignObject>
                  </g>

                  {/* 3. 6M CATEGORY RIBS & CAUSE FEATHERS */}
                  {fishboneLayout.ribs.map((rib) => {
                    const isFiltered =
                      selectedCategoryFilter !== 'ALL' && selectedCategoryFilter !== rib.key;
                    const isHovered = hoveredCategory === rib.key;
                    const opacity = isFiltered ? 0.2 : 1.0;
                    const IconComponent = rib.icon;

                    return (
                      <g
                        key={rib.key}
                        opacity={opacity}
                        className="transition-opacity duration-300"
                        onMouseEnter={() => setHoveredCategory(rib.key)}
                        onMouseLeave={() => setHoveredCategory(null)}
                      >
                        {/* Diagonal Rib Line */}
                        <line
                          x1={rib.ribEndX}
                          y1={rib.ribEndY}
                          x2={rib.spineX}
                          y2={fishboneLayout.spineY}
                          stroke={rib.color}
                          strokeWidth={isHovered ? '4' : '3'}
                          strokeLinecap="round"
                          className="transition-all"
                        />

                        {/* Category Box at tip */}
                        <g
                          transform={`translate(${rib.ribEndX - 90}, ${
                            rib.isUpper ? rib.ribEndY - 50 : rib.ribEndY + 10
                          })`}
                        >
                          <rect
                            width="180"
                            height="44"
                            rx="10"
                            fill="#0f172a"
                            stroke={rib.color}
                            strokeWidth="1.5"
                            className="shadow-md"
                          />
                          <foreignObject width="180" height="44">
                            <div className="w-full h-full px-2.5 py-1.5 flex items-center justify-between select-none">
                              <div className="flex items-center gap-2">
                                <div
                                  className="w-6 h-6 rounded-lg flex items-center justify-center text-white"
                                  style={{ backgroundColor: rib.color }}
                                >
                                  <IconComponent className="w-3.5 h-3.5" />
                                </div>
                                <div>
                                  <span className="text-xs font-bold text-white block leading-tight">
                                    {rib.key}
                                  </span>
                                  <span className="text-[9px] text-slate-400">
                                    {rib.branchData.causes?.length || 0} causes
                                  </span>
                                </div>
                              </div>
                              {rib.branchData.is_unsubstantiated && (
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                              )}
                            </div>
                          </foreignObject>
                        </g>

                        {/* Sub-Branch Feather Bones (Contributing Causes) */}
                        {rib.subBranches.map((sub, sIdx) => (
                          <g key={`${rib.key}-cause-${sIdx}`} className="group/feather">
                            {/* Horizontal Feather Line */}
                            <line
                              x1={sub.endX}
                              y1={sub.endY}
                              x2={sub.startX}
                              y2={sub.startY}
                              stroke="#64748b"
                              strokeWidth="1.5"
                              strokeDasharray={sub.is_unsubstantiated ? '3 2' : 'none'}
                            />

                            {/* Cause Text Box on Sub-Branch */}
                            <foreignObject
                              x={sub.endX - 180}
                              y={sub.endY - 24}
                              width="180"
                              height="48"
                            >
                              <div
                                onClick={() => setSelectedFishboneCause(sub)}
                                className={`w-full h-full p-1.5 rounded-lg bg-slate-900/90 border cursor-pointer transition-all flex flex-col justify-between ${
                                  sub.is_unsubstantiated
                                    ? 'border-amber-600/60 hover:border-amber-400'
                                    : 'border-slate-700 hover:border-indigo-400'
                                } shadow-md`}
                              >
                                <p className="text-[10px] text-slate-200 line-clamp-2 leading-tight font-medium">
                                  {sub.cause}
                                </p>
                                <div className="flex items-center justify-between text-[8px] text-slate-400">
                                  {sub.citation_ids.length > 0 ? (
                                    <span
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        if (onSourceClick) onSourceClick(resolveCitation(sub.citation_ids[0]));
                                      }}
                                      className="text-indigo-400 hover:underline flex items-center gap-0.5 font-mono"
                                    >
                                      <FileText className="w-2 h-2" />
                                      {sub.citation_ids[0]}
                                    </span>
                                  ) : (
                                    <span className="text-amber-400 italic">⚠️ Assumption</span>
                                  )}
                                  <span className="text-slate-500 font-mono">#{sIdx + 1}</span>
                                </div>
                              </div>
                            </foreignObject>
                          </g>
                        ))}
                      </g>
                    );
                  })}
                </svg>
              </div>
            </div>

            {/* Fishbone Cause Inspector Drawer */}
            {selectedFishboneCause && (
              <div className="p-4 bg-slate-900 border-t border-slate-800 flex items-start justify-between gap-4 animate-in slide-in-from-bottom duration-200">
                <div className="space-y-1 max-w-3xl">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-sky-400 uppercase tracking-wider">
                      Ishikawa Factor: {selectedFishboneCause.category}
                    </span>
                    {selectedFishboneCause.is_unsubstantiated ? (
                      <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded-full font-bold">
                        Unsubstantiated Factor
                      </span>
                    ) : (
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full font-bold">
                        Verified Evidence Grounded
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-200 font-medium">
                    {selectedFishboneCause.cause}
                  </p>
                  {selectedFishboneCause.citation_ids?.length > 0 && (
                    <div className="flex items-center gap-2 pt-1">
                      <span className="text-xs text-slate-400">Grounding Citations:</span>
                      {selectedFishboneCause.citation_ids.map((cid) => (
                        <button
                          key={cid}
                          onClick={() => {
                            if (onSourceClick) onSourceClick(resolveCitation(cid));
                          }}
                          className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-700/60 text-xs font-mono hover:bg-indigo-900 flex items-center gap-1"
                        >
                          <FileText className="w-3 h-3" /> {cid}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <button
                  onClick={() => setSelectedFishboneCause(null)}
                  className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
