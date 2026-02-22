import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const success = login(username, password);
    if (success) {
      navigate('/');
    } else {
      setError('Invalid credentials');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-sm">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy Engine</h1>
        <p className="text-gray-500 text-sm mb-8">Sign in to continue</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError(''); }}
              className="w-full rounded-lg border border-gray-300 py-2.5 px-3 text-sm focus:outline-none focus:border-gray-500"
              placeholder="Enter username"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(''); }}
              className="w-full rounded-lg border border-gray-300 py-2.5 px-3 text-sm focus:outline-none focus:border-gray-500"
              placeholder="Enter password"
              required
            />
          </div>
          {error && <p className="text-red-600 text-xs">{error}</p>}
          <button type="submit" className="btn-red w-full py-2.5">
            Sign In
          </button>
          <p className="text-xs text-gray-400 text-center mt-4">
            admin/admin (full access) or user/user (read-only)
          </p>
        </form>
      </div>
    </div>
  );
}
