import React, { useState } from 'react';
import { Bot, Mail, Lock, ArrowRight, FileText, Database, Cpu, MessageSquare, GitBranch, Shield, Globe, Zap, Eye } from 'lucide-react';

const ANIM_STYLE = `
  @keyframes flowRight {
    0%   { left: -6px; opacity: 0; }
    20%  { opacity: 1; }
    80%  { opacity: 1; }
    100% { left: calc(100% + 6px); opacity: 0; }
  }
  .dot-flow  { position:absolute; top:50%; transform:translateY(-50%); width:5px; height:5px; border-radius:50%; animation: flowRight 2s ease-in-out infinite; }
  .dot-flow-2 { animation-delay: 0.67s; }
  .dot-flow-3 { animation-delay: 1.33s; }
`;

const STEPS = [
  { label: 'Documents', sub: 'PDF & Web',  icon: FileText,      color: '#475569', bg: '#f1f5f9', border: '#e2e8f0' },
  { label: 'Qdrant',    sub: 'Vector DB',  icon: Database,      color: '#1d4ed8', bg: '#dbeafe', border: '#93c5fd' },
  { label: 'NetworkX',  sub: 'Graph',      icon: GitBranch,     color: '#0369a1', bg: '#e0f2fe', border: '#7dd3fc' },
  { label: 'Groq LPU',  sub: 'Llama 3.3', icon: Cpu,           color: '#1e3a8a', bg: '#dbeafe', border: '#93c5fd' },
  { label: 'Answer',    sub: 'Cited',      icon: MessageSquare, color: '#065f46', bg: '#d1fae5', border: '#6ee7b7' },
];

const FEATURES = [
  { title: 'Knowledge Gate', desc: 'Restricts AI to specific asset manuals and work orders. Zero context bleed between users.', icon: Shield, accent: '#1d4ed8', accentBg: '#dbeafe', accentBorder: '#93c5fd', tag: 'Privacy' },
  { title: 'Asset Relationship Graph', desc: 'Explore knowledge as an interactive hierarchical graph.', icon: GitBranch, accent: '#0891b2', accentBg: '#cffafe', accentBorder: '#67e8f9', tag: 'Visual' },
  { title: 'Web Search', desc: 'Search OEM manuals, compliance standards, and external web sources.', icon: Globe, accent: '#d97706', accentBg: '#fef3c7', accentBorder: '#fcd34d', tag: 'Web Intel' },
  { title: 'Self-Healing Agents', desc: 'LangGraph retries with a new strategy if confidence is low.', icon: Zap, accent: '#059669', accentBg: '#d1fae5', accentBorder: '#6ee7b7', tag: 'Resilience' },
  { title: 'Full Explainability', desc: 'Every answer shows source docs, retrieval strategy, and confidence score.', icon: Eye, accent: '#1e3a8a', accentBg: '#eff6ff', accentBorder: '#bfdbfe', tag: 'Transparency' },
];

