import { useCallback, useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { adminApi } from '../../api/services';
import { useAuth } from '../../context/AuthContext';

export function AdminConsolePage() {
  const { user } = useAuth(); const [stats, setStats] = useState<Record<string, number> | null>(null); const [users, setUsers] = useState<Array<Record<string, unknown>>>([]); const [error, setError] = useState('');
  const loadUsers = useCallback(() => adminApi.listUsers().then(setUsers).catch(e => setError(e.message)), []);
  useEffect(() => { void adminApi.getStats().then(setStats).catch(e => setError(e.message)); if (user?.role === 'administrator') void loadUsers(); }, [user?.role, loadUsers]);
  if (!user || (user.role !== 'administrator' && user.role !== 'content_manager')) return <Navigate to="/dashboard" replace />;
  async function toggleUser(row: Record<string, unknown>) {
    const id = String(row.id);
    const isActive = Boolean(row.is_active);
    if (!window.confirm(`${isActive ? 'Deactivate' : 'Reactivate'} ${String(row.email)}?`)) return;
    setError('');
    try { await adminApi.setUserActive(id, !isActive); await loadUsers(); }
    catch (err) { setError(err instanceof Error ? err.message : 'User account status could not be updated.'); }
  }
  return <main className="space-y-6"><header><p className="text-sm font-semibold text-purple-700">Platform management</p><h1 className="mt-1 text-3xl font-bold text-slate-900">Admin console</h1><p className="mt-2 text-slate-600">Operational counts are read from the application database. User account controls are restricted to administrators.</p></header>{error && <div role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
    <section><h2 className="mb-3 text-lg font-semibold">Platform records</h2><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{stats ? Object.entries(stats).map(([key,value])=><article key={key} className="rounded-xl border bg-white p-5"><p className="text-sm capitalize text-slate-500">{key.replaceAll('_',' ')}</p><p className="mt-2 text-3xl font-bold text-slate-900">{value}</p></article>) : <p className="text-sm text-slate-500">Loading database counts…</p>}</div></section>
    <section className="grid gap-4 md:grid-cols-3"><div className="rounded-xl border bg-white p-5"><h2 className="text-lg font-semibold">Question content workflow</h2><p className="mt-1 text-sm text-slate-600">Review provenance, approve, publish, reject, archive, and revise question bank records.</p><Link to="/admin/questions" className="mt-4 inline-flex rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800">Manage questions</Link></div><div className="rounded-xl border bg-white p-5"><h2 className="text-lg font-semibold">Learning modules</h2><p className="mt-1 text-sm text-slate-600">Create module drafts, add lesson content, and publish to a selected industry.</p><Link to="/admin/modules" className="mt-4 inline-flex rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800">Manage modules</Link></div><div className="rounded-xl border bg-white p-5"><h2 className="text-lg font-semibold">Question taxonomy</h2><p className="mt-1 text-sm text-slate-600">Maintain the categories, roles and topic dimensions used by the question bank.</p><Link to="/admin/question-taxonomy" className="mt-4 inline-flex rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800">Manage taxonomy</Link></div></section>
    {user.role === 'administrator' && <section className="rounded-xl border bg-white p-5"><h2 className="text-lg font-semibold">Recent user accounts</h2>{users.length ? <div className="mt-3 divide-y">{users.map(row=><div key={String(row.id)} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"><span>{String(row.full_name)} · {String(row.email)}<span className="ml-2 text-slate-500">{String(row.role)} · {row.is_active ? 'active' : 'inactive'}</span></span>{String(row.id) !== user.id && <button type="button" onClick={() => void toggleUser(row)} className="rounded border px-3 py-1.5 text-xs font-semibold">{row.is_active ? 'Deactivate' : 'Reactivate'}</button>}</div>)}</div> : <p className="mt-3 text-sm text-slate-500">No user records loaded.</p>}</section>}
  </main>;
}
