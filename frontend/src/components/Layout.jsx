import { Link, Outlet } from 'react-router-dom';
import { Database, Network, Shield } from 'lucide-react';

export default function Layout() {
  return (
    <div className="min-h-screen bg-background text-text flex flex-col font-sans">
      <header className="border-b border-border bg-surface/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <Network className="h-6 w-6 text-primary" />
              <Link to="/" className="text-xl font-bold tracking-tight">Industrial Mind OS</Link>
            </div>
            <nav className="hidden md:flex space-x-8">
              <Link to="/upload" className="text-sm text-textMuted hover:text-text transition-colors flex items-center space-x-1">
                <Database className="w-4 h-4" />
                <span>Knowledge Space</span>
              </Link>
              <div className="flex items-center space-x-1 text-sm text-green-500">
                <Shield className="w-4 h-4" />
                <span>Immune System Active</span>
              </div>
            </nav>
          </div>
        </div>
      </header>
      
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
