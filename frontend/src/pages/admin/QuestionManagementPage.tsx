import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { industriesApi } from '../../api/candidates';
import { questionTaxonomyApi, questionsApi } from '../../api/services';
import { useAuth } from '../../context/AuthContext';
import type { Industry, Question } from '../../types';
import { RequiredLabel } from '../../components/common/RequiredMark';

const questionTypes = ['mcq_single', 'mcq_multiple', 'short_answer', 'long_answer', 'descriptive', 'coding', 'scenario', 'case_study', 'situational', 'behavioral', 'technical', 'domain_specific'];

export function QuestionManagementPage() {
  const { user } = useAuth();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [industryId, setIndustryId] = useState('');
  const [roleId, setRoleId] = useState('');
  const [skillIds, setSkillIds] = useState<string[]>([]);
  const [skills, setSkills] = useState<Array<{ id: string; name: string; is_active?: boolean }>>([]);
  const [questionType, setQuestionType] = useState('short_answer');
  const [questionText, setQuestionText] = useState('');
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [difficulty, setDifficulty] = useState('intermediate');
  const [round, setRound] = useState('');
  const [answer, setAnswer] = useState('');
  const [provenance, setProvenance] = useState('');
  const [optionsJson, setOptionsJson] = useState('[{"id":"A","text":"","is_correct":true},{"id":"B","text":"","is_correct":false}]');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState('');
  const [search, setSearch] = useState('');
  const [versions, setVersions] = useState<Record<string, Question[]>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [questionList, industryList, skillList] = await Promise.all([
        questionsApi.manage({ workflow_status: workflowStatus, search }), industriesApi.listIndustries(), questionTaxonomyApi.list('skill'),
      ]);
      setQuestions(questionList ?? []);
      setIndustries(industryList ?? []);
      setSkills((skillList as typeof skills).filter((skill) => skill.is_active !== false));
      setIndustryId((current) => current || industryList?.[0]?.id || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Question content could not be loaded.');
    } finally { setLoading(false); }
  }, [workflowStatus, search]);

  useEffect(() => { void load(); }, [load]);

  if (!user || (user.role !== 'administrator' && user.role !== 'content_manager')) return <Navigate to="/dashboard" replace />;

  async function createQuestion(event: FormEvent) {
    event.preventDefault();
    setError('');
    try {
      const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
      const workflowStatus = submitter?.value === 'draft' ? 'draft' : 'pending_review';
      const mcq = questionType === 'mcq_single' || questionType === 'mcq_multiple';
      const options = mcq ? JSON.parse(optionsJson) : [];
      await questionsApi.create({ question_text: questionText, question_type: questionType, industry_id: industryId,
        job_role_id: roleId || null, job_role_ids: roleId ? [roleId] : [], skill_ids: skillIds, subject, topic, difficulty, interview_round: round || 'General', options,
        expected_answer: answer, evaluation_rubric: {}, tags: [], source_provenance: provenance, approval_status: 'pending', workflow_status: workflowStatus });
      setQuestionText(''); setAnswer(''); setSubject(''); setTopic('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Question could not be created. Check the selected provenance and answer options.');
    }
  }

  async function generateDraft() {
    setError('');
    try {
      await questionsApi.generateDraft({ question_type: questionType, industry_id: industryId, job_role_id: roleId || null,
        job_role_ids: roleId ? [roleId] : [], skill_ids: skillIds,
        subject, topic, difficulty, interview_round: round || 'Technical', source_provenance: 'ai_generated' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI drafting is unavailable. No draft was saved.');
    }
  }

  async function decide(id: string, decision: 'approved' | 'rejected') {
    try { await questionsApi.review(id, decision); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Review action failed.'); }
  }

  async function submitForReview(id: string) {
    try { await questionsApi.submitForReview(id); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Draft could not be submitted for review.'); }
  }

  async function archive(id: string) {
    try { await questionsApi.archive(id); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Archive action failed.'); }
  }

  async function publish(id: string) {
    try { await questionsApi.publish(id); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Only approved content can be published.'); }
  }

  async function showVersions(id: string) {
    try { setVersions({ ...versions, [id]: await questionsApi.versions(id) }); }
    catch (err) { setError(err instanceof Error ? err.message : 'Revision history could not be loaded.'); }
  }

  async function restoreVersion(id: string, versionId: string) {
    try { await questionsApi.restoreVersion(id, versionId); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Revision could not be restored.'); }
  }

  const selectedIndustry = industries.find((industry) => industry.id === industryId);
  return <section className="space-y-6">
    <header><p className="text-sm font-semibold text-purple-700">Content management</p><h1 className="mt-1 text-3xl font-bold text-slate-900">Question review</h1><p className="mt-2 text-slate-600">New questions enter review. Review their provenance and content before publishing.</p></header>
    {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
    <form onSubmit={createQuestion} className="grid gap-4 rounded-xl border bg-white p-5 md:grid-cols-2">
      <h2 className="md:col-span-2 text-lg font-semibold text-slate-900">Create question draft</h2>
      <label className="text-sm font-medium"><RequiredLabel>Industry</RequiredLabel><select required value={industryId} onChange={(event) => { setIndustryId(event.target.value); setRoleId(''); }} className="mt-1 block w-full rounded-lg border p-2.5">{industries.map((industry) => <option key={industry.id} value={industry.id}>{industry.name}</option>)}</select></label>
      <label className="text-sm font-medium">Job role<select value={roleId} onChange={(event) => setRoleId(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5"><option value="">All roles</option>{selectedIndustry?.job_roles.filter((role) => role.is_active).map((role) => <option key={role.id} value={role.id}>{role.title}</option>)}</select></label>
      <label className="text-sm font-medium">Skill focus<select multiple value={skillIds} onChange={(event) => setSkillIds(Array.from(event.target.selectedOptions, (option) => option.value))} className="mt-1 block w-full rounded-lg border p-2.5">{skills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select><span className="mt-1 block font-normal text-slate-500">Select one or more skills from the taxonomy; manage the list in Admin → Question taxonomy.</span></label>
      <label className="text-sm font-medium">Question type<select value={questionType} onChange={(event) => setQuestionType(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5">{questionTypes.map((type) => <option key={type} value={type}>{type.replaceAll('_', ' ')}</option>)}</select></label>
      <label className="text-sm font-medium">Difficulty<select value={difficulty} onChange={(event) => setDifficulty(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5"><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option><option value="expert">Expert</option></select></label>
      <label className="text-sm font-medium"><RequiredLabel>Subject</RequiredLabel><input required value={subject} onChange={(event) => setSubject(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5" /></label>
      <label className="text-sm font-medium"><RequiredLabel>Topic</RequiredLabel><input required value={topic} onChange={(event) => setTopic(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5" /></label>
      <label className="text-sm font-medium">Interview round<input value={round} onChange={(event) => setRound(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5" placeholder="General, HR, Technical…" /></label>
      <label className="text-sm font-medium"><RequiredLabel>Content provenance</RequiredLabel><select required value={provenance} onChange={(event) => setProvenance(event.target.value)} className="mt-1 block w-full rounded-lg border p-2.5"><option value="">Select provenance</option><option value="source_verified">Source verified</option><option value="source_formatted">Source formatted</option><option value="ai_generated">AI generated</option><option value="editorially_reviewed">Editorially reviewed</option></select></label>
      <label className="text-sm font-medium md:col-span-2"><RequiredLabel>Question</RequiredLabel><textarea required minLength={10} value={questionText} onChange={(event) => setQuestionText(event.target.value)} rows={3} className="mt-1 block w-full rounded-lg border p-2.5" /></label>
      {(questionType === 'mcq_single' || questionType === 'mcq_multiple') && <label className="text-sm font-medium md:col-span-2"><RequiredLabel>Options JSON</RequiredLabel><textarea value={optionsJson} onChange={(event) => setOptionsJson(event.target.value)} rows={4} className="mt-1 block w-full rounded-lg border p-2.5 font-mono text-xs" /><span className="mt-1 block font-normal text-slate-500">Use unique option IDs and set is_correct on the correct choice(s).</span></label>}
      <label className="text-sm font-medium md:col-span-2"><RequiredLabel>Expected answer</RequiredLabel><textarea required value={answer} onChange={(event) => setAnswer(event.target.value)} rows={3} className="mt-1 block w-full rounded-lg border p-2.5" /></label>
      <div className="md:col-span-2 flex flex-wrap gap-2"><button type="submit" name="workflow_status" value="draft" className="rounded-lg border px-4 py-2.5 text-sm font-semibold">Save as draft</button><button type="submit" name="workflow_status" value="pending_review" className="rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-800">Save as pending review</button><button type="button" disabled={!industryId || !subject.trim() || !topic.trim()} onClick={()=>void generateDraft()} className="rounded-lg border border-violet-700 px-4 py-2.5 text-sm font-semibold text-violet-800 disabled:opacity-50">Generate AI draft for review</button></div>
    </form>
    <section className="space-y-3"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-semibold text-slate-900">Question content</h2><div className="flex gap-2"><input aria-label="Search question content" value={search} onChange={event=>setSearch(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'){event.preventDefault();void load();}}} placeholder="Search questions" className="rounded-lg border px-3 py-2 text-sm"/><select aria-label="Filter question workflow" value={workflowStatus} onChange={event=>setWorkflowStatus(event.target.value)} className="rounded-lg border px-3 py-2 text-sm"><option value="">All workflow states</option>{['draft','pending_review','approved','published','rejected','archived','superseded'].map(state=><option key={state} value={state}>{state.replaceAll('_',' ')}</option>)}</select><button type="button" onClick={()=>void load()} className="rounded-lg border px-3 py-2 text-sm">Apply</button></div></div>{loading ? <p className="rounded-xl bg-white p-6 text-slate-600">Loading content…</p> : questions.length ? questions.map((question) => <article key={question.id} className="rounded-xl border bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-4"><div className="max-w-3xl"><div className="flex flex-wrap gap-2 text-xs"><span className="rounded-full bg-purple-50 px-2 py-1 text-purple-800">{(question.workflow_status ?? question.approval_status).replaceAll('_', ' ')}</span><span className="rounded-full bg-slate-100 px-2 py-1">Version {question.version_number ?? 1}</span><span className="rounded-full bg-slate-100 px-2 py-1">{question.source_provenance.replaceAll('_', ' ')}</span><span className="rounded-full bg-slate-100 px-2 py-1">{question.industry?.name}</span></div><h3 className="mt-3 font-semibold text-slate-900">{question.question_text}</h3><p className="mt-2 text-sm text-slate-600">Expected answer: {question.expected_answer}</p></div><div className="flex flex-wrap gap-2">{question.workflow_status === 'draft' && <button type="button" onClick={() => void submitForReview(question.id)} className="rounded-md bg-violet-700 px-3 py-2 text-sm font-semibold text-white">Submit for review</button>}{question.workflow_status === 'pending_review' && <><button type="button" onClick={() => void decide(question.id, 'approved')} className="rounded-md bg-violet-700 px-3 py-2 text-sm font-semibold text-white">Approve</button><button type="button" onClick={() => void decide(question.id, 'rejected')} className="rounded-md border px-3 py-2 text-sm">Reject</button></>}{question.workflow_status === 'approved' && <button type="button" onClick={() => void publish(question.id)} className="rounded-md bg-violet-700 px-3 py-2 text-sm font-semibold text-white">Publish</button>}<button type="button" onClick={() => void showVersions(question.id)} className="rounded-md border px-3 py-2 text-sm">Versions</button><button type="button" onClick={() => void archive(question.id)} className="rounded-md border border-rose-200 px-3 py-2 text-sm text-rose-700">Archive</button></div></div>
      {versions[question.id] && <div className="mt-4 border-t pt-3"><h4 className="text-sm font-semibold">Revision history</h4><ul className="mt-2 space-y-2">{versions[question.id].map(version=><li key={version.id} className="flex flex-wrap items-center justify-between gap-2 text-sm"><span>v{version.version_number} · {version.workflow_status} · {version.question_text.slice(0,100)}</span>{version.workflow_status!=='published'&&<button type="button" onClick={()=>void restoreVersion(question.id,version.id)} className="rounded border px-2 py-1">Restore as draft</button>}</li>)}</ul></div>}
    </article>) : <p className="rounded-xl border border-dashed bg-white p-6 text-slate-600">No questions in the bank yet.</p>}</section>
  </section>;
}
