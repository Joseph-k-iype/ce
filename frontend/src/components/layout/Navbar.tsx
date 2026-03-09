import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../stores/authStore';
import api from '../../services/api';

const NAV_ITEMS = [
  { path: '/', label: 'Policy Overview', roles: ['admin', 'editor', 'user'] },
  { path: '/evaluator', label: 'Policy Evaluator', roles: ['admin', 'editor', 'user'] },
  { path: '/saved-policies', label: 'Saved Policies', roles: ['admin'] },
  { path: '/generator', label: 'Policy Generator', roles: ['admin'] },
  { path: '/editor', label: 'Policy Editor', roles: ['admin', 'editor'] },
  { path: '/dashboard', label: 'Dashboard', roles: ['admin'] },
  { path: '/data-sources', label: 'Data Sources', roles: ['admin'] },
  { path: '/access-control', label: 'Access Control', roles: ['admin'] },
];

const ENV_STYLES: Record<string, string> = {
  dev: 'bg-green-100 text-green-700 border-green-200',
  uat: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  prod: 'bg-red-100 text-red-700 border-red-200',
};

export function Navbar() {
  const location = useLocation();
  const { isAuthenticated, role, username, logout } = useAuthStore();

  const { data: envData } = useQuery({
    queryKey: ['environment'],
    queryFn: () => api.get('/env').then(r => r.data),
    staleTime: Infinity,
    enabled: isAuthenticated,
  });

  const env: string = envData?.env ?? 'dev';
  const envStyle = ENV_STYLES[env] ?? ENV_STYLES.dev;

  if (!isAuthenticated) return null;

  return (
    <nav className="w-full py-4 px-8">
      <div className="flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="border border-gray-300 rounded-full px-5 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-50 flex items-center gap-2 h-8">
            <span>Privacy Policy Engine</span>
          </div>
          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${envStyle}`}>
            {env}
          </span>
        </Link>

        <div className="flex items-center gap-1 bg-white rounded-full border border-gray-200 px-1 py-1">
          {NAV_ITEMS.filter(item => role && item.roles.includes(role)).map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${location.pathname === item.path
                ? 'bg-gray-900 text-white'
                : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">{username} ({role})</span>
          <button
            onClick={logout}
            className="text-xs text-gray-500 hover:text-gray-700 border border-gray-300 rounded-full px-3 py-1"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
