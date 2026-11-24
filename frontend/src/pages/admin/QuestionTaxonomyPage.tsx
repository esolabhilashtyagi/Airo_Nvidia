import { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { industriesApi } from '../../api/candidates';
import { questionTaxonomyApi } from '../../api/services';
import { useAuth } from '../../context/AuthContext';
import type { Industry } from '../../types';
import { RequiredLabel } from '../../components/common/RequiredMark';

const kinds = [
  ['category', 'Industry category'], ['job_role', 'Job role'], ['skill', 'Skill'], ['subject', 'Subject'],
  ['topic', 'Topic'], ['company', 'Company'], ['experience_level', 'Experience level'], ['interview_round', 'Interview round'],
];

export function QuestionTaxonomyPage() {
  const { user } = useAuth();
  const [kind, setKind] = useState('category');
  const [name, setName] = useState('');
  const [industryId, setIndustryId] = useState('');
  const [parentId, setParentId] = useState('');
  const [search, setSearch] = useState('');
  const [rows, setRows] = useState<Array<Record<string, any>>>([]);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [subjects, setSubjects] = useState<Array<Record<string, any>>>([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [items, industryRows] = await Promise.all([questionTaxonomyApi.list(kind, search), industriesApi.listIndustries()]);
      setRows(items); setIndustries(industryRows);
      setIndustryId((value) => value || industryRows[0]?.id || '');
      if (kind === 'topic') setSubjects(await questionTaxonomyApi.list('subject'));
    } catch (err) { setError(err instanceof Error ? err.message : 'Taxonomy records could not be loaded.'); }
  }, [kind, search]);
  useEffect(() => { void load(); }, [load]);

  if (!user || (user.role !== 'administrator' && user.role !== 'content_manager')) return <Navigate to="/dashboard" replace />;

  async function create(event: React.FormEvent) {
    event.preventDefault(); setError('');
    try {
      await questionTaxonomyApi.create({ kind, name, industry_id: ['category','job_role','subject','interview_round'].includes(kind) ? industryId : undefined, parent_id: kind === 'topic' ? parentId : undefined });
      setName(''); await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Taxonomy record could not be saved.'); }
  }
  async function rename(row: Record<string, any>) {
    const nextName = window.prompt('Update taxonomy name', row.name ?? row.title);
    if (!nextName?.trim()) return;
    try { await questionTaxonomyApi.update(kind, row.id, { name: nextName.trim(), industry_id: row.industry_id, parent_id: row.subject_id }); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Taxonomy record could not be updated.'); }
  }
  async function deactivate(row: Record<string, any>) {
    try { await questionTaxonomyApi.deactivate(kind, row.id); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Taxonomy record could not be deactivated.'); }
  }
  async function reactivate(row: Record<string, any>) {
    try { await questionTaxonomyApi.setActive(kind, row.id, true); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Taxonomy record could not be reactivated.'); }
  }

  return <main className="space-y-6">
    <header><p className="text-sm font-semibold text-purple-700">Content management</p><h1 className="mt-1 text-3xl font-bold text-slate-900">Question taxonomy</h1><p className="mt-2 text-slate-600">Manage shared categories, roles, skills, subjects, topics, companies, experience levels and interview rounds. Deactivation keeps historical links intact.</p></header>
    {error && <div role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
    <div className="flex flex-wrap gap-3 rounded-xl border bg-white p-4"><label className="text-sm font-medium">Taxonomy type<select value={kind} onChange={event => { setKind(event.target.value); setParentId(''); }} className="mt-1 block rounded-lg border px-3 py-2">{kinds.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label className="flex-1 text-sm font-medium">Search<input value={search} onChange={event=>setSearch(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'){event.preventDefault();void load();}}} className="mt-1 block w-full rounded-lg border px-3 py-2" /></label><button type="button" onClick={()=>void load()} className="self-end rounded-lg border px-4 py-2 text-sm">Search</button></div>
    <form onSubmit={create} className="grid gap-3 rounded-xl border bg-white p-5 sm:grid-cols-2"><h2 className="sm:col-span-2 text-lg font-semibold">Add {kinds.find(([value])=>value===kind)?.[1]}</h2><label className="text-sm font-medium"><RequiredLabel>Name</RequiredLabel><input required minLength={2} value={name} onChange={event=>setName(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5" /></label>{['category','job_role','subject','interview_round'].includes(kind)&&<label className="text-sm font-medium"><RequiredLabel>Industry</RequiredLabel><select required value={industryId} onChange={event=>setIndustryId(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5">{industries.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}{kind==='topic'&&<label className="text-sm font-medium"><RequiredLabel>Parent subject</RequiredLabel><select required value={parentId} onChange={event=>setParentId(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5"><option value="">Select subject</option>{subjects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<button className="w-fit rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-800">Add record</button></form>
    <section className="overflow-hidden rounded-xl border bg-white"><h2 className="border-b p-4 text-lg font-semibold">Records ({rows.length})</h2>{rows.length ? <ul className="divide-y">{rows.map(row=><li key={row.id} className="flex flex-wrap items-center justify-between gap-3 p-4"><div><p className="font-medium">{row.name ?? row.title}</p><p className="text-xs text-slate-500">{row.is_active ? 'Active' : 'Inactive'}{row.industry_id ? ` · ${industries.find(item=>item.id===row.industry_id)?.name ?? 'Industry'}` : ''}</p></div><div className="flex gap-2"><button type="button" onClick={()=>void rename(row)} className="rounded border px-3 py-1.5 text-sm">Rename</button>{row.is_active ? <button type="button" onClick={()=>void deactivate(row)} className="rounded border border-rose-200 px-3 py-1.5 text-sm text-rose-700">Deactivate</button> : user.role === 'administrator' && <button type="button" onClick={()=>void reactivate(row)} className="rounded border border-emerald-200 px-3 py-1.5 text-sm text-emerald-800">Reactivate</button>}</div></li>)}</ul> : <p className="p-6 text-sm text-slate-500">No matching taxonomy records.</p>}</section>
  </main>;
}
