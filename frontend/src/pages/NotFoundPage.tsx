import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-6xl font-bold text-gray-300">404</h1>
      <p className="text-gray-500 mt-2">Page not found</p>
      <Link to="/" className="mt-4 text-blue-600 hover:text-blue-800 text-sm">Back to home</Link>
    </div>
  );
}
