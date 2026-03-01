import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

const NAV_ITEMS = [
  { path: '/', label: 'Policy Overview', roles: ['admin', 'user'] },
  { path: '/evaluator', label: 'Policy Evaluator', roles: ['admin', 'user'] },
  { path: '/saved-policies', label: 'Saved Policies', roles: ['admin'] },
  { path: '/generator', label: 'Policy Generator', roles: ['admin'] },
  { path: '/editor', label: 'Policy Editor', roles: ['admin'] },
  { path: '/dashboard', label: 'Dashboard', roles: ['admin'] },
  { path: '/data-sources', label: 'Data Sources', roles: ['admin'] },
];

export function Navbar() {
  const location = useLocation();
  const { isAuthenticated, role, username, logout } = useAuthStore();

  if (!isAuthenticated) return null;

  return (
    <nav className="w-full py-4 px-8">
      <div className="flex items-center justify-between">
        <Link to="/" className="flex items-center">
          <div className="border border-gray-300 rounded-full px-5 py-1.5 text-sm font-medium text-gray-800 hover:bg-gray-50 flex items-center gap-2 h-8">
            <span>Privacy Policy Engine</span>
          </div>
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
