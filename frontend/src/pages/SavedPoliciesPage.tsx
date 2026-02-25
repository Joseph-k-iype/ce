import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { listSavedSessions, deleteSavedSession, resumeWizardSession } from '../services/wizardApi';
import { useWizardStore } from '../stores/wizardStore';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import type { SavedSession } from '../types/wizard';

export function SavedPoliciesPage() {
  const [sessions, setSessions] = useState<SavedSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<'saved_at' | 'origin_country' | 'status'>('saved_at');
  const [sortAsc, setSortAsc] = useState(false);

  const navigate = useNavigate();
  const { loadFromSession } = useWizardStore();

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listSavedSessions();
      setSessions(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load saved policies');
    }
    setLoading(false);
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSessions();
  }, []);

  const handleResume = async (sessionId: string) => {
    try {
      const session = await resumeWizardSession(sessionId);
      loadFromSession(session as unknown as Record<string, unknown>);
      navigate('/generator');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume session');
    }
  };

  const handleDelete = async (sessionId: string) => {
    try {
      await deleteSavedSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      setDeleteConfirm(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session');
    }
  };

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const filteredSessions = sessions
    .filter(s => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        (s.origin_country || '').toLowerCase().includes(q) ||
        (s.receiving_countries || []).some(c => c.toLowerCase().includes(q)) ||
        (s.rule_text || '').toLowerCase().includes(q) ||
        s.session_id.toLowerCase().includes(q) ||
        (s.status || '').toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      let cmp = 0;
      if (sortField === 'saved_at') {
        cmp = (a.saved_at || '').localeCompare(b.saved_at || '');
      } else if (sortField === 'origin_country') {
        cmp = (a.origin_country || '').localeCompare(b.origin_country || '');
      } else if (sortField === 'status') {
        cmp = (a.status || '').localeCompare(b.status || '');
      }
      return sortAsc ? cmp : -cmp;
    });

  if (loading) return <LoadingSpinner message="Loading saved policies..." />;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Saved Policies</h1>
          <p className="text-sm text-gray-500 mt-1">Resume or manage your saved policy wizard sessions</p>
        </div>
        <button
          onClick={() => navigate('/generator')}
          className="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-800"
        >
          Create New Policy
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by country, rule text, or session ID..."
          className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-200"
        />
      </div>

      {filteredSessions.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-400 text-sm">
            {sessions.length === 0
              ? 'No saved policies yet. Create a new policy to get started.'
              : 'No policies match your search.'}
          </p>
          {sessions.length === 0 && (
            <button
              onClick={() => navigate('/generator')}
              className="mt-4 text-sm font-medium text-gray-700 hover:text-gray-900 underline"
            >
              Create New Policy
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Session
                </th>
                <th
                  className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                  onClick={() => handleSort('origin_country')}
                >
                  Route {sortField === 'origin_country' ? (sortAsc ? '↑' : '↓') : ''}
                </th>
                <th
                  className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                  onClick={() => handleSort('status')}
                >
                  Status {sortField === 'status' ? (sortAsc ? '↑' : '↓') : ''}
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Step
                </th>
                <th
                  className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                  onClick={() => handleSort('saved_at')}
                >
                  Saved {sortField === 'saved_at' ? (sortAsc ? '↑' : '↓') : ''}
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredSessions.map((session) => (
                <tr key={session.session_id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="text-xs font-mono text-gray-400">{session.session_id.slice(0, 8)}...</span>
                    {session.rule_text && (
                      <p className="text-xs text-gray-600 mt-0.5 truncate max-w-[200px]">{session.rule_text}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-800">
                      {session.origin_country || '—'}
                    </span>
                    {(session.receiving_countries || []).length > 0 && (
                      <span className="text-xs text-gray-400 ml-1">
                        → {session.receiving_countries.join(', ')}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${session.status === 'approved' ? 'bg-green-100 text-green-700' :
                        session.status === 'saved' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-600'
                      }`}>
                      {session.status || 'draft'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-500">Step {session.current_step || 1}/6</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-500">
                      {session.saved_at ? new Date(session.saved_at).toLocaleDateString() : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleResume(session.session_id)}
                        className="text-xs font-medium text-gray-700 hover:text-gray-900 border border-gray-300 rounded px-2.5 py-1 hover:bg-gray-50"
                      >
                        Resume
                      </button>
                      {deleteConfirm === session.session_id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleDelete(session.session_id)}
                            className="text-xs font-medium text-red-600 hover:text-red-700 border border-red-300 rounded px-2 py-1"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(null)}
                            className="text-xs text-gray-400 hover:text-gray-600 px-1"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirm(session.session_id)}
                          className="text-xs font-medium text-red-500 hover:text-red-600 border border-red-200 rounded px-2.5 py-1 hover:bg-red-50"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-400 text-center">
        {filteredSessions.length} of {sessions.length} policies shown
      </div>
    </div>
  );
}
