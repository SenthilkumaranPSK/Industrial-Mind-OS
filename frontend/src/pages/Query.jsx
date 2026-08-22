import { useState } from 'react';
import { Send, Settings2, ShieldCheck } from 'lucide-react';
import ChatMessage from '../components/ChatMessage';
import { motion } from 'framer-motion';

export default function Query() {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('Private');
  
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I am connected to your Industrial Mind OS distributed knowledge base. What would you like to know?',
      confidence: 1.0
    },
    {
      role: 'user',
      content: 'What is the current architecture standard based on the docs I uploaded yesterday?'
    },
    {
      role: 'assistant',
      content: 'Based on the company_policy_v2.pdf and architecture_diagram.txt, the new standard utilizes a multi-agent orchestrated layer over a Neo4j graph database for semantic reasoning.',
      confidence: 0.95,
      sources: ['architecture_diagram.txt', 'company_policy_v2.pdf'],
      immuneAction: 'Detected conflict with company_policy_v1.pdf. Marked v1 as deprecated and used v2.'
    }
  ]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    setMessages([...messages, { role: 'user', content: input }]);
    setInput('');
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'This is a mocked response from Industrial Mind OS showing the verified results from the hypergraph.',
        confidence: 0.88,
        sources: ['mock_data_source.pdf']
      }]);
    }, 1000);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-5xl mx-auto border border-border rounded-xl overflow-hidden bg-surface/30">
      {/* Header Bar */}
      <div className="flex justify-between items-center p-4 border-b border-border bg-surface">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-green-500" />
          <h2 className="font-semibold text-lg">Knowledge Query</h2>
        </div>
        
        <div className="flex items-center space-x-3 bg-surfaceHover px-3 py-1.5 rounded-md border border-border">
          <Settings2 className="w-4 h-4 text-textMuted" />
          <select 
            value={mode} 
            onChange={(e) => setMode(e.target.value)}
            className="bg-transparent text-sm focus:outline-none text-text cursor-pointer"
          >
            <option value="Private">Private Mode</option>
            <option value="Public">Public Mode</option>
            <option value="Hybrid">Hybrid Mode</option>
          </select>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg} />
        ))}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-surface border-t border-border">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Query your knowledge spaces collaboratively..."
            className="w-full bg-background border border-border rounded-lg pl-4 pr-12 py-4 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-text"
          />
          <button 
            type="submit" 
            disabled={!input.trim()}
            className="absolute right-2 p-2 bg-primary hover:bg-primaryHover text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
        <div className="text-center mt-2">
          <span className="text-xs text-textMuted">Industrial Mind OS uses hypergraph reasoning and can make mistakes. Verify critical information.</span>
        </div>
      </div>
    </div>
  );
}
