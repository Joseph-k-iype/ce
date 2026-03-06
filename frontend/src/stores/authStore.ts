import { create } from 'zustand';
import axios from 'axios';

export type UserRole = 'admin' | 'editor' | 'user';

interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  role: UserRole | null;
  token: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

// Load persisted auth from localStorage
function loadAuth(): { isAuthenticated: boolean; username: string | null; role: UserRole | null; token: string | null } {
  try {
    const stored = localStorage.getItem('auth');
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        isAuthenticated: parsed.isAuthenticated || false,
        username: parsed.username || null,
        role: parsed.role || null,
        token: parsed.token || null,
      };
    }
  } catch { /* ignore */ }
  return { isAuthenticated: false, username: null, role: null, token: null };
}

const initial = loadAuth();

export const useAuthStore = create<AuthState>((set) => ({
  ...initial,

  login: async (username: string, password: string) => {
    try {
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);

      const response = await axios.post('/api/auth/login', params, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      const { access_token, role, username: returnedUsername } = response.data;

      const state = {
        isAuthenticated: true,
        username: returnedUsername,
        role,
        token: access_token
      };

      localStorage.setItem('auth', JSON.stringify(state));
      set(state);
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem('auth');
    set({ isAuthenticated: false, username: null, role: null, token: null });
  },
}));
