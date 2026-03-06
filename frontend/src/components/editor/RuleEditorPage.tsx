import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useAuthStore } from '../../stores/authStore';
import { STATUS_STYLES } from '../../utils/ruleStatus';

interface LinkedEntity {
  target_type: string;
  target_name: string;
  target_id?: string;
}

interface RuleProperty {
  [key: string]: unknown;
}

interface SubgraphNode {
  node_type: string;
  properties: RuleProperty;
}

interface SubgraphData {
  rule_id: string;
  nodes: SubgraphNode[];
}

const ENTITY_ENDPOINTS: Record<string, { endpoint: string; nameField: string; nestedKey?: string }> = {
  Regulator:              { endpoint: '/regulators', nameField: 'name' },
  Authority:              { endpoint: '/authorities', nameField: 'name' },
  Process:                { endpoint: '/all-dropdown-values', nameField: 'name', nestedKey: 'processes_dict' },
  PurposeOfProcessing:    { endpoint: '/purpose-of-processing', nameField: 'name' },
  DataCategory:           { endpoint: '/data-categories', nameField: 'name' },
  SensitiveDataCategory:  { endpoint: '/sensitive-data-categories', nameField: 'name' },
  GDC:                    { endpoint: '/all-dropdown-values', nameField: 'name', nestedKey: 'gdc' },
  DataSubject:            { endpoint: '/all-dropdown-values', nameField: 'name', nestedKey: 'data_subjects' },
  LegalEntity:            { endpoint: '/legal-entities', nameField: 'name' },
  GlobalBusinessFunction: { endpoint: '/global-business-functions', nameField: 'name' },
};

const ENTITY_TYPES = Object.keys(ENTITY_ENDPOINTS);


