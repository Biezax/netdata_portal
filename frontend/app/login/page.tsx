'use client';

import { useState } from 'react';
import BrandMark from '../components/BrandMark';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (response.ok) {
        window.location.assign('/');
        return;
      }
      setError('Invalid credentials');
    } catch {
      setError('Login failed, please try again');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-netdata-bg">
      <form
        onSubmit={handleSubmit}
        className="w-80 space-y-4 rounded-2xl border border-netdata-border bg-netdata-bg-panel p-6"
      >
        <BrandMark size="lg" />
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
          required
          className="w-full rounded bg-netdata-dark p-2 text-netdata-text-primary outline-none focus:ring-1 focus:ring-netdata-accent"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full rounded bg-netdata-dark p-2 text-netdata-text-primary outline-none focus:ring-1 focus:ring-netdata-accent"
        />
        {error && <p className="text-sm text-netdata-critical">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-netdata-accent p-2 font-medium text-white disabled:opacity-50"
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
