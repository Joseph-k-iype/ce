import { create } from 'zustand';

export type UserRole = 'admin' | 'user';

interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  role: UserRole | null;
  login: (username: string, password: string) => boolean;
  logout: () => void;
}

const CREDENTIALS: Record<string, { password: string; role: UserRole }> = {
  admin: { password: 'admin', role: 'admin' },
  user: { password: 'user', role: 'user' },
};

// Load persisted auth from localStorage
function loadAuth(): { isAuthenticated: boolean; username: string | null; role: UserRole | null } {
  try {
    const stored = localStorage.getItem('auth');
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        isAuthenticated: parsed.isAuthenticated || false,
        username: parsed.username || null,
        role: parsed.role || null,
      };
    }
  } catch { /* ignore */ }
  return { isAuthenticated: false, username: null, role: null };
}

const initial = loadAuth();

export const useAuthStore = create<AuthState>((set) => ({
  ...initial,

  login: (username: string, password: string) => {
    const cred = CREDENTIALS[username];
    if (cred && cred.password === password) {
      const state = { isAuthenticated: true, username, role: cred.role };
      localStorage.setItem('auth', JSON.stringify(state));
      set(state);
      return true;
    }
    return false;
  },

  logout: () => {
    localStorage.removeItem('auth');
    set({ isAuthenticated: false, username: null, role: null });
  },
}));
