import { useEffect, useState } from 'react';
import { interviewsApi, type InterviewReport, type InterviewSession } from '../../api/interviews';
import { industriesApi } from '../../api/candidates';
import { RequiredLabel } from '../../components/common/RequiredMark';
import type { Industry } from '../../types';

export function InterviewPage() {
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [industryId, setIndustryId] = useState('');
  const [role, setRole] = useState('');
  const [round, setRound] = useState('');
  const [count, setCount] = useState(5);
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [answer, setAnswer] = useState('');
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    void industriesApi.listIndustries().then((rows) => {
      setIndustries(rows);
      setIndustryId(rows[0]?.id ?? '');
    }).catch((caught) => setError(caught.message));
    void interviewsApi.history().then(setHistory).catch(() => undefined);
  }, []);

  async function start() {
    setBusy(true);
    setError('');
    try {
      const row = await interviewsApi.setup({
        industry_id: industryId || null,
        job_role: role,
        interview_round: round,
        number_of_questions: count,
        duration_minutes: 20,
        mode: 'text',
      });
      setSession(row);
      setReport(null);
      setAnswer('');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Interview could not be started');
    } finally {
      setBusy(false);
    }
  }

  async function respond() {
    if (!session || !answer.trim()) return;
    setBusy(true);
    setError('');
    try {
      const result = await interviewsApi.respond(session.id, answer);
      if ('mock_interview_id' in result) {
        setReport(result);
        setSession(null);
      } else {
        setSession(result);
        setAnswer('');
        if (result.status === 'completed') {
          try {
            setReport(await interviewsApi.report(result.id));
            setSession(null);
          } catch {
            // Keep the saved session available if the report request needs a retry.
          }
        }
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Response could not be saved');
    } finally {
      setBusy(false);
    }
  }

  async function conclude() {
    if (!session) return;
    setBusy(true);
    setError('');
    try {
      setReport(await interviewsApi.conclude(session.id));
      setSession(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Interview could not be concluded');
    } finally {
      setBusy(false);
    }
  }

  return <main className="mx-auto max-w-4xl space-y-6">
    <header>
      <p className="text-sm font-semibold text-violet-700">Interview practice</p>
      <h1 className="mt-1 text-3xl font-bold text-slate-900">Mock interview</h1>
      <p className="mt-2 text-slate-600">Practice role-specific questions, follow-ups, and get structured feedback.</p>
    </header>
    {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}

    {!session && !report && <section className="rounded-xl border bg-white p-6">
      <h2 className="text-lg font-semibold">Configure a text interview</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="text-sm"><RequiredLabel>Industry</RequiredLabel><select required value={industryId} onChange={(event) => setIndustryId(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5"><option value="">Choose industry</option>{industries.map((industry) => <option key={industry.id} value={industry.id}>{industry.name}</option>)}</select></label>
        <label className="text-sm"><RequiredLabel>Target role</RequiredLabel><input required value={role} onChange={(event) => setRole(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5" /></label>
        <label className="text-sm"><RequiredLabel>Interview round</RequiredLabel><select required value={round} onChange={(event) => setRound(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5"><option value="">Choose interview round</option>{['Technical', 'Behavioral', 'HR', 'System Design', 'General'].map((item) => <option key={item}>{item}</option>)}</select></label>
        <label className="text-sm"><RequiredLabel>Question count</RequiredLabel><input required type="number" min={1} max={20} value={count} onChange={(event) => setCount(Number(event.target.value))} className="mt-1 block w-full rounded-lg border p-2.5" /></label>
      </div>
      <button disabled={busy || !industryId || !role.trim() || !round || count < 1 || count > 20} onClick={() => void start()} className="mt-5 rounded-lg bg-violet-700 px-4 py-2.5 font-semibold text-white transition-colors hover:bg-violet-800 disabled:opacity-50">{busy ? 'Starting…' : 'Start interview'}</button>
    </section>}

    {session && <section className="space-y-4 rounded-xl border bg-white p-6">
      <div className="flex items-center justify-between"><p className="text-sm text-slate-500">Question {session.current_question_index} of {session.total_questions}</p>{session.ai_status === 'unavailable' && <span className="rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-800">Follow-up temporarily unavailable</span>}</div>
      {session.interviewer_message ? <>
        <h2 className="text-xl font-semibold">{session.interviewer_message}</h2>
        <label className="block text-sm font-medium"><RequiredLabel>Your answer</RequiredLabel><textarea value={answer} onChange={(event) => setAnswer(event.target.value)} rows={7} className="mt-2 block w-full rounded-lg border p-3" /></label>
        <button disabled={busy || !answer.trim()} onClick={() => void respond()} className="rounded-lg bg-violet-700 px-4 py-2.5 font-semibold text-white disabled:opacity-50">{busy ? 'Saving…' : 'Save answer and continue'}</button>
      </> : <div role="status" className="rounded-lg bg-purple-50 p-4 text-sm text-purple-900">Your answer is saved. Follow-up is unavailable; conclude the interview to view the final review.</div>}
      <button disabled={busy} onClick={() => void conclude()} className="ml-3 rounded-lg border px-4 py-2.5 text-sm">Conclude interview</button>
      {/* Saved answers are intentionally withheld until the final interview report. */}
    </section>}

    {report && <section className="space-y-5 rounded-xl border bg-white p-6">
      <div>
        <h2 className="text-xl font-bold">Interview report</h2>
        <p className="mt-2">Evaluation status: <strong>{report.evaluation_status}</strong> ({report.evaluation_provenance})</p>
        {report.overall_score == null
          ? <p className="mt-3 rounded-lg bg-purple-50 p-4 text-purple-900">The interview is complete. No score or refined responses are available because a validated AI evaluation was not returned. Your original answers are preserved below.</p>
          : <p className="mt-3 text-3xl font-bold">{report.overall_score}/100</p>}
      </div>
      <section aria-labelledby="final-responses-title" className="space-y-3">
        <div><h3 id="final-responses-title" className="font-semibold text-slate-900">Final response review</h3><p className="mt-1 text-sm text-slate-500">Your answers and fact-preserving refinements are shown after the interview is complete.</p></div>
        {report.responses.length ? report.responses.map((item) => <article key={item.question_number} className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Question {item.question_number}</p>
          <h4 className="mt-1 font-medium text-slate-900">{item.question}</h4>
          <div className="mt-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Your submitted answer</p><p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-700">{item.candidate_answer}</p></div>
          <div className="mt-4 rounded-lg bg-violet-50 p-3"><p className="text-xs font-semibold uppercase tracking-wide text-violet-800">Refined response</p><p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-800">{item.refined_answer || 'A refined response was not returned for this answer. Your original response is preserved.'}</p></div>
        </article>) : <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">No submitted responses are available for this interview.</p>}
      </section>
      <button className="text-sm text-violet-800 underline" onClick={() => setReport(null)}>Back to interviews</button>
    </section>}

    {history.length > 0 && !session && !report && <section className="rounded-xl border bg-white p-6"><h2 className="font-semibold">Recent interviews</h2>{history.map((row, index) => <p key={String(row.id ?? index)} className="mt-3 text-sm text-slate-700">{String(row.job_role ?? 'Interview')} · {String(row.status ?? 'unknown')} · evaluation {String(row.evaluation_status ?? 'unavailable')}</p>)}</section>}
  </main>;
}
