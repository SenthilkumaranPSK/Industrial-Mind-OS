import { UploadCloud, File, Trash2, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Upload() {
  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight mb-2">Knowledge Space</h2>
        <p className="text-textMuted text-lg">Upload and manage your custom knowledge base.</p>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="border-2 border-dashed border-border rounded-xl p-12 flex flex-col items-center justify-center bg-surface/30 hover:bg-surface/50 transition-colors cursor-pointer"
      >
        <div className="bg-primary/20 p-4 rounded-full mb-4">
          <UploadCloud className="w-8 h-8 text-primary" />
        </div>
        <h3 className="text-xl font-medium mb-1">Click to upload or drag & drop</h3>
        <p className="text-sm text-textMuted">PDF, TXT, DOCX (Max: 50MB)</p>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="space-y-4"
      >
        <h3 className="text-xl font-semibold">Your Documents</h3>
        <div className="bg-surface border border-border rounded-md overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-border hover:bg-surfaceHover transition-colors">
            <div className="flex items-center space-x-4">
              <File className="w-5 h-5 text-textMuted" />
              <div>
                <p className="font-medium text-sm">company_policy_v2.pdf</p>
                <div className="flex items-center space-x-2 mt-1">
                  <CheckCircle className="w-3 h-3 text-green-400" />
                  <span className="text-xs text-textMuted">Indexed & Embedded</span>
                </div>
              </div>
            </div>
            <button className="p-2 text-textMuted hover:text-red-400 transition-colors">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between p-4 hover:bg-surfaceHover transition-colors">
            <div className="flex items-center space-x-4">
              <File className="w-5 h-5 text-textMuted" />
              <div>
                <p className="font-medium text-sm">architecture_diagram.txt</p>
                <div className="flex items-center space-x-2 mt-1">
                  <CheckCircle className="w-3 h-3 text-green-400" />
                  <span className="text-xs text-textMuted">Indexed & Embedded</span>
                </div>
              </div>
            </div>
            <button className="p-2 text-textMuted hover:text-red-400 transition-colors">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
