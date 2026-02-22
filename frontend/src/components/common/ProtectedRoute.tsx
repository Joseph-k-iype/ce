import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore, type UserRole } from '../../stores/authStore';

interface Props {
  requiredRole?: UserRole;
}

export function ProtectedRoute({ requiredRole }: Props) {
  const { isAuthenticated, role } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && role !== requiredRole) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
