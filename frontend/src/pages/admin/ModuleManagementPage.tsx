import { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { modulesApi, questionTaxonomyApi } from '../../api/services';
import { industriesApi } from '../../api/candidates';
import { useAuth } from '../../context/AuthContext';
import type { Industry, Module } from '../../types';
import { RequiredLabel } from '../../components/common/RequiredMark';

export function ModuleManagementPage() {
  const { user } = useAuth();
  const [modules, setModules] = useState<Module[]>([]);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [skills, setSkills] = useState<Array<{ id: string; name: string }>>([]);
  const [roleIds, setRoleIds] = useState<string[]>([]);
  const [skillIds, setSkillIds] = useState<string[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [industryId, setIndustryId] = useState('');
  const [selected, setSelected] = useState('');
  const [previewModuleId, setPreviewModuleId] = useState('');
  const [lessonTitle, setLessonTitle] = useState('');
  const [lessonContent, setLessonContent] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [rows, industryRows, skillRows] = await Promise.all([
        modulesApi.manage(), industriesApi.listIndustries(), questionTaxonomyApi.list('skill'),
      ]);
      setModules(rows);
      setIndustries(industryRows);
      setSkills(skillRows as Array<{ id: string; name: string }>);
      setIndustryId((current) => current || industryRows[0]?.id || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Modules could not be loaded.');
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  if (!user || (user.role !== 'administrator' && user.role !== 'content_manager')) return <Navigate to="/dashboard" replace />;

  async function create(event: React.FormEvent) {
    event.preventDefault(); setError('');
    try {
      await modulesApi.createDraft({ title, description, industry_id: industryId, job_role_ids: roleIds, skill_ids: skillIds });
      setTitle(''); setDescription(''); setRoleIds([]); setSkillIds([]); await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Draft could not be created.'); }
  }
  async function addLesson(event: React.FormEvent) {
    event.preventDefault(); setError('');
    try {
      const module = modules.find((row) => row.id === selected);
      await modulesApi.addLesson(selected, { title: lessonTitle, content: lessonContent, order_index: (module?.lessons.length ?? 0) + 1 });
      setLessonTitle(''); setLessonContent(''); setSelected(''); await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Lesson could not be saved.'); }
  }
  async function editModule(module: Module) {
    const nextTitle = window.prompt('Module title', module.title);
    if (!nextTitle?.trim()) return;
    const nextDescription = window.prompt('Module description', module.description);
    if (!nextDescription?.trim()) return;
    try { await modulesApi.updateManaged(module.id, { title: nextTitle.trim(), description: nextDescription.trim() }); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Module could not be updated.'); }
  }
  async function editLesson(module: Module, lesson: Module['lessons'][number]) {
    const nextTitle = window.prompt('Lesson title', lesson.title);
    if (!nextTitle?.trim()) return;
    const nextContent = window.prompt('Lesson content', lesson.content);
    if (!nextContent?.trim()) return;
    try { await modulesApi.updateLesson(module.id, lesson.id, { title: nextTitle.trim(), content: nextContent.trim(), duration_minutes: lesson.duration_minutes, order_index: lesson.order_index }); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Lesson could not be updated.'); }
  }
  async function moveLesson(module: Module, index: number, delta: -1 | 1) {
    const lessons = [...module.lessons].filter((lesson) => !lesson.is_archived).sort((a, b) => a.order_index - b.order_index);
    const targetIndex = index + delta;
    if (targetIndex < 0 || targetIndex >= lessons.length) return;
    const current = lessons[index]; const other = lessons[targetIndex];
    try {
      await modulesApi.updateLesson(module.id, current.id, { title: current.title, content: current.content, duration_minutes: current.duration_minutes, order_index: other.order_index });
      await modulesApi.updateLesson(module.id, other.id, { title: other.title, content: other.content, duration_minutes: other.duration_minutes, order_index: current.order_index });
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Lesson order could not be updated.'); }
  }
  async function archiveLesson(module: Module, lessonId: string) {
    try { await modulesApi.archiveLesson(module.id, lessonId); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Lesson could not be archived.'); }
  }
  async function publish(module: Module) {
    setError('');
    try { await modulesApi.updateManaged(module.id, { is_published: !module.is_published }); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Module could not be published. Add an active lesson first.'); }
  }
  async function archiveModule(module: Module) {
    try { await modulesApi.deleteManaged(module.id); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Module could not be archived.'); }
  }

  return <main className="space-y-6">
    <header><p className="text-sm font-semibold text-purple-700">Content management</p><h1 className="mt-1 text-3xl font-bold">Learning module administration</h1><p className="mt-2 text-slate-600">Create, edit, sequence, publish and archive learning modules while retaining candidate progress.</p></header>
    {error && <div role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
    <form onSubmit={create} className="grid gap-4 rounded-xl border bg-white p-5 md:grid-cols-2">
      <h2 className="text-lg font-semibold md:col-span-2">New module draft</h2>
      <label className="text-sm"><RequiredLabel>Industry</RequiredLabel><select required value={industryId} onChange={(event) => { setIndustryId(event.target.value); setRoleIds([]); }} className="mt-1 block w-full rounded border p-2.5">{industries.map((industry) => <option key={industry.id} value={industry.id}>{industry.name}</option>)}</select></label>
      <label className="text-sm"><RequiredLabel>Title</RequiredLabel><input required minLength={3} value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1 block w-full rounded border p-2.5" /></label>
      <label className="text-sm">Job roles<select multiple value={roleIds} onChange={(event) => setRoleIds(Array.from(event.target.selectedOptions, (option) => option.value))} className="mt-1 block w-full rounded border p-2.5">{industries.find((item) => item.id === industryId)?.job_roles.filter((role) => role.is_active).map((role) => <option key={role.id} value={role.id}>{role.title}</option>)}</select></label>
      <label className="text-sm">Skills<select multiple value={skillIds} onChange={(event) => setSkillIds(Array.from(event.target.selectedOptions, (option) => option.value))} className="mt-1 block w-full rounded border p-2.5">{skills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select></label>
      <label className="text-sm md:col-span-2"><RequiredLabel>Description</RequiredLabel><textarea required minLength={5} value={description} onChange={(event) => setDescription(event.target.value)} rows={3} className="mt-1 block w-full rounded border p-2.5" /></label>
      <button className="w-fit rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-violet-800">Create draft</button>
    </form>
    <section className="space-y-3"><h2 className="text-xl font-semibold">Modules</h2>{modules.map((module) => {
      const lessons = [...module.lessons].sort((a, b) => a.order_index - b.order_index);
      const activeLessons = lessons.filter((lesson) => !lesson.is_archived);
      const archivedLessons = lessons.filter((lesson) => lesson.is_archived);
      return <article key={module.id} className="rounded-xl border bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><span className={`rounded-full px-2 py-1 text-xs ${module.is_published ? 'bg-violet-50 text-violet-800' : 'bg-purple-50 text-purple-800'}`}>{module.is_published ? 'published' : 'draft'}</span><h3 className="mt-3 font-semibold">{module.title}</h3><p className="mt-1 text-sm text-slate-600">{module.description}</p><p className="mt-2 text-xs text-slate-500">{lessons.filter((lesson) => !lesson.is_archived).length} active lessons · {industries.find((item) => item.id === module.industry_id)?.name ?? 'Industry'} · {module.job_role_ids?.length ?? 0} roles · {module.skill_ids?.length ?? 0} skills</p></div>
          <div className="flex flex-wrap gap-2"><button type="button" onClick={() => void editModule(module)} className="rounded border px-3 py-2 text-sm">Edit</button><button type="button" onClick={() => setSelected(module.id)} className="rounded border px-3 py-2 text-sm">Add lesson</button><button type="button" onClick={() => setPreviewModuleId((current) => current === module.id ? '' : module.id)} className="rounded border px-3 py-2 text-sm">{previewModuleId === module.id ? 'Close preview' : 'Preview'}</button><button type="button" onClick={() => void publish(module)} disabled={!lessons.some((lesson) => !lesson.is_archived) && !module.is_published} className="rounded bg-violet-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-40">{module.is_published ? 'Unpublish' : 'Publish'}</button><button type="button" onClick={() => void archiveModule(module)} className="rounded border border-rose-200 px-3 py-2 text-sm text-rose-700">Archive</button></div></div>
        {lessons.length > 0 && <ol className="mt-4 divide-y rounded-lg border">{activeLessons.map((lesson, index) => <li key={lesson.id} className="flex flex-wrap items-center justify-between gap-3 p-3"><div><p className="text-sm font-medium">{lesson.order_index}. {lesson.title}</p><p className="text-xs text-slate-500">{lesson.duration_minutes} minutes</p></div><div className="flex gap-2"><button type="button" aria-label={`Move ${lesson.title} up`} disabled={index===0} onClick={() => void moveLesson(module, index, -1)} className="rounded border px-2 py-1 text-sm disabled:opacity-40">↑</button><button type="button" aria-label={`Move ${lesson.title} down`} disabled={index===activeLessons.length-1} onClick={() => void moveLesson(module, index, 1)} className="rounded border px-2 py-1 text-sm disabled:opacity-40">↓</button><button type="button" onClick={() => void editLesson(module, lesson)} className="rounded border px-2 py-1 text-sm">Edit</button><button type="button" onClick={() => void archiveLesson(module, lesson.id)} className="rounded border border-rose-200 px-2 py-1 text-sm text-rose-700">Archive lesson</button></div></li>)}{archivedLessons.map((lesson)=><li key={lesson.id} className="flex justify-between p-3 text-sm text-slate-500"><span>{lesson.order_index}. {lesson.title} · archived</span><span>{lesson.duration_minutes} minutes</span></li>)}</ol>}
        {previewModuleId === module.id && <section role="region" aria-label={`${module.title} preview`} className="mt-4 rounded-lg border border-violet-200 bg-violet-50/50 p-4"><h4 className="font-semibold">Candidate preview · {module.title}</h4><p className="mt-1 text-sm text-slate-600">{module.description}</p><ol className="mt-3 space-y-3">{activeLessons.map((lesson) => <li key={lesson.id} className="rounded-md bg-white p-3"><h5 className="font-medium">{lesson.order_index}. {lesson.title}</h5><p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{lesson.content}</p></li>)}</ol></section>}
        {selected === module.id && <form onSubmit={addLesson} className="mt-4 grid gap-3 rounded-lg bg-slate-50 p-4"><h4 className="font-medium">Add lesson</h4><label className="text-sm font-medium"> <RequiredLabel>Lesson title</RequiredLabel><input required minLength={3} placeholder="Lesson title" value={lessonTitle} onChange={(event) => setLessonTitle(event.target.value)} className="mt-1 w-full rounded border p-2.5" /></label><label className="text-sm font-medium"><RequiredLabel>Lesson content</RequiredLabel><textarea required minLength={5} placeholder="Lesson content" value={lessonContent} onChange={(event) => setLessonContent(event.target.value)} rows={4} className="mt-1 w-full rounded border p-2.5" /></label><div className="flex gap-2"><button className="rounded bg-violet-700 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-800">Save lesson</button><button type="button" onClick={() => setSelected('')} className="rounded border px-3 py-2 text-sm">Cancel</button></div></form>}
      </article>;
    })}</section>
  </main>;
}
