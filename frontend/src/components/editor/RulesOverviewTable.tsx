import { useState, useEffect, useRef } from 'react';
import api from '../../services/api';
import { useAuthStore } from '../../stores/authStore';
import { RuleEditorModal } from './RuleEditorModal';
import { STATUS_STYLES } from '../../utils/ruleStatus';
import type { RuleTableRow } from '../../types/api';

interface RulesTableData {
  total_rules: number;
  total_countries: number;
  rows: RuleTableRow[];
  filters: Record<string, string[]>;
}

export function RulesOverviewTable() {
  const { role } = useAuthStore();
  const [data, setData] = useState<RulesTableData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [countryFilter, setCountryFilter] = useState('');
  const [actionLoading, setActionLoading] = useState<{ ruleId: string; action: string } | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  // Debounced search: only fires 300ms after the user stops typing
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => setDebouncedSearch(value), 300);
  };

  const fetchRules = () => {
    const params = new URLSearchParams();
    if (debouncedSearch) params.set('search', debouncedSearch);
    if (riskFilter) params.set('risk', riskFilter);
    if (countryFilter) params.set('country', countryFilter);

    setLoading(true);
    api.get<RulesTableData>(`/rules-overview-table?${params.toString()}`)
      .then(res => { setData(res.data); setError(null); })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchRules(); }, [debouncedSearch, riskFilter, countryFilter]);

  const handleStatusAction = async (ruleId: string, action: 'submit' | 'approve' | 'revert') => {
    setActionLoading({ ruleId, action });
    try {
      await api.post(`/admin/rules/${encodeURIComponent(ruleId)}/${action}`);
      fetchRules();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Action failed');
    } finally {
      setActionLoading(null);
    }
  };

  const priorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      high: 'bg-red-50 text-red-700 border-red-200',
      medium: 'bg-amber-50 text-amber-700 border-amber-200',
      low: 'bg-green-50 text-green-700 border-green-200',
    };
    return colors[priority?.toLowerCase()] || 'bg-gray-50 text-gray-600 border-gray-200';
  };

  const outcomeBadge = (outcome: string) =>
    outcome === 'Prohibition'
      ? 'bg-red-50 text-red-700 border-red-200'
      : 'bg-purple-50 text-purple-700 border-purple-200';

  const handleExportCsv = () => {
    if (!data?.rows?.length) return;
    const headers = ['Rule Name', 'Sending Country', 'Receiving Country', 'Type', 'Priority', 'Status', 'Duty'];
    const escape = (s?: string | null) => s ? `"${s.replace(/"/g, '""')}"` : '""';
    const csvContent = [
      headers.join(','),
      ...data.rows.map(row => [
        escape(row.rule_name), escape(row.sending_country), escape(row.receiving_country),
        escape(row.permission_prohibition), escape(row.priority), escape(row.status), escape(row.duty),
      ].join(',')),
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'rules_overview.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCsv}
            disabled={!data?.rows?.length}
            className="px-4 py-2 bg-white text-gray-700 border border-gray-300 text-sm font-medium rounded-lg shadow-sm hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Export to CSV
          </button>
          {role === 'admin' && (
            <button
              onClick={() => { setEditingRuleId(null); setIsModalOpen(true); }}
              className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg shadow hover:bg-purple-700 transition-colors"
            >
              Create New Rule
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search rules..."
          value={search}
          onChange={e => handleSearchChange(e.target.value)}
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
            onClick={() => { setSearch(''); setDebouncedSearch(''); setRiskFilter(''); setCountryFilter(''); }}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Clear
          </button>
        )}
      </div>

      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
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
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">Status</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(data?.rows || []).map((row) => {
                const status = row.status ?? 'live';
                const isLoadingThis = (action: string) =>
                  actionLoading?.ruleId === row.rule_id && actionLoading?.action === action;
                return (
                  <tr key={row.rule_id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                    <td
                      className="py-3 px-4 cursor-pointer"
                      onClick={() => { setEditingRuleId(row.rule_id); setIsModalOpen(true); }}
                    >
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
                    <td className="py-3 px-4">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs border ${STATUS_STYLES[status] ?? STATUS_STYLES.live}`}>
                        {status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {/* Admin: submit draft → in_progress */}
                        {role === 'admin' && status === 'draft' && (
                          <button
                            onClick={() => handleStatusAction(row.rule_id, 'submit')}
                            disabled={!!actionLoading}
                            className="px-2 py-0.5 text-xs rounded border border-yellow-300 text-yellow-700 bg-yellow-50 hover:bg-yellow-100 disabled:opacity-50"
                          >
                            {isLoadingThis('submit') ? '…' : 'Submit'}
                          </button>
                        )}
                        {/* Admin or Editor: approve → live */}
                        {(role === 'admin' || role === 'editor') && status !== 'live' && (
                          <button
                            onClick={() => handleStatusAction(row.rule_id, 'approve')}
                            disabled={!!actionLoading}
                            className="px-2 py-0.5 text-xs rounded border border-green-300 text-green-700 bg-green-50 hover:bg-green-100 disabled:opacity-50"
                          >
                            {isLoadingThis('approve') ? '…' : 'Approve'}
                          </button>
                        )}
                        {/* Admin only: revert live → draft */}
                        {role === 'admin' && status === 'live' && (
                          <button
                            onClick={() => handleStatusAction(row.rule_id, 'revert')}
                            disabled={!!actionLoading}
                            className="px-2 py-0.5 text-xs rounded border border-gray-300 text-gray-600 bg-gray-50 hover:bg-gray-100 disabled:opacity-50"
                          >
                            {isLoadingThis('revert') ? '…' : 'Revert'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {data?.rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400 text-sm">
                    No rules found matching your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <RuleEditorModal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setEditingRuleId(null); }}
        ruleId={editingRuleId}
        onSave={fetchRules}
      />
    </div>
  );
}
