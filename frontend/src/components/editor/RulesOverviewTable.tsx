import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import type { RuleTableRow } from '../../types/api';

interface RulesTableData {
  total_rules: number;
  total_countries: number;
  rows: RuleTableRow[];
  filters: Record<string, string[]>;
}

export function RulesOverviewTable() {
  const navigate = useNavigate();
  const [data, setData] = useState<RulesTableData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [countryFilter, setCountryFilter] = useState('');

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (riskFilter) params.set('risk', riskFilter);
    if (countryFilter) params.set('country', countryFilter);

    setLoading(true);
    api.get<RulesTableData>(`/rules-overview-table?${params.toString()}`)
      .then(res => {
        setData(res.data);
        setError(null);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [search, riskFilter, countryFilter]);

  const priorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      high: 'bg-red-50 text-red-700 border-red-200',
      medium: 'bg-amber-50 text-amber-700 border-amber-200',
      low: 'bg-green-50 text-green-700 border-green-200',
    };
    return colors[priority.toLowerCase()] || 'bg-gray-50 text-gray-600 border-gray-200';
  };

  const outcomeBadge = (outcome: string) => {
    return outcome === 'Prohibition'
      ? 'bg-red-50 text-red-700 border-red-200'
      : 'bg-purple-50 text-purple-700 border-purple-200';
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Rules Overview</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {data ? `${data.total_rules} rules across ${data.total_countries} countries` : 'Loading...'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search rules..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 max-w-xs rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
        />
        <select
          value={riskFilter}
          onChange={e => setRiskFilter(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
        >
          <option value="">All Risk Levels</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <input
          type="text"
          placeholder="Filter by country..."
          value={countryFilter}
          onChange={e => setCountryFilter(e.target.value)}
          className="max-w-[180px] rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
        />
        {(search || riskFilter || countryFilter) && (
          <button
            onClick={() => { setSearch(''); setRiskFilter(''); setCountryFilter(''); }}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Clear
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="border border-gray-200 rounded-xl overflow-hidden bg-white">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">Rule</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">Sending</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">Receiving</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">Type</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">Priority</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">Duty</th>
              </tr>
            </thead>
            <tbody>
              {(data?.rows || []).map((row) => (
                <tr
                  key={row.rule_id}
                  onClick={() => navigate(`/editor/${encodeURIComponent(row.rule_id)}`)}
                  className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="py-3 px-4">
                    <div className="font-medium text-gray-900 text-sm">{row.rule_name}</div>
                    <div className="text-xs text-gray-400 mt-0.5 line-clamp-1">{row.rule_details}</div>
                  </td>
                  <td className="py-3 px-4 text-gray-600">{row.sending_country}</td>
                  <td className="py-3 px-4 text-gray-600">{row.receiving_country}</td>
                  <td className="py-3 px-4">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs border ${outcomeBadge(row.permission_prohibition)}`}>
                      {row.permission_prohibition}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-block px-2 py-0.5 rounded-full text-xs border ${priorityBadge(row.priority)}`}>
                      {row.priority}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-500 text-xs max-w-[200px] truncate">{row.duty}</td>
                </tr>
              ))}
              {data?.rows.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">
                    No rules found matching your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
