import React, { useState } from 'react';
import { ShieldAlert, CheckCircle2, Link as LinkIcon, AlertTriangle, ChevronRight, ChevronDown, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const [isThoughtOpen, setIsThoughtOpen] = useState(false);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "flex w-full mb-6",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div className={clsx(
        "max-w-[80%] rounded-2xl p-5",
        isUser 
          ? "bg-primary text-white rounded-br-none" 
          : "bg-surface border border-border rounded-bl-none shadow-lg"
      )}>
        {!isUser && message.isTyping ? (
          <div className="flex items-center space-x-2 text-indigo-500 py-2">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-sm font-medium animate-pulse">Analyzing context & routing to agents...</span>
          </div>
        ) : (
          <>
            {!isUser && message.steps && message.steps.length > 0 && (
              <div className="mb-3 text-sm">
                <button 
                  onClick={() => setIsThoughtOpen(!isThoughtOpen)}
                  className="flex items-center space-x-2 text-slate-500 hover:text-slate-300 transition-colors font-medium bg-slate-800/50 px-3 py-1.5 rounded-full border border-slate-700/50"
                >
                  {isThoughtOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  <span className="text-xs font-semibold uppercase tracking-wider">Thought Process</span>
                </button>
                {isThoughtOpen && (
                  <div className="mt-3 p-3 bg-slate-900/50 rounded-lg border border-slate-800 text-slate-300 text-xs space-y-2 animate-in fade-in slide-in-from-top-1 duration-200">
                    {message.steps.map((step, idx) => (
                      <div key={idx} className="flex items-start">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 mr-2 flex-shrink-0"></div>
                        <span className="leading-relaxed">{step.step} - <span className="text-emerald-400 font-semibold">{step.status}</span></span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <p className="whitespace-pre-wrap text-sm md:text-base leading-relaxed">
              {message.content}
            </p>
          </>
        )}
        
        {!isUser && message.confidence && (
          <div className="mt-4 pt-4 border-t border-border flex flex-col gap-3">
            <div className="flex items-center space-x-2 text-xs font-medium">
              {message.confidence >= 0.9 ? (
                <CheckCircle2 className="w-4 h-4 text-green-400" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-yellow-400" />
              )}
              <span className={clsx(
                message.confidence >= 0.9 ? "text-green-400" : "text-yellow-400"
              )}>
                {(message.confidence * 100).toFixed(0)}% Confidence Score
              </span>
            </div>

            {message.immuneAction && (
              <div className="flex items-start space-x-2 bg-indigo-500/10 border border-indigo-500/20 p-2 rounded-md">
                <ShieldAlert className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
                <span className="text-xs text-indigo-300">
                  Immune System: {message.immuneAction}
                </span>
              </div>
            )}

            {message.sources && message.sources.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {message.sources.map((src, idx) => (
                  <span key={idx} className="flex items-center space-x-1 text-xs bg-surfaceHover px-2 py-1 rounded-md border border-border text-textMuted hover:text-text cursor-pointer transition-colors">
                    <LinkIcon className="w-3 h-3" />
                    <span>{src}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
