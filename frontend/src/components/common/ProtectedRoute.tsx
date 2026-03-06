import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore, type UserRole } from '../../stores/authStore';

interface Props {
  requiredRole?: UserRole | UserRole[];
}

export function ProtectedRoute({ requiredRole }: Props) {
  const { isAuthenticated, role } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole) {
    const allowed = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!role || !allowed.includes(role)) {
      return <Navigate to="/" replace />;
    }
  }

  return <Outlet />;
}
