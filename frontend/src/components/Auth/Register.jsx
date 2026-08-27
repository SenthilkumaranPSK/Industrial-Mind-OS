import React, { useState } from 'react';
import { Mail, Lock, ArrowRight } from 'lucide-react';
import AuthShell, { inputStyle, iconStyle, focusInput, blurInput } from './AuthShell';

export default function Register({ onRegister, onNavigateLogin }) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/auth/register`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) {
        let msg = 'Failed to create account';
        try { const d = await res.json(); msg = d.detail || msg; } catch {}
        throw new Error(msg);
      }
      const data = await res.json();
      onRegister(data.email, password);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <AuthShell
      heading="Your Knowledge, Your Control"
      subheading="Private, multi-agent RAG — documents embedded locally, retrieved by hybrid search, and synthesized with full source citations across isolated contexts."
      formTitle="Create an account"
      formSubtitle="Set up your private knowledge workspace."
      error={error}
      footer={
        <p style={{ marginTop: 20, fontSize: 14, color: '#64748b', textAlign: 'center' }}>
          Already have an account?{' '}
          <button onClick={onNavigateLogin} style={{ fontWeight: 600, color: '#1d4ed8', background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: 14 }}>
            Sign in
          </button>
        </p>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 6 }}>Email address</label>
          <div style={{ position: 'relative' }}>
            <Mail style={iconStyle} />
            <input type="email" required placeholder="you@company.com" value={email} onChange={e => setEmail(e.target.value)}
              style={inputStyle} onFocus={focusInput} onBlur={blurInput} />
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 5 }}>Password</label>
          <div style={{ position: 'relative' }}>
            <Lock style={iconStyle} />
            <input type="password" required placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)}
              style={inputStyle} onFocus={focusInput} onBlur={blurInput} />
          </div>
        </div>

        <button type="button" onClick={handleSubmit} disabled={loading}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', padding: '10px 18px', background: '#1d4ed8', color: '#fff', fontSize: 14.5, fontWeight: 600, borderRadius: 8, border: 'none', cursor: loading ? 'not-allowed' : 'pointer', transition: 'background 0.15s', opacity: loading ? 0.7 : 1, marginTop: 4 }}
          onMouseEnter={e => { if (!loading) e.currentTarget.style.background = '#1e40af'; }}
          onMouseLeave={e => { if (!loading) e.currentTarget.style.background = '#1d4ed8'; }}
        >
          {loading
            ? <><svg style={{ marginRight: 8, width: 16, height: 16, animation: 'spin 1s linear infinite' }} fill="none" viewBox="0 0 24 24"><circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Creating account...</>
            : <>Create account <ArrowRight style={{ marginLeft: 6, width: 15, height: 15 }} /></>
          }
        </button>
      </div>
    </AuthShell>
  );
}
