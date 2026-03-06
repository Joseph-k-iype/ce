import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

type Tab = 'users' | 'roles' | 'workspaces' | 'audit';

// ── API helpers ──────────────────────────────────────────────────────────────

const fetchUsers = () => api.get('/api/rbac/users').then(r => r.data);
const fetchRoles = () => api.get('/api/rbac/roles').then(r => r.data);
const fetchWorkspaces = () => api.get('/api/rbac/workspaces').then(r => r.data);
const fetchAudit = (offset: number) =>
  api.get('/api/rbac/audit-log', { params: { limit: 50, offset } }).then(r => r.data);

// ── Sub-components ───────────────────────────────────────────────────────────

function UsersTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['rbac-users'], queryFn: fetchUsers });
  const { data: rolesData } = useQuery({ queryKey: ['rbac-roles'], queryFn: fetchRoles });

  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('user');

  const createUser = useMutation({
    mutationFn: (payload: object) => api.post('/api/rbac/users', payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['rbac-users'] }); setNewUsername(''); setNewEmail(''); },
  });

  const updateUserRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.put(`/api/rbac/users/${userId}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rbac-users'] }),
  });

  const deactivateUser = useMutation({
    mutationFn: (userId: string) => api.delete(`/api/rbac/users/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rbac-users'] }),
  });

  const roleNames = rolesData?.roles?.map((r: any) => r.name) ?? ['admin', 'editor', 'user'];

  return (
    <div className="space-y-5">
      {/* Add user form */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Add User</h3>
        <div className="flex gap-3 flex-wrap">
          <input
            value={newUsername}
            onChange={e => setNewUsername(e.target.value)}
            placeholder="Username"
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
            onChange={e => setNewRole(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
          >
            {roleNames.map((r: string) => <option key={r} value={r}>{r}</option>)}
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

      {/* Users table */}
      {isLoading ? (
        <div className="text-sm text-gray-500">Loading users...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
                <th className="py-2 pr-4">Username</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Role</th>
                <th className="py-2 pr-4">Workspace</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(data?.users ?? []).map((user: any) => (
                <tr key={user.user_id} className="hover:bg-gray-50">
                  <td className="py-2 pr-4 font-medium">{user.username}</td>
                  <td className="py-2 pr-4 text-gray-500">{user.email || '—'}</td>
                  <td className="py-2 pr-4">
                    <select
                      value={user.role}
                      onChange={e => updateUserRole.mutate({ userId: user.user_id, role: e.target.value })}
                      className="border border-gray-200 rounded px-2 py-0.5 text-xs"
                    >
                      {roleNames.map((r: string) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td className="py-2 pr-4 text-gray-500 text-xs">{user.workspace_id || 'default'}</td>
                  <td className="py-2 pr-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {user.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td className="py-2">
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
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RolesTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['rbac-roles'], queryFn: fetchRoles });
  const [newRoleName, setNewRoleName] = useState('');
  const [newPermissions, setNewPermissions] = useState('');
  const [editingPerms, setEditingPerms] = useState<Record<string, string>>({});

  const createRole = useMutation({
    mutationFn: (payload: object) => api.post('/api/rbac/roles', payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['rbac-roles'] }); setNewRoleName(''); setNewPermissions(''); },
  });

  const updateRole = useMutation({
    mutationFn: ({ roleId, permissions }: { roleId: string; permissions: string[] }) =>
      api.put(`/api/rbac/roles/${roleId}`, { permissions }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rbac-roles'] }),
  });

  return (
    <div className="space-y-5">
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Create Custom Role</h3>
        <div className="flex gap-3 flex-wrap">
          <input
            value={newRoleName}
            onChange={e => setNewRoleName(e.target.value)}
            placeholder="Role name"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
          />
          <input
            value={newPermissions}
            onChange={e => setNewPermissions(e.target.value)}
            placeholder="Permissions (comma-separated)"
            className="border border-gray-300 rounded px-3 py-1.5 text-sm flex-1 min-w-[200px]"
          />
          <button
            onClick={() => createRole.mutate({
              name: newRoleName,
              permissions: newPermissions.split(',').map(s => s.trim()).filter(Boolean)
            })}
            disabled={!newRoleName || createRole.isPending}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
          >
            Create Role
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-sm text-gray-500">Loading roles...</div>
      ) : (
        <div className="space-y-3">
          {(data?.roles ?? []).map((role: any) => (
            <div key={role.role_id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-semibold text-gray-800">{role.name}</h4>
                <span className="text-xs text-gray-500">{role.role_id}</span>
              </div>
              <div className="flex items-center gap-3">
                <input
                  value={editingPerms[role.role_id] ?? role.permissions.join(', ')}
                  onChange={e => setEditingPerms(prev => ({ ...prev, [role.role_id]: e.target.value }))}
                  className="border border-gray-200 rounded px-2 py-1 text-xs flex-1"
                />
                <button
                  onClick={() => updateRole.mutate({
                    roleId: role.role_id,
                    permissions: (editingPerms[role.role_id] ?? role.permissions.join(', '))
                      .split(',').map((s: string) => s.trim()).filter(Boolean)
                  })}
                  className="px-3 py-1 bg-gray-700 text-white text-xs rounded hover:bg-gray-900"
                >
                  Save
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WorkspacesTab() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ['rbac-workspaces'], queryFn: fetchWorkspaces });
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newEnv, setNewEnv] = useState('dev');

  const createWs = useMutation({
    mutationFn: (payload: object) => api.post('/api/rbac/workspaces', payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['rbac-workspaces'] }); setNewName(''); setNewDesc(''); },
  });

  const ENV_COLORS: Record<string, string> = {
    dev: 'bg-green-100 text-green-700',
    uat: 'bg-yellow-100 text-yellow-700',
    prod: 'bg-red-100 text-red-700',
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
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
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
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {(data?.workspaces ?? []).map((ws: any) => (
            <div key={ws.workspace_id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-semibold text-gray-800">{ws.name}</h4>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${ENV_COLORS[ws.environment] ?? 'bg-gray-100 text-gray-600'}`}>
                  {ws.environment}
                </span>
              </div>
              <p className="text-xs text-gray-500 mb-2">{ws.description || 'No description'}</p>
              <p className="text-xs text-gray-400">{ws.member_count ?? 0} member(s)</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-200 text-left text-[10px] text-gray-400 uppercase tracking-wide">
                  <th className="py-2 pr-3">Time</th>
                  <th className="py-2 pr-3">User</th>
                  <th className="py-2 pr-3">Action</th>
                  <th className="py-2 pr-3">Resource</th>
                  <th className="py-2">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entries.map((e: any) => (
                  <tr key={e.id} className="hover:bg-gray-50">
                    <td className="py-1.5 pr-3 text-gray-400 whitespace-nowrap">
                      {new Date(e.timestamp).toLocaleString()}
                    </td>
                    <td className="py-1.5 pr-3">{e.user_id || '—'}</td>
                    <td className="py-1.5 pr-3 font-medium">{e.action}</td>
                    <td className="py-1.5 pr-3 text-gray-500">
                      {e.resource_type ? `${e.resource_type}:${e.resource_id}` : '—'}
                    </td>
                    <td className="py-1.5 text-gray-400 max-w-[200px] truncate">
                      {e.details ? JSON.stringify(e.details) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setOffset(Math.max(0, offset - 50))}
              disabled={offset === 0}
              className="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-xs text-gray-500">
              Showing {offset + 1}–{Math.min(offset + 50, total)} of {total}
            </span>
            <button
              onClick={() => setOffset(offset + 50)}
              disabled={offset + 50 >= total}
              className="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export function RBACAdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('users');

  const tabs: { id: Tab; label: string }[] = [
    { id: 'users', label: 'Users' },
    { id: 'roles', label: 'Roles' },
    { id: 'workspaces', label: 'Workspaces' },
    { id: 'audit', label: 'Audit Log' },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Access Control</h1>
        <p className="text-sm text-gray-500 mt-1">Manage users, roles, workspaces, and permissions</p>
      </div>

      {/* Tab nav */}
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

      {/* Tab content */}
      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'roles' && <RolesTab />}
      {activeTab === 'workspaces' && <WorkspacesTab />}
      {activeTab === 'audit' && <AuditTab />}
    </div>
  );
}
