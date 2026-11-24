import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BookOpen, CheckCircle2, Clock3 } from 'lucide-react';
import { modulesApi } from '../../api/services';
import type { Module } from '../../types';

type LessonResources = { article: string; practice: string; video: string };

const moduleResources: Record<string, LessonResources> = {
  'Data Structures & Scalable Algorithms': {
    article: 'https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/resources/lecture-videos/',
    practice: 'https://www.geeksforgeeks.org/dsa/data-structures-and-algorithms-online-quiz/',
    video: 'https://www.youtube.com/watch?v=CHhwJjR0mZA',
  },
  'Distributed Systems & REST Architecture': {
    article: 'https://www.ibm.com/think/topics/cap-theorem',
    practice: 'https://www.nbktechworld.com/topics/distributed-systems/cap-and-quorums',
    video: 'https://www.youtube.com/watch?v=_RbsFXWRZ10',
  },
};

const lessonResourceLabels: Record<string, { article: string; practice: string; video: string }> = {
  'Caching Strategies & Database Partitioning': {
    article: 'https://redis.io/docs/latest/develop/use/client-side-caching/',
    practice: 'https://shardcraft.dev/caching/recap-and-quiz/',
    video: 'https://www.youtube.com/watch?v=U3RkDLtS7uY',
  },
  'CAP Theorem & Consistency Models': {
    article: 'https://www.ibm.com/think/topics/cap-theorem',
    practice: 'https://www.nbktechworld.com/topics/distributed-systems/cap-and-quorums',
    video: 'https://www.youtube.com/watch?v=_RbsFXWRZ10',
  },
};

export function ModulesPage() {
  const [searchParams] = useSearchParams();
  const [modules, setModules] = useState<Module[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [savingLesson, setSavingLesson] = useState('');
  const selected = modules.find((module) => module.id === selectedId) ?? modules[0];
  const requestedModuleId = searchParams.get('moduleId');

  const loadModules = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await modulesApi.listModules();
      setModules(result ?? []);
      setSelectedId((current) => result?.find((module) => module.id === requestedModuleId)?.id || current || result?.[0]?.id || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Learning modules could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [requestedModuleId]);

  useEffect(() => { void loadModules(); }, [loadModules]);

  async function completeLesson(lessonId: string) {
    if (!selected) return;
    setSavingLesson(lessonId);
    setError('');
    try {
      const updated = await modulesApi.completeLesson(selected.id, lessonId);
      setModules((current) => current.map((module) => module.id === updated.id ? updated : module));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lesson progress could not be saved.');
    } finally {
      setSavingLesson('');
    }
  }

  async function startModule() {
    if (!selected) return;
    setError('');
    try {
      const updated = await modulesApi.enroll(selected.id);
      setModules((current) => current.map((module) => module.id === updated.id ? updated : module));
    } catch (err) { setError(err instanceof Error ? err.message : 'Module could not be started.'); }
  }

  return (
    <section className="space-y-6">
      <header>
        <p className="text-sm font-semibold text-violet-700">Learning</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-900">Learning Modules</h1>
        <p className="mt-2 text-slate-600">Continue published modules and track progress lesson by lesson.</p>
      </header>
      {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      {loading ? <div className="rounded-xl border bg-white p-8 text-slate-600">Loading your modules…</div> : !modules.length ? <div className="rounded-xl border border-dashed bg-white p-10 text-center"><BookOpen className="mx-auto h-8 w-8 text-slate-400" /><h2 className="mt-3 font-semibold text-slate-900">No modules available yet</h2><p className="mt-2 text-sm text-slate-600">Published learning modules for your profile will appear here.</p></div> : (
        <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
          <nav aria-label="Available learning modules" className="space-y-2">
            {modules.map((module) => <button key={module.id} type="button" onClick={() => setSelectedId(module.id)} className={`w-full rounded-xl border p-4 text-left ${selected?.id === module.id ? 'border-violet-500 bg-violet-50' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
              <span className="block font-semibold text-slate-900">{module.title}</span><span className="mt-1 block text-xs text-slate-600">{module.difficulty} · {module.lessons.length} lessons</span>
              <span className="mt-3 block h-1.5 overflow-hidden rounded bg-slate-200"><span className="block h-full rounded bg-violet-600" style={{ width: `${module.completion_percentage}%` }} /></span><span className="mt-1 block text-xs text-slate-600">{module.completion_percentage}% complete</span>
            </button>)}
          </nav>
          {selected && <article className="rounded-xl border border-slate-200 bg-white p-5 sm:p-7">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-medium text-violet-700">{selected.difficulty}</p><h2 className="mt-1 text-2xl font-bold text-slate-900">{selected.title}</h2></div><span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1.5 text-xs text-slate-700"><Clock3 className="h-3.5 w-3.5" />{selected.duration_minutes} min</span></div>
            <p className="mt-3 leading-6 text-slate-600">{selected.description}</p>
            {selected.progress_status === 'not_started' && <button type="button" onClick={() => void startModule()} className="mt-4 rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white">Start module</button>}
            <div className="mt-6 space-y-3">{selected.lessons.map((lesson, index) => {
              const completed = selected.completed_lesson_ids?.includes(lesson.id) ?? false;
              const resources = lessonResourceLabels[lesson.title] ?? moduleResources[selected.title];
              return <section key={lesson.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-medium uppercase tracking-wide text-slate-500">Lesson {index + 1} · {lesson.duration_minutes} min</p><h3 className="mt-1 font-semibold text-slate-900">{lesson.title}</h3></div>
                {completed ? <span className="inline-flex items-center gap-1 text-sm font-medium text-emerald-700"><CheckCircle2 className="h-4 w-4" />Completed</span> : <button type="button" disabled={!!savingLesson} onClick={() => void completeLesson(lesson.id)} className="rounded-lg border border-violet-700 px-3 py-2 text-sm font-semibold text-violet-800 hover:bg-violet-50 disabled:opacity-50">{savingLesson === lesson.id ? 'Saving…' : 'Mark complete'}</button>}</div>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{lesson.content}</p>
                {resources && <nav aria-label={`${lesson.title} learning resources`} className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-100 pt-3 text-sm">
                  <a href={resources.article} target="_blank" rel="noreferrer" className="font-medium text-violet-800 underline">Read article / course</a>
                  <a href={resources.practice} target="_blank" rel="noreferrer" className="font-medium text-violet-800 underline">Practice quiz</a>
                  <a href={resources.video} target="_blank" rel="noreferrer" className="font-medium text-violet-800 underline">Watch video</a>
                </nav>}
              </section>;
            })}</div>
          </article>}
        </div>
      )}
    </section>
  );
}
