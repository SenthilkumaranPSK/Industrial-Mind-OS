import React, { useEffect, useState, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Share2, RefreshCw, Maximize2, X } from 'lucide-react';

export default function GraphVisualizer({ onClose }) {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const fgRef = useRef();

  useEffect(() => {
    fetchGraphData();
  }, []);

  const fetchGraphData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('imos_token');
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/graph/data`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setGraphData(data);
      }
    } catch (err) {
      console.error("Failed to fetch graph data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (node) => {
    // Center at node
    fgRef.current.centerAt(node.x, node.y, 1000);
    fgRef.current.zoom(2, 1000);
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 lg:p-12 animate-in fade-in zoom-in duration-300">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-md" onClick={onClose}></div>
      
      <div className="relative w-full h-full max-w-6xl bg-white rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col border border-white/20">
        
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-6 border-b border-slate-100 bg-white/80 backdrop-blur-md z-10">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center border border-indigo-100">
              <Share2 className="w-6 h-6 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Semantic Knowledge Graph</h2>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-widest">NetworkX Distributed Entities</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
             <button 
                onClick={fetchGraphData}
                className="p-3 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-indigo-600"
                title="Refresh Graph"
             >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
             </button>
             <button 
                onClick={() => fgRef.current.zoomToFit(400)}
                className="p-3 hover:bg-slate-100 rounded-xl transition-colors text-slate-400"
                title="Zoom to Fit"
             >
                <Maximize2 className="w-5 h-5" />
             </button>
             <div className="w-px h-6 bg-slate-200 mx-2"></div>
             <button 
                onClick={onClose}
                className="p-3 bg-slate-100 hover:bg-rose-50 rounded-xl transition-colors text-slate-600 hover:text-rose-600"
             >
                <X className="w-5 h-5" />
             </button>
          </div>
        </div>

        {/* Graph Container */}
        <div className="flex-1 relative bg-[#fcfcfd]">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center flex-col bg-white/50 backdrop-blur-sm z-20">
                <div className="w-16 h-16 border-4 border-indigo-500/20 border-t-indigo-600 rounded-full animate-spin mb-4"></div>
                <span className="text-slate-500 font-bold text-sm tracking-widest uppercase">Mapping Neural Paths...</span>
            </div>
          )}

          {!loading && graphData.nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center flex-col z-20">
                <Share2 className="w-16 h-16 text-slate-200 mb-4" />
                <span className="text-slate-400 font-medium">No semantic connections indexed yet.</span>
            </div>
          )}

          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            nodeLabel="name"
            nodeColor={() => '#4f46e5'}
            nodeRelSize={6}
            linkColor={() => '#e2e8f0'}
            linkWidth={1.5}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const label = node.name;
              const fontSize = 12/globalScale;
              ctx.font = `${fontSize}px Inter, sans-serif`;
              const textWidth = ctx.measureText(label).width;
              const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); 

              ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
              ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = '#1e293b';
              ctx.fillText(label, node.x, node.y);

              node.__bckgDimensions = bckgDimensions; // to use in nodePointerAreaPaint
            }}
            onNodeClick={handleNodeClick}
            cooldownTicks={100}
            d3AlphaDecay={0.01}
          />
        </div>

        {/* Footer Legend */}
        <div className="px-8 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">
            <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
                    <span>Entities</span>
                </div>
                <div className="flex items-center space-x-2">
                    <div className="w-4 h-0.5 bg-slate-300"></div>
                    <span>Relationships</span>
                </div>
            </div>
            <div>
                {graphData.nodes.length} Nodes • {graphData.links.length} Edges
            </div>
        </div>
      </div>
    </div>
  );
}
