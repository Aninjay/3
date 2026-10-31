import React, { useState } from 'react';
import { api, setToken } from '../api/client';
import { ArrowRight, AlertCircle } from 'lucide-react';

export function CampusLogin({ onLoginSuccess }) {
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  async function handleLogin(e) {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);

    try {
      const res = await api.login({ login_id: loginId, password });
      setToken(res.data.token);
      onLoginSuccess(res.data.user);
    } catch (err) {
      setLoginError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoginLoading(false);
    }
  }

  return (
    <div className="campus-login-page">
      <div className="campus-bg-image" />
      <div className="campus-bg-overlay" />

      <div className="login-card-container">
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <img
            src="/assets/tapmi-logo.png"
            alt="TAPMI — Manipal Academy of Higher Education"
            style={{ display: 'block', width: 'min(100%, 280px)', height: 'auto', margin: '0 auto 14px', objectFit: 'contain' }}
          />
          <h2 className="h2" style={{ fontSize: '20px', marginBottom: '4px' }}>
            Cultural Committee
          </h2>
          <p className="text-muted" style={{ fontSize: '13px' }}>
            Convener · Co-convener · Volunteer · Core Committee
          </p>
        </div>

        <div style={{ borderBottom: '1px solid var(--color-border)', marginBottom: '20px' }} />

        {loginError && (
          <div className="banner banner-danger" style={{ marginBottom: '16px' }}>
            <AlertCircle size={16} />
            <span>{loginError}</span>
          </div>
        )}

        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">Shared Email or Login ID</label>
            <input
              type="text"
              className="form-input"
              placeholder="Shared email, student ID, or committee login ID"
              value={loginId}
              onChange={(e) => setLoginId(e.target.value)}
              required
            />
          </div>

          <p className="text-muted text-sm" style={{ marginTop: '-8px', marginBottom: '14px' }}>
            When an email is shared, your individual password opens your account.
          </p>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="Enter your account password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', height: '42px', marginTop: '8px' }}
            disabled={loginLoading}
          >
            {loginLoading ? 'Signing in...' : 'Sign In'}
            {!loginLoading && <ArrowRight size={16} />}
          </button>
        </form>
      </div>
    </div>
  );
}
