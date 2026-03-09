import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

type Tab = 'users' | 'workspaces' | 'audit';

const PREDEFINED_ROLES = ['admin', 'editor', 'user'] as const;
type PredefinedRole = typeof PREDEFINED_ROLES[number];

const ROLE_BADGE: Record<string, string> = {
  admin: 'bg-red-100 text-red-700',
  editor: 'bg-blue-100 text-blue-700',
  user: 'bg-gray-100 text-gray-600',
};

// ── API helpers ──────────────────────────────────────────────────────────────

const fetchUsers = () => api.get('/rbac/users').then(r => r.data);
const fetchWorkspaces = () => api.get('/rbac/workspaces').then(r => r.data);
const fetchAudit = (offset: number) =>
  api.get('/rbac/audit-log', { params: { limit: 50, offset } }).then(r => r.data);
const fetchWorkspaceMembers = (wsId: string) =>
  api.get(`/rbac/workspaces/${wsId}/members`).then(r => r.data);
const fetchWorkspaceRules = (wsId: string) =>
  api.get(`/rbac/workspaces/${wsId}/rules`).then(r => r.data);

// ── UsersTab ─────────────────────────────────────────────────────────────────

function UsersTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['rbac-users'], queryFn: fetchUsers });

  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState<PredefinedRole>('user');

  const createUser = useMutation({
    mutationFn: (payload: object) => api.post('/rbac/users', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rbac-users'] });
      setNewUsername('');
      setNewEmail('');
    },
  });

  const updateUserRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.put(`/rbac/users/${userId}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rbac-users'] }),
  });

  const deactivateUser = useMutation({
    mutationFn: (userId: string) => api.delete(`/rbac/users/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rbac-users'] }),
  });

  return (
    <div className="space-y-5">
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Add User</h3>
        <div className="flex gap-3 flex-wrap">
          <input
            value={newUsername}
            onChange={e => setNewUsername(e.target.value)}
            placeholder="Employee ID / Username"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm flex-1 min-w-[140px]"
          />
          <input
            value={newEmail}
            onChange={e => setNewEmail(e.target.value)}
            placeholder="Email (optional)"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm flex-1 min-w-[140px]"
          />
          <select
            value={newRole}
            onChange={e => setNewRole(e.target.value as PredefinedRole)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            {PREDEFINED_ROLES.map(r => (
              <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
            ))}
          </select>
          <button
            onClick={() => createUser.mutate({ username: newUsername, email: newEmail, role: newRole })}
            disabled={!newUsername || createUser.isPending}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {createUser.isPending ? 'Adding...' : 'Add User'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-500">Loading users...</div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wide border-b border-gray-200">
                <th className="py-2.5 px-4">Username</th>
                <th className="py-2.5 px-4">Email</th>
                <th className="py-2.5 px-4">Role</th>
                <th className="py-2.5 px-4">Workspace</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(data?.users ?? []).map((user: any) => (
                <tr key={user.user_id} className="hover:bg-gray-50">
                  <td className="py-2.5 px-4 font-medium">{user.username}</td>
                  <td className="py-2.5 px-4 text-gray-500">{user.email || '—'}</td>
                  <td className="py-2.5 px-4">
                    <select
                      value={user.role}
                      onChange={e => updateUserRole.mutate({ userId: user.user_id, role: e.target.value })}
                      className="border border-gray-200 rounded px-2 py-0.5 text-xs bg-white"
                    >
                      {PREDEFINED_ROLES.map(r => (
                        <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2.5 px-4 text-gray-500 text-xs">{user.workspace_id || 'default'}</td>
                  <td className="py-2.5 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {user.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td className="py-2.5 px-4">
                    {user.is_active && (
                      <button
                        onClick={() => deactivateUser.mutate(user.user_id)}
                        className="text-xs text-red-500 hover:text-red-700 underline"
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {(data?.users ?? []).length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">No users yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Role reference */}
      <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
        <h4 className="text-xs font-semibold text-blue-700 mb-2 uppercase tracking-wide">Role Definitions</h4>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">admin</span>
            <span className="text-xs text-gray-600">Full access — manage rules, users, workspaces, data sources</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">editor</span>
            <span className="text-xs text-gray-600">Edit & approve rules, view policy overview and evaluator</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">user</span>
            <span className="text-xs text-gray-600">View policy overview, run evaluations in assigned workspaces</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── WorkspaceMembersPanel ─────────────────────────────────────────────────────

function WorkspaceMembersPanel({ workspaceId }: { workspaceId: string }) {
  const qc = useQueryClient();
  const { data: membersData, isLoading } = useQuery({
    queryKey: ['ws-members', workspaceId],
    queryFn: () => fetchWorkspaceMembers(workspaceId),
  });
  const { data: usersData } = useQuery({ queryKey: ['rbac-users'], queryFn: fetchUsers });

  const [selectedUserId, setSelectedUserId] = useState('');
  const [memberRole, setMemberRole] = useState<PredefinedRole>('user');

  const allUsers: any[] = usersData?.users ?? [];
  const members: any[] = membersData?.members ?? [];
  const memberIds = new Set(members.map((m: any) => m.user_id));
  const availableUsers = allUsers.filter(u => !memberIds.has(u.user_id) && u.is_active);

  const addMember = useMutation({
    mutationFn: () => api.post(`/rbac/workspaces/${workspaceId}/members`, {
      user_id: selectedUserId, role: memberRole,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ws-members', workspaceId] });
      setSelectedUserId('');
    },
  });

  const removeMember = useMutation({
    mutationFn: (userId: string) => api.delete(`/rbac/workspaces/${workspaceId}/members/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ws-members', workspaceId] }),
  });

  return (
    <div className="mt-3 space-y-3">
      <div className="flex gap-2 flex-wrap">
        <select
          value={selectedUserId}
          onChange={e => setSelectedUserId(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 text-xs flex-1 min-w-[140px] bg-white"
        >
          <option value="">Select user to add...</option>
          {availableUsers.map(u => (
            <option key={u.user_id} value={u.user_id}>{u.username}</option>
          ))}
        </select>
        <select
          value={memberRole}
          onChange={e => setMemberRole(e.target.value as PredefinedRole)}
          className="border border-gray-300 rounded px-2 py-1 text-xs bg-white"
        >
          {PREDEFINED_ROLES.map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <button
          onClick={() => addMember.mutate()}
          disabled={!selectedUserId || addMember.isPending}
          className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Add
        </button>
      </div>
      {isLoading ? (
        <p className="text-xs text-gray-400">Loading members...</p>
      ) : members.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No members yet</p>
      ) : (
        <div className="space-y-1">
          {members.map((m: any) => (
            <div key={m.user_id} className="flex items-center justify-between bg-gray-50 rounded px-3 py-1.5">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-800">{m.username}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${ROLE_BADGE[m.role] ?? 'bg-gray-100 text-gray-600'}`}>
                  {m.role}
                </span>
              </div>
              <button
                onClick={() => removeMember.mutate(m.user_id)}
                className="text-[10px] text-red-400 hover:text-red-600"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── WorkspaceRulesPanel ───────────────────────────────────────────────────────

function WorkspaceRulesPanel({ workspaceId }: { workspaceId: string }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['ws-rules', workspaceId],
    queryFn: () => fetchWorkspaceRules(workspaceId),
  });
  const [ruleInput, setRuleInput] = useState('');

  const assignRule = useMutation({
    mutationFn: (rule_id: string) => api.post(`/rbac/workspaces/${workspaceId}/rules`, { rule_id }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ws-rules', workspaceId] });
      setRuleInput('');
    },
  });

  const removeRule = useMutation({
    mutationFn: (ruleId: string) => api.delete(`/rbac/workspaces/${workspaceId}/rules/${encodeURIComponent(ruleId)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ws-rules', workspaceId] }),
  });

  const ruleIds: string[] = data?.rule_ids ?? [];

  return (
    <div className="mt-3 space-y-3">
      <div className="flex gap-2">
        <input
          value={ruleInput}
          onChange={e => setRuleInput(e.target.value)}
          placeholder="Rule ID (e.g. RULE_abc123...)"
          className="border border-gray-300 rounded px-2 py-1 text-xs flex-1 font-mono"
          onKeyDown={e => { if (e.key === 'Enter' && ruleInput.trim()) assignRule.mutate(ruleInput.trim()); }}
        />
        <button
          onClick={() => { if (ruleInput.trim()) assignRule.mutate(ruleInput.trim()); }}
          disabled={!ruleInput.trim() || assignRule.isPending}
          className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
        >
          Assign
        </button>
      </div>
      {isLoading ? (
        <p className="text-xs text-gray-400">Loading rules...</p>
      ) : ruleIds.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No rules assigned — users in this workspace can test all approved rules</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {ruleIds.map(id => (
            <span key={id} className="flex items-center gap-1 bg-green-50 border border-green-200 text-green-800 text-[10px] px-2 py-0.5 rounded font-mono">
              {id}
              <button onClick={() => removeRule.mutate(id)} className="text-green-400 hover:text-red-500 ml-0.5">✕</button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── WorkspacesTab ─────────────────────────────────────────────────────────────

function WorkspacesTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['rbac-workspaces'], queryFn: fetchWorkspaces });
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newEnv, setNewEnv] = useState('dev');
  const [expandedWs, setExpandedWs] = useState<string | null>(null);
  const [wsTab, setWsTab] = useState<Record<string, 'members' | 'rules'>>({});

  const createWs = useMutation({
    mutationFn: (payload: object) => api.post('/rbac/workspaces', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rbac-workspaces'] });
      setNewName('');
      setNewDesc('');
    },
  });

  const ENV_COLORS: Record<string, string> = {
    dev: 'bg-green-100 text-green-700 border-green-200',
    uat: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    prod: 'bg-red-100 text-red-700 border-red-200',
  };

  return (
    <div className="space-y-5">
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Create Workspace</h3>
        <div className="flex gap-3 flex-wrap">
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="Workspace name"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm min-w-[160px]"
          />
          <input
            value={newDesc}
            onChange={e => setNewDesc(e.target.value)}
            placeholder="Description (optional)"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm flex-1"
          />
          <select
            value={newEnv}
            onChange={e => setNewEnv(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white"
          >
            <option value="dev">dev</option>
            <option value="uat">uat</option>
            <option value="prod">prod</option>
          </select>
          <button
            onClick={() => createWs.mutate({ name: newName, description: newDesc, environment: newEnv })}
            disabled={!newName || createWs.isPending}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
          >
            Create
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-500">Loading workspaces...</div>
      ) : (
        <div className="space-y-3">
          {(data?.workspaces ?? []).map((ws: any) => {
            const isExpanded = expandedWs === ws.workspace_id;
            const activeTab = wsTab[ws.workspace_id] ?? 'members';
            return (
              <div key={ws.workspace_id} className="border border-gray-200 rounded-lg overflow-hidden">
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 select-none"
                  onClick={() => setExpandedWs(isExpanded ? null : ws.workspace_id)}
                >
                  <div className="flex items-center gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-semibold text-gray-800">{ws.name}</h4>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${ENV_COLORS[ws.environment] ?? 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                          {ws.environment}
                        </span>
                      </div>
                      {ws.description && <p className="text-xs text-gray-500 mt-0.5">{ws.description}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400">{ws.member_count ?? 0} member(s)</span>
                    <svg
                      className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      fill="none" stroke="currentColor" viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-gray-100 px-4 pb-4">
                    {/* Sub-tabs */}
                    <div className="flex gap-1 mt-3 mb-3">
                      {(['members', 'rules'] as const).map(t => (
                        <button
                          key={t}
                          onClick={() => setWsTab(prev => ({ ...prev, [ws.workspace_id]: t }))}
                          className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
                            activeTab === t
                              ? 'bg-gray-900 text-white'
                              : 'text-gray-500 hover:text-gray-700 border border-gray-200'
                          }`}
                        >
                          {t === 'members' ? 'Members' : 'Assigned Rules'}
                        </button>
                      ))}
                    </div>
                    {activeTab === 'members' && (
                      <WorkspaceMembersPanel workspaceId={ws.workspace_id} />
                    )}
                    {activeTab === 'rules' && (
                      <WorkspaceRulesPanel workspaceId={ws.workspace_id} />
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {(data?.workspaces ?? []).length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">No workspaces yet</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── AuditTab ──────────────────────────────────────────────────────────────────

function AuditTab() {
  const [offset, setOffset] = useState(0);
  const { data, isLoading } = useQuery({
    queryKey: ['rbac-audit', offset],
    queryFn: () => fetchAudit(offset),
  });

  const entries = data?.entries ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500">{total} total entries</p>
      {isLoading ? (
        <div className="text-sm text-gray-500">Loading audit log...</div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-xs">
              <thead className="bg-gray-50">
                <tr className="text-left text-[10px] text-gray-400 uppercase tracking-wide border-b border-gray-200">
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">User</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Resource</th>
                  <th className="py-2.5 px-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entries.map((e: any) => (
                  <tr key={e.id} className="hover:bg-gray-50">
                    <td className="py-2 px-3 text-gray-400 whitespace-nowrap">
                      {new Date(e.timestamp).toLocaleString()}
                    </td>
                    <td className="py-2 px-3">{e.user_id || '—'}</td>
                    <td className="py-2 px-3 font-medium">{e.action}</td>
                    <td className="py-2 px-3 text-gray-500">
                      {e.resource_type ? `${e.resource_type}:${e.resource_id}` : '—'}
                    </td>
                    <td className="py-2 px-3 text-gray-400 max-w-[200px] truncate">
                      {e.details ? JSON.stringify(e.details) : '—'}
                    </td>
                  </tr>
                ))}
                {entries.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-gray-400">No audit entries</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setOffset(Math.max(0, offset - 50))}
              disabled={offset === 0}
              className="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
            >Previous</button>
            <span className="text-xs text-gray-500">
              Showing {offset + 1}–{Math.min(offset + 50, total)} of {total}
            </span>
            <button
              onClick={() => setOffset(offset + 50)}
              disabled={offset + 50 >= total}
              className="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
            >Next</button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function RBACAdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('users');

  const tabs: { id: Tab; label: string }[] = [
    { id: 'users', label: 'Users' },
    { id: 'workspaces', label: 'Workspaces' },
    { id: 'audit', label: 'Audit Log' },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Access Control</h1>
        <p className="text-sm text-gray-500 mt-1">Manage users, roles, workspaces, and permissions</p>
      </div>

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'workspaces' && <WorkspacesTab />}
      {activeTab === 'audit' && <AuditTab />}
    </div>
  );
}
