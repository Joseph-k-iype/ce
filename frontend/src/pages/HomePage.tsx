import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getRulesOverviewTable } from '../services/rulesApi';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import gsap from 'gsap';

export function HomePage() {
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState<Record<string, string>>({});
  const tableRef = useRef<HTMLDivElement>(null);

  const queryParams: Record<string, string> = { ...filters };
  if (search) queryParams.search = search;

  const { data, isLoading, error } = useQuery({
    queryKey: ['rulesOverviewTable', queryParams],
    queryFn: () => getRulesOverviewTable(queryParams),
    staleTime: 30000,
  });

  useEffect(() => {
    if (tableRef.current && data) {
      gsap.fromTo(tableRef.current, { opacity: 0 }, { opacity: 1, duration: 0.4 });
    }
  }, [data]);

  const setFilter = (key: string, value: string) => {
    setFilters(prev => {
      if (!value) {
        const next = { ...prev };
        delete next[key];
        return next;
      }
      return { ...prev, [key]: value };
    });
  };

  return (
    <div>
      <div className="flex items-end justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Welcome to Privacy Policy Engine</h1>
        <div className="flex gap-6 text-right">
          <div>
            <div className="text-2xl font-bold text-gray-900">{data?.total_rules ?? '—'}</div>
            <div className="text-xs text-gray-500">Rules</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{data?.total_countries ?? '—'}</div>
            <div className="text-xs text-gray-500">Countries</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <span className="text-sm text-gray-500 font-medium">Filter by</span>
        <select
          className="text-sm border border-gray-300 rounded-full px-3 py-1.5 bg-white"
          value={filters.country || ''}
          onChange={(e) => setFilter('country', e.target.value)}
        >
          <option value="">Countries</option>
          {(data?.filters?.countries || []).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          className="text-sm border border-gray-300 rounded-full px-3 py-1.5 bg-white"
          value={filters.risk || ''}
          onChange={(e) => setFilter('risk', e.target.value)}
        >
          <option value="">Risk (H, M, L)</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          className="text-sm border border-gray-300 rounded-full px-3 py-1.5 bg-white"
          value={filters.duty || ''}
          onChange={(e) => setFilter('duty', e.target.value)}
        >
          <option value="">Duties</option>
          {(data?.filters?.duties || []).map(d => <option key={d} value={d}>{d}</option>)}
        </select>
        <div className="ml-auto flex items-center gap-2">
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 w-48"
          />
        </div>
      </div>

      {isLoading && <LoadingSpinner message="Loading rules..." />}
      {error && <div className="text-red-600 text-sm p-4 border border-red-200 rounded">Failed to load rules</div>}

      {data && (
        <div ref={tableRef} className="overflow-x-auto rounded-xl">
          <table className="w-full table-dark">
            <thead>
              <tr>
                <th>Sending Country</th>
                <th>Receiving Country</th>
                <th>Rule</th>
                <th>Rule Details</th>
                <th>Permission/Prohibition</th>
                <th>Duty</th>
              </tr>
            </thead>
            <tbody>
              {(data.rows || []).length === 0 && (
                <tr><td colSpan={6} className="text-center py-8 text-gray-400">No rules found</td></tr>
              )}
              {(data.rows || []).map((row, i) => (
                <tr key={`${row.rule_id}-${i}`}>
                  <td>{row.sending_country}</td>
                  <td>{row.receiving_country}</td>
                  <td className="font-medium">{row.rule_name}</td>
                  <td className="max-w-xs">{row.rule_details}</td>
                  <td>
                    <span className={row.permission_prohibition === 'Permission' ? 'badge-permission' : 'badge-prohibition'}>
                      {row.permission_prohibition}
                    </span>
                  </td>
                  <td>{row.duty}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
