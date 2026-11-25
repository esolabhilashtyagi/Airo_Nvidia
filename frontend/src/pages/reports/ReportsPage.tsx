import { useEffect, useState } from 'react';
import { Activity, Award, BookOpenCheck, ChartNoAxesCombined, ClipboardCheck, Target } from 'lucide-react';
import { dashboardApi } from '../../api/services';

type Analytics = {
  weekly_activity: Array<{ day: string; questions: number; minutes?: number | null }>;
  score_history: Array<{ date: string; timestamp?: string | null; score: number; type: string }>;
  topic_performance: Array<{ topic: string; proficiency?: number | null; total_questions: number }>;
  module_completion_percentage: number;
  total_practice_count: number;
};

function formatCompletedAt(timestamp?: string | null, legacyDate?: string) {
  const parsed = timestamp ? new Date(timestamp) : legacyDate ? new Date(legacyDate) : null;
  if (!parsed || Number.isNaN(parsed.getTime())) return legacyDate || 'Time unavailable';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(parsed);
}

function MetricCard({ icon: Icon, label, value, hint }: { icon: typeof Activity; label: string; value: string | number; hint: string }) {
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-900/[0.03]">
    <div className="flex items-start justify-between gap-4"><div><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value}</p></div><span className="grid h-11 w-11 place-items-center rounded-xl bg-violet-50 text-violet-700"><Icon className="h-5 w-5" /></span></div>
    <p className="mt-3 text-xs leading-5 text-slate-500">{hint}</p>
  </article>;
}

export function ReportsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { void dashboardApi.getAnalytics().then(setData).catch((e) => setError(e instanceof Error ? e.message : 'Reports could not be loaded.')); }, []);
  const maxDay = Math.max(1, ...(data?.weekly_activity.map((item) => item.questions) ?? []));

  return <main className="space-y-6">
    <header className="rounded-2xl border border-violet-100 bg-gradient-to-br from-white via-white to-violet-50/80 p-6 shadow-sm sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-violet-700">Your progress</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-3xl font-bold tracking-tight text-slate-950">Performance reports</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">A clear view of your practice activity, topic results, and completed evaluations.</p></div><span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600"><ChartNoAxesCombined className="h-4 w-4 text-violet-700" />Saved activity only</span></div>
    </header>
    {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    {!data && !error && <p className="rounded-xl border border-slate-200 bg-white p-6 text-slate-600">Loading your reports…</p>}
    {data && <>
      <section aria-label="Progress summary" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <MetricCard icon={ClipboardCheck} label="Practice responses" value={data.total_practice_count} hint="Answers saved across practice activities." />
        <MetricCard icon={BookOpenCheck} label="Learning progress" value={`${Math.round(data.module_completion_percentage)}%`} hint="Completion across your published learning modules." />
        <MetricCard icon={Award} label="Completed evaluations" value={data.score_history.length} hint="Validated assessment and interview scores recorded." />
      </section>
      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex items-start justify-between gap-3"><div><h2 className="font-semibold text-slate-950">Practice activity</h2><p className="mt-1 text-sm text-slate-500">Questions answered over the last seven days</p></div><span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">{data.weekly_activity.reduce((sum, item) => sum + item.questions, 0)} total</span></div>
          {data.weekly_activity.length ? <div className="mt-6 space-y-4">{data.weekly_activity.map((day, index) => <div key={`${day.day}-${index}`} className="grid grid-cols-[2.5rem_minmax(0,1fr)_2rem] items-center gap-3 text-sm"><span className="text-slate-600">{day.day}</span><div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-violet-600 transition-all" style={{ width: `${day.questions ? Math.max(4, (day.questions / maxDay) * 100) : 0}%` }} /></div><span className="text-right font-medium tabular-nums text-slate-700">{day.questions}</span></div>)}</div> : <p className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No practice activity has been recorded yet.</p>}
        </article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex items-start justify-between gap-3"><div><h2 className="font-semibold text-slate-950">Topic performance</h2><p className="mt-1 text-sm text-slate-500">Results from evaluated answers</p></div><Target className="h-5 w-5 text-violet-700" /></div>
          {data.topic_performance.length ? <div className="mt-4 divide-y divide-slate-100">{data.topic_performance.map((item) => <div key={item.topic} className="py-3.5"><div className="flex items-baseline justify-between gap-3"><p className="font-medium text-slate-800">{item.topic}</p><strong className="shrink-0 text-sm tabular-nums text-slate-900">{item.proficiency == null ? '—' : `${item.proficiency}%`}</strong></div><div className="mt-2 flex items-center gap-3"><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-violet-500" style={{ width: `${Math.max(0, Math.min(100, item.proficiency ?? 0))}%` }} /></div><span className="text-xs text-slate-500">{item.total_questions} evaluated</span></div></div>)}</div> : <p className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Topic scores appear after valid evaluations are available.</p>}
        </article>
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-violet-50 text-violet-700"><Activity className="h-5 w-5" /></span><div><h2 className="font-semibold text-slate-950">Score history</h2><p className="mt-1 text-sm text-slate-500">Only completed evaluations with a valid score appear here.</p></div></div>
        {data.score_history.length ? <div className="mt-4 divide-y divide-slate-100">{data.score_history.map((item, index) => <div key={`${item.timestamp ?? item.date}-${item.type}-${index}`} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium capitalize text-slate-800">{item.type.replaceAll('_', ' ')}</p><time className="mt-0.5 block text-xs text-slate-500" dateTime={item.timestamp || undefined}>{formatCompletedAt(item.timestamp, item.date)}</time></div><span className="rounded-lg bg-emerald-50 px-3 py-1.5 text-sm font-bold tabular-nums text-emerald-800">{item.score}%</span></div>)}</div> : <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No validated assessment or interview scores have been recorded yet.</p>}
      </section>
    </>}
  </main>;
}