/* Full-page backdrop — blobs spread across whole viewport */
function FullBackdrop() {
  return (
    <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 }}>
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
        viewBox="0 0 1400 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="fb1"><feGaussianBlur stdDeviation="60" /></filter>
          <filter id="fb2"><feGaussianBlur stdDeviation="80" /></filter>
          <filter id="fb3"><feGaussianBlur stdDeviation="70" /></filter>
        </defs>
        <ellipse cx="160"  cy="200" rx="260" ry="230" fill="#bfdbfe" opacity="0.45" filter="url(#fb1)" />
        <ellipse cx="700"  cy="500" rx="300" ry="260" fill="#bae6fd" opacity="0.25" filter="url(#fb2)" />
        <ellipse cx="1250" cy="200" rx="260" ry="220" fill="#c7d2fe" opacity="0.30" filter="url(#fb3)" />
        <ellipse cx="1150" cy="760" rx="280" ry="240" fill="#dbeafe" opacity="0.35" filter="url(#fb1)" />
        <ellipse cx="300"  cy="780" rx="200" ry="180" fill="#e0f2fe" opacity="0.28" filter="url(#fb3)" />
      </svg>
      {/* Dot grid overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)',
        backgroundSize: '26px 26px', opacity: 0.22,
      }} />
    </div>
  );
}

function Pipeline() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
      {STEPS.map((step, i) => {
        const Icon = step.icon;
        const isLast = i === STEPS.length - 1;
        return (
          <React.Fragment key={step.label}>
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              flexShrink: 0, width: 100, padding: '14px 8px',
              background: 'rgba(255,255,255,0.85)', backdropFilter: 'blur(12px)',
              border: `1px solid ${step.border}`, borderRadius: 12,
              boxShadow: '0 2px 10px rgba(0,0,0,0.06)', transition: 'transform 0.2s',
            }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-4px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <div style={{ width: 38, height: 38, borderRadius: 9, background: step.bg, border: `1px solid ${step.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8 }}>
                <Icon style={{ width: 18, height: 18, color: step.color }} />
              </div>
              <span style={{ fontSize: 11.5, fontWeight: 700, color: '#1e293b', textAlign: 'center', lineHeight: 1.25 }}>{step.label}</span>
              <span style={{ fontSize: 9.5, color: '#94a3b8', textAlign: 'center', marginTop: 3 }}>{step.sub}</span>
            </div>
            {!isLast && (
              <div style={{ position: 'relative', width: 28, height: 24, flexShrink: 0 }}>
                <div style={{ position: 'absolute', top: '50%', left: 0, right: 6, height: 2, background: '#cbd5e1', transform: 'translateY(-50%)' }} />
                <svg style={{ position: 'absolute', right: 0, top: '50%', transform: 'translateY(-50%)' }} width="6" height="10" viewBox="0 0 6 10">
                  <path d="M0 0L6 5L0 10Z" fill="#94a3b8" />
                </svg>
                <div className="dot-flow" style={{ background: step.color, width: 6, height: 6 }} />
                <div className="dot-flow dot-flow-2" style={{ background: step.color, opacity: 0.55, width: 6, height: 6 }} />
                <div className="dot-flow dot-flow-3" style={{ background: step.color, opacity: 0.30, width: 6, height: 6 }} />
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function FeatureCard({ f, style = {} }) {
  const Icon = f.icon;
  return (
    <div style={{
      background: 'rgba(255,255,255,0.82)', backdropFilter: 'blur(16px)',
      border: `1px solid ${f.accentBorder}`, borderRadius: 12,
      padding: '14px 18px', boxShadow: '0 2px 10px rgba(0,0,0,0.06)',
      transition: 'box-shadow 0.2s, transform 0.2s', cursor: 'default',
      ...style,
    }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-3px)'; }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = '0 2px 10px rgba(0,0,0,0.06)'; e.currentTarget.style.transform = 'translateY(0)'; }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: f.accentBg, border: `1px solid ${f.accentBorder}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon style={{ width: 16, height: 16, color: f.accent }} />
        </div>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#1e293b', lineHeight: 1.2 }}>{f.title}</span>
        <span style={{ marginLeft: 'auto', fontSize: 10, fontWeight: 600, color: f.accent, background: f.accentBg, border: `1px solid ${f.accentBorder}`, borderRadius: 5, padding: '2px 8px', whiteSpace: 'nowrap', flexShrink: 0 }}>{f.tag}</span>
      </div>
      <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.5 }}>{f.desc}</div>
    </div>
  );
}

function FeatureBento() {
  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 10, marginBottom: 10 }}>
        <FeatureCard f={FEATURES[0]} />
        <FeatureCard f={FEATURES[1]} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '0.8fr 1.2fr', gap: 10, marginBottom: 10 }}>
        <FeatureCard f={FEATURES[2]} />
        <FeatureCard f={FEATURES[3]} />
      </div>
      <FeatureCard f={FEATURES[4]} />
    </div>
  );
}

export default function Login({ onLogin, onNavigateRegister }) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const fd = new URLSearchParams();
      fd.append('username', email); fd.append('password', password);
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: fd,
      });
      if (!res.ok) throw new Error('Invalid credentials. Please try again.');
      const data = await res.json();
      localStorage.setItem('imos_token', data.access_token);
      onLogin(data.access_token);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', width: '100%', fontFamily: 'Inter, system-ui, sans-serif', overflow: 'hidden', background: '#f8fafc', position: 'relative' }}>
      <style>{ANIM_STYLE}</style>

      {/* ── Full-page blurred backdrop ── */}
      <FullBackdrop />

      {/* ── Left: Info panel (65%) ── */}
      <div style={{ width: '65%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 60px', position: 'relative', zIndex: 1 }}
        className="hidden lg:flex">
        <div style={{ width: '100%', maxWidth: 640 }}>
          {/* Header */}
          <div style={{ marginBottom: 24 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: '#1d4ed8', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>
              How it works
            </p>
            <h1 style={{ fontSize: 32, fontWeight: 700, color: '#0f172a', lineHeight: 1.3, marginBottom: 10 }}>
              Unified Asset Brain
            </h1>
            <p style={{ fontSize: 14.5, color: '#64748b', lineHeight: 1.6, maxWidth: 580 }}>
              Private, multi-agent RAG — documents embedded locally, retrieved by hybrid search, and synthesized with full source citations across isolated user contexts.
            </p>
          </div>

          {/* Pipeline */}
          <Pipeline />

          {/* Divider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '20px 0 16px' }}>
            <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
            <span style={{ fontSize: 10.5, fontWeight: 700, color: '#94a3b8', letterSpacing: '0.1em' }}>KEY FEATURES</span>
            <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
          </div>

          {/* Bento */}
          <FeatureBento />
        </div>
      </div>

      {/* ── Right: Form card (35%) ── */}
      <div style={{ width: '35%', display: 'flex', alignItems: 'center', justifyContent: 'flex-start', padding: '32px 40px 32px 0', position: 'relative', zIndex: 1 }}
        className="w-full lg:w-[35%]">
        {/* Form card */}
        <div style={{
          width: '100%', maxWidth: 360,
          background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(24px)',
          border: '1px solid rgba(226,232,240,0.8)', borderRadius: 16,
          boxShadow: '0 12px 50px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.06)',
          padding: '36px 32px',
        }}>

          {/* Brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
            <div style={{ width: 40, height: 40, background: '#1d4ed8', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Bot style={{ width: 20, height: 20, color: '#fff' }} />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', lineHeight: 1.2 }}>Industrial Mind OS</div>
              <div style={{ fontSize: 11.5, color: '#94a3b8' }}>Unified Asset Brain</div>
            </div>
          </div>

          <div style={{ marginBottom: 24 }}>
            <h2 style={{ fontSize: 22, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>Sign in</h2>
            <p style={{ fontSize: 14, color: '#64748b' }}>Enter your credentials to continue.</p>
          </div>

          {error && (
            <div style={{ marginBottom: 16, padding: '12px 14px', background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 13.5, borderRadius: 8 }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 6 }}>Email address</label>
              <div style={{ position: 'relative' }}>
                <Mail style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', width: 16, height: 16, color: '#9ca3af', pointerEvents: 'none' }} />
                <input type="text" required placeholder="you@company.com" value={email} onChange={e => setEmail(e.target.value)}
                  style={{ width: '100%', paddingLeft: 38, paddingRight: 12, paddingTop: 10, paddingBottom: 10, background: '#fff', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, color: '#1e293b', outline: 'none', boxSizing: 'border-box' }}
                  onFocus={e => { e.target.style.borderColor = '#1d4ed8'; e.target.style.boxShadow = '0 0 0 3px rgba(29,78,216,0.12)'; }}
                  onBlur={e => { e.target.style.borderColor = '#d1d5db'; e.target.style.boxShadow = 'none'; }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 6 }}>Password</label>
              <div style={{ position: 'relative' }}>
                <Lock style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', width: 16, height: 16, color: '#9ca3af', pointerEvents: 'none' }} />
                <input type="password" required placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)}
                  style={{ width: '100%', paddingLeft: 38, paddingRight: 12, paddingTop: 10, paddingBottom: 10, background: '#fff', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, color: '#1e293b', outline: 'none', boxSizing: 'border-box' }}
                  onFocus={e => { e.target.style.borderColor = '#1d4ed8'; e.target.style.boxShadow = '0 0 0 3px rgba(29,78,216,0.12)'; }}
                  onBlur={e => { e.target.style.borderColor = '#d1d5db'; e.target.style.boxShadow = 'none'; }}
                />
              </div>
            </div>

            <button type="button" onClick={handleSubmit} disabled={loading}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', padding: '10px 18px', background: '#1d4ed8', color: '#fff', fontSize: 14.5, fontWeight: 600, borderRadius: 8, border: 'none', cursor: loading ? 'not-allowed' : 'pointer', transition: 'background 0.15s', opacity: loading ? 0.7 : 1, marginTop: 4 }}
              onMouseEnter={e => { if (!loading) e.currentTarget.style.background = '#1e40af'; }}
              onMouseLeave={e => { if (!loading) e.currentTarget.style.background = '#1d4ed8'; }}
            >
              {loading
                ? <><svg style={{ marginRight: 8, width: 16, height: 16, animation: 'spin 1s linear infinite' }} fill="none" viewBox="0 0 24 24"><circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Signing in...</>
                : <>Sign in <ArrowRight style={{ marginLeft: 6, width: 15, height: 15 }} /></>
              }
            </button>
          </div>

          <p style={{ marginTop: 20, fontSize: 14, color: '#64748b', textAlign: 'center' }}>
            Don't have an account?{' '}
            <button onClick={onNavigateRegister} style={{ fontWeight: 600, color: '#1d4ed8', background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: 14 }}>
              Create one
            </button>
          </p>

          <div style={{ marginTop: 24, paddingTop: 18, borderTop: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94a3b8' }}>
              <Shield style={{ width: 14, height: 14 }} />
              <span style={{ fontSize: 12 }}>Supabase Auth</span>
            </div>
            <div style={{ width: 1, height: 12, background: '#e2e8f0' }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94a3b8' }}>
              <Database style={{ width: 14, height: 14 }} />
              <span style={{ fontSize: 12 }}>Per-user isolation</span>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