export function RuleEditorPage() {
  const { ruleId } = useParams<{ ruleId: string }>();
  const navigate = useNavigate();
  const { role } = useAuthStore();

  const [subgraph, setSubgraph] = useState<SubgraphData | null>(null);
  const [links, setLinks] = useState<LinkedEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Link form
  const [linkType, setLinkType] = useState('Regulator');
  const [linkName, setLinkName] = useState('');
  const [linkLoading, setLinkLoading] = useState(false);
  const [entitySuggestions, setEntitySuggestions] = useState<string[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!ruleId) return;
    setLoading(true);
    try {
      const [subRes, linksRes] = await Promise.all([
        api.get<SubgraphData>(`/rules/${encodeURIComponent(ruleId)}/subgraph`),
        api.get<LinkedEntity[]>(`/rules/${encodeURIComponent(ruleId)}/links`),
      ]);
      setSubgraph(subRes.data);
      setLinks(linksRes.data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load rule');
    } finally {
      setLoading(false);
    }
  }, [ruleId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Fetch entity suggestions when linkType changes
  useEffect(() => {
    const config = ENTITY_ENDPOINTS[linkType];
    if (!config) { setEntitySuggestions([]); return; }
    let cancelled = false;
    setSuggestionsLoading(true);
    api.get(config.endpoint).then(res => {
      if (cancelled) return;
      let items = res.data;
      if (config.nestedKey && items && typeof items === 'object' && !Array.isArray(items)) {
        items = items[config.nestedKey] || [];
      }
      if (linkType === 'LegalEntity' && items && typeof items === 'object' && !Array.isArray(items)) {
        const all: string[] = [];
        Object.values(items).forEach((les) => { if (Array.isArray(les)) all.push(...les); });
        setEntitySuggestions([...new Set(all)].sort());
        setSuggestionsLoading(false);
        return;
      }
      if (Array.isArray(items)) {
        const names = items
          .map((item: string | Record<string, unknown>) =>
            typeof item === 'string' ? item : String(item[config.nameField] || ''))
          .filter(Boolean).sort();
        setEntitySuggestions([...new Set(names)]);
      } else {
        setEntitySuggestions([]);
      }
      setSuggestionsLoading(false);
    }).catch(() => { if (!cancelled) { setEntitySuggestions([]); setSuggestionsLoading(false); } });
    return () => { cancelled = true; };
  }, [linkType]);

  const handleAddLink = async () => {
    if (!ruleId || !linkName.trim()) return;
    setLinkLoading(true);
    try {
      await api.post(`/rules/${encodeURIComponent(ruleId)}/link`, {
        target_type: linkType,
        target_name: linkName.trim(),
      });
      setLinkName('');
      await fetchData();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || (err instanceof Error ? err.message : 'Failed'));
    } finally {
      setLinkLoading(false);
    }
  };

  const handleRemoveLink = async (entity: LinkedEntity) => {
    if (!ruleId) return;
    try {
      await api.delete(`/rules/${encodeURIComponent(ruleId)}/unlink`, {
        data: { target_type: entity.target_type, target_name: entity.target_name },
      });
      await fetchData();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || (err instanceof Error ? err.message : 'Failed'));
    }
  };

  const handleStatusAction = async (action: 'submit' | 'approve' | 'revert') => {
    if (!ruleId) return;
    setActionLoading(action);
    try {
      await api.post(`/admin/rules/${encodeURIComponent(ruleId)}/${action}`);
      await fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Action failed');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-8 h-8 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const ruleNode = subgraph?.nodes.find(n => n.node_type === 'Rule');
  const props = ruleNode?.properties ?? {};
  const status = (props.status as string) ?? 'live';

  return (
    <div className="h-full flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/editor')}
            className="text-sm text-gray-500 hover:text-gray-800 transition-colors"
          >
            &larr; Back to Rules
          </button>
          <span className="text-gray-300">|</span>
          <span className="text-sm font-medium text-gray-800">{props.name as string || ruleId}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[status] ?? STATUS_STYLES.live}`}>
            {status}
          </span>
        </div>

        {/* Workflow action buttons */}
        <div className="flex items-center gap-2">
          {role === 'admin' && status === 'draft' && (
            <button
              onClick={() => handleStatusAction('submit')}
              disabled={!!actionLoading}
              className="px-3 py-1.5 text-xs rounded-lg border border-yellow-300 text-yellow-700 bg-yellow-50 hover:bg-yellow-100 disabled:opacity-50"
            >
              {actionLoading === 'submit' ? 'Submitting…' : 'Submit for Review'}
            </button>
          )}
          {(role === 'admin' || role === 'editor') && status !== 'live' && (
            <button
              onClick={() => handleStatusAction('approve')}
              disabled={!!actionLoading}
              className="px-3 py-1.5 text-xs rounded-lg border border-green-400 text-green-700 bg-green-50 hover:bg-green-100 disabled:opacity-50 font-medium"
            >
              {actionLoading === 'approve' ? 'Approving…' : 'Approve & Publish'}
            </button>
          )}
          {role === 'admin' && status === 'live' && (
            <button
              onClick={() => handleStatusAction('revert')}
              disabled={!!actionLoading}
              className="px-3 py-1.5 text-xs rounded-lg border border-gray-300 text-gray-600 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              {actionLoading === 'revert' ? 'Reverting…' : 'Revert to Draft'}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-3 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 ml-3">&times;</button>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* Rule properties panel */}
        <div className="flex-1 overflow-y-auto p-6">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Rule Properties</h3>
          {ruleNode ? (
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <tbody className="divide-y divide-gray-100">
                  {Object.entries(props)
                    .filter(([k]) => !['name', 'rule_id'].includes(k))
                    .map(([key, val]) => (
                      <tr key={key} className="hover:bg-gray-50">
                        <td className="py-2.5 px-4 text-xs font-medium text-gray-500 w-1/3 capitalize">
                          {key.replace(/_/g, ' ')}
                        </td>
                        <td className="py-2.5 px-4 text-gray-800 text-xs font-mono break-words">
                          {val === null || val === undefined ? (
                            <span className="text-gray-300">—</span>
                          ) : typeof val === 'boolean' ? (
                            <span className={val ? 'text-green-600' : 'text-red-500'}>{String(val)}</span>
                          ) : (
                            String(val)
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No rule data found.</p>
          )}
        </div>

        {/* Linked entities sidebar */}
        <div className="w-80 border-l border-gray-200 bg-gray-50/50 overflow-y-auto flex flex-col">
          <div className="p-4 space-y-4 flex-1">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Linked Entities</h3>

            <div className="space-y-1.5">
              {links.length === 0 && (
                <p className="text-xs text-gray-400">No linked entities yet.</p>
              )}
              {links.map((link, i) => (
                <div key={i} className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-3 py-2">
                  <div>
                    <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">{link.target_type}</span>
                    <p className="text-sm text-gray-900 leading-tight">{link.target_name}</p>
                  </div>
                  {role === 'admin' && (
                    <button
                      onClick={() => handleRemoveLink(link)}
                      className="text-xs text-red-400 hover:text-red-600 ml-2"
                      title="Remove link"
                    >
                      &times;
                    </button>
                  )}
                </div>
              ))}
            </div>

            {/* Add link form — admin only */}
            {role === 'admin' && (
              <div className="border-t border-gray-200 pt-3 space-y-2">
                <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Add Link</h4>
                <select
                  value={linkType}
                  onChange={e => { setLinkType(e.target.value); setLinkName(''); }}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
                >
                  {ENTITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                {suggestionsLoading ? (
                  <div className="text-xs text-gray-400 py-1">Loading entities…</div>
                ) : (
                  <>
                    <input
                      type="text"
                      list={`entity-suggestions-${linkType}`}
                      value={linkName}
                      onChange={e => setLinkName(e.target.value)}
                      placeholder={`Search ${linkType}…`}
                      className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
                      onKeyDown={e => e.key === 'Enter' && handleAddLink()}
                    />
                    <datalist id={`entity-suggestions-${linkType}`}>
                      {entitySuggestions.map(name => <option key={name} value={name} />)}
                    </datalist>
                  </>
                )}
                <button
                  onClick={handleAddLink}
                  disabled={linkLoading || !linkName.trim()}
                  className="w-full bg-gray-900 text-white rounded-lg px-3 py-2 text-sm font-medium hover:bg-gray-800 disabled:opacity-50 transition-colors"
                >
                  {linkLoading ? 'Linking…' : 'Add Link'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
