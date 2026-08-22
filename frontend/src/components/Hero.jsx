import { motion } from 'framer-motion';
import { ArrowRight, BrainCircuit, Activity, Database, Shield } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Hero() {
  return (
    <div className="flex flex-col lg:flex-row items-center justify-between min-h-[80vh] gap-12">
      <div className="flex-1 space-y-8">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-5xl lg:text-7xl font-bold tracking-tight leading-tight"
        >
          Self-Healing <br className="hidden lg:block" />
          <span className="text-primary">Knowledge graph</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
          className="text-lg text-textMuted max-w-xl"
        >
          A multi-agent retrieval system that retrieves, reasons, validates, and dynamically updates your distributed knowledge spaces.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
          className="flex flex-wrap gap-4"
        >
          <Link to="/query" className="bg-primary hover:bg-primaryHover text-white px-6 py-3 rounded-md font-medium flex items-center transition-colors">
            Start Querying <ArrowRight className="ml-2 w-4 h-4" />
          </Link>
          <Link to="/upload" className="bg-surface hover:bg-surfaceHover border border-border text-text px-6 py-3 rounded-md font-medium transition-colors">
            Manage Documents
          </Link>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, rotateY: 30, scale: 0.9 }}
        animate={{ opacity: 1, rotateY: 0, scale: 1 }}
        transition={{ duration: 1.2, ease: "easeOut" }}
        className="flex-1 relative w-full max-w-lg aspect-square"
        style={{ perspective: 1000 }}
      >
        <div className="absolute inset-0 grid grid-cols-2 gap-4">
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
            className="bg-surface border border-border rounded-xl p-6 flex flex-col justify-between shadow-2xl"
          >
            <Database className="w-8 h-8 text-blue-400 mb-4" />
            <h3 className="font-semibold text-lg">Vector Storage</h3>
            <p className="text-sm text-textMuted mt-2">Semantic search across millions of embedding vectors.</p>
          </motion.div>

          <motion.div
            animate={{ y: [0, 15, 0] }}
            transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
            className="bg-surface border border-border rounded-xl p-6 flex flex-col justify-between shadow-2xl translate-y-8"
          >
            <BrainCircuit className="w-8 h-8 text-purple-400 mb-4" />
            <h3 className="font-semibold text-lg">Hypergraph</h3>
            <p className="text-sm text-textMuted mt-2">Relational reasoning using Neo4j knowledge graphs.</p>
          </motion.div>

          <motion.div
            animate={{ y: [0, -15, 0] }}
            transition={{ repeat: Infinity, duration: 4.5, ease: "easeInOut" }}
            className="bg-surface border border-border rounded-xl p-6 flex flex-col justify-between shadow-2xl translate-y-4"
          >
            <Activity className="w-8 h-8 text-green-400 mb-4" />
            <h3 className="font-semibold text-lg">Immune System</h3>
            <p className="text-sm text-textMuted mt-2">Continuous background conflict resolution & self-healing.</p>
          </motion.div>

          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ repeat: Infinity, duration: 5.5, ease: "easeInOut" }}
            className="bg-surface border border-border rounded-xl p-6 flex flex-col justify-between shadow-2xl -translate-y-4"
          >
            <Shield className="w-8 h-8 text-indigo-400 mb-4" />
            <h3 className="font-semibold text-lg">Trust & Verify</h3>
            <p className="text-sm text-textMuted mt-2">Provides confidence scores and validates every answer.</p>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
