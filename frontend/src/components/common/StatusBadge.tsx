const statusColors: Record<string, string> = {
  ALLOWED: 'bg-green-100 text-green-800 border-green-200',
  PROHIBITED: 'bg-red-100 text-red-800 border-red-200',
  REQUIRES_REVIEW: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  INSUFFICIENT_DATA: 'bg-gray-100 text-gray-800 border-gray-200',
  permission: 'bg-green-100 text-green-800 border-green-200',
  prohibition: 'bg-red-100 text-red-800 border-red-200',
};

export function StatusBadge({ status }: { status: string }) {
  const colors = statusColors[status] || 'bg-gray-100 text-gray-600 border-gray-200';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors}`}>
      {status}
    </span>
  );
}
