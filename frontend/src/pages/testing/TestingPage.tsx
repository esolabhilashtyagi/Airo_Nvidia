import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Clock3, Flag, History, Play, Send } from 'lucide-react';
import { industriesApi } from '../../api/candidates';
import { testingApi } from '../../api/services';
import { useAuth } from '../../context/AuthContext';
import { assessmentSessionKey } from './assessmentSessionKey';
import { RequiredLabel } from '../../components/common/RequiredMark';
import { isWholeNumberInRange, normalizeWholeNumberInput } from './wholeNumberInput';
import type { AssessmentAttempt, AssessmentResult, Industry, Question } from '../../types';

type ActiveAttempt = Awaited<ReturnType<typeof testingApi.startAssessment>>;
type SavedAnswer = { selected_options: string[]; text_response: string; is_marked_for_review: boolean };
function formatTime(seconds: number) {
  return `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`;
}

export function TestingPage() {
  const [searchParams] = useSearchParams();
  const requestedAssessmentId = searchParams.get('assessmentId');
  const { user } = useAuth();
  const userSessionKey = user?.id ? assessmentSessionKey(user.id) : null;
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [history, setHistory] = useState<AssessmentAttempt[]>([]);
  const [industryId, setIndustryId] = useState('');
  const [roleId, setRoleId] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [topicSuggestions, setTopicSuggestions] = useState<Awaited<ReturnType<typeof testingApi.suggestTopics>>['suggestions']>([]);
  const [suggestionSource, setSuggestionSource] = useState('');
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [round, setRound] = useState('');
  const [number, setNumber] = useState('');
  const [duration, setDuration] = useState(20);
  const [marks, setMarks] = useState('10');
  const [negativeMarks, setNegativeMarks] = useState('0');
  const [assessmentId, setAssessmentId] = useState('');
  const [aiGeneratedQuestionCount, setAiGeneratedQuestionCount] = useState(0);
  const [active, setActive] = useState<ActiveAttempt | null>(null);
  const [attemptId, setAttemptId] = useState('');
  const [answers, setAnswers] = useState<Record<string, SavedAnswer>>({});
  const [index, setIndex] = useState(0);
  const [remaining, setRemaining] = useState(0);
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [error, setError] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const submitRef = useRef<((automatic?: boolean) => Promise<void>) | null>(null);

  const refreshHistory = useCallback(async () => {
    setHistory(await testingApi.getHistory());
  }, []);

  const loadAttempt = useCallback(async (id: string) => {
    const resumed = await testingApi.startAssessment(id);
    setAssessmentId(id);
    setActive(resumed);
    setAiGeneratedQuestionCount(resumed.questions.filter((question) => question.source_provenance === 'ai_generated').length);
    setAttemptId(resumed.attempt_id);
    setIndex(0);
    setRemaining(Math.max(0, Math.floor((new Date(resumed.ends_at).getTime() - Date.now()) / 1000)));
    setAnswers(Object.fromEntries(resumed.saved_answers.map((answer) => [answer.question_id, {
      selected_options: answer.selected_options,
      text_response: answer.text_response ?? '',
      is_marked_for_review: answer.is_marked_for_review,
    }])));
    setResult(null);
  }, []);

  useEffect(() => {
    let mounted = true;
    void Promise.all([industriesApi.listIndustries(), testingApi.getHistory()]).then(async ([items, previous]) => {
      if (!mounted) return;
      setIndustries(items);
      setHistory(previous);
      const storedAssessment = requestedAssessmentId || (userSessionKey ? localStorage.getItem(userSessionKey) : null);
      if (requestedAssessmentId && userSessionKey) localStorage.setItem(userSessionKey, requestedAssessmentId);
      if (storedAssessment) await loadAttempt(storedAssessment);
    }).catch((caught) => {
      if (mounted) setError(caught instanceof Error ? caught.message : 'Testing data could not be loaded.');
    }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [loadAttempt, userSessionKey, requestedAssessmentId]);

  useEffect(() => {
    if (!industryId || subject.trim().length < 2 || active || result) {
      setTopicSuggestions([]);
      return;
    }
    let current = true;
    const timer = window.setTimeout(() => {
      setSuggestionsLoading(true);
      void testingApi.suggestTopics(subject.trim()).then((response) => {
        if (!current) return;
        setTopicSuggestions(response.suggestions);
        setSuggestionSource(response.ai_status);
      }).catch(() => {
        if (current) setTopicSuggestions([]);
      }).finally(() => { if (current) setSuggestionsLoading(false); });
    }, 350);
    return () => { current = false; window.clearTimeout(timer); };
  }, [industryId, subject, active, result]);

  useEffect(() => {
    if (!active || !attemptId || result) return;
    const current = active.questions[index];
    const value = current ? answers[current.id] : null;
    if (!current || !value) return;
    const timer = window.setTimeout(() => {
      setSaving(true);
      void testingApi.saveAnswer(attemptId, {
        question_id: current.id,
        selected_options: value.selected_options,
        text_response: value.text_response || null,
        is_marked_for_review: value.is_marked_for_review,
      }).then((saved) => {
        if (saved?.expired) void submitRef.current?.(true);
        else setStatusMessage('Answer saved');
      }).catch((caught) => setError(caught instanceof Error ? caught.message : 'Answer could not be saved.')).finally(() => setSaving(false));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [active, answers, attemptId, index, result]);

  const submit = useCallback(async (automatic = false) => {
    if (!attemptId || result) return;
    setError('');
    setSaving(true);
    try {
      const submitted = await testingApi.submitAssessment(attemptId);
      setResult(submitted);
      setActive(null);
      if (userSessionKey) localStorage.removeItem(userSessionKey);
      setConfirmSubmit(false);
      setStatusMessage(automatic ? 'Time expired. Your responses were submitted.' : 'Assessment submitted.');
      await refreshHistory();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Submission failed. Your saved responses remain available.');
    } finally {
      setSaving(false);
    }
  }, [attemptId, refreshHistory, result, userSessionKey]);
  useEffect(() => { submitRef.current = submit; }, [submit]);

  useEffect(() => {
    if (!active || result) return;
    const timer = window.setInterval(() => {
      const seconds = Math.max(0, Math.floor((new Date(active.ends_at).getTime() - Date.now()) / 1000));
      setRemaining(seconds);
      if (seconds === 0) void submit(true);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [active, result, submit]);

  async function configure() {
    setError('');
    if (!isWholeNumberInRange(number, 1, 50)) {
      setError('Enter the whole-number question count you want (1 to 50).');
      return;
    }
    if (!isWholeNumberInRange(marks, 1, 100)) {
      setError('Enter whole marks per question from 1 to 100.');
      return;
    }
    if (!isWholeNumberInRange(negativeMarks, 0, 100)) {
      setError('Enter whole negative marks from 0 to 100.');
      return;
    }
    try {
      setConfiguring(true);
      const configured = await testingApi.configure({
        industry_id: industryId,
        job_role_id: roleId || null,
        subject: subject || null,
        topic: topic || null,
        difficulty: difficulty || null,
        interview_round: round || null,
        num_questions: Number(number),
        duration_minutes: duration,
        marks_per_question: Number(marks),
        negative_marking_points: Number(negativeMarks),
        randomize_questions: true,
      });
      setAssessmentId(configured.id);
      setAiGeneratedQuestionCount(configured.ai_generated_question_count ?? 0);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No assessment could be configured for these filters.');
    } finally {
      setConfiguring(false);
    }
  }

  async function begin() {
    if (!assessmentId) return;
    setError('');
    try {
      if (!userSessionKey) throw new Error('Your account session is not ready. Please sign in again.');
      localStorage.setItem(userSessionKey, assessmentId);
      await loadAttempt(assessmentId);
    } catch (caught) {
      if (userSessionKey) localStorage.removeItem(userSessionKey);
      setError(caught instanceof Error ? caught.message : 'Assessment could not be started.');
    }
  }

  function updateAnswer(question: Question, update: Partial<SavedAnswer>) {
    setAnswers((current) => ({
      ...current,
      [question.id]: {
        selected_options: update.selected_options ?? current[question.id]?.selected_options ?? [],
        text_response: update.text_response ?? current[question.id]?.text_response ?? '',
        is_marked_for_review: update.is_marked_for_review ?? current[question.id]?.is_marked_for_review ?? false,
      },
    }));
  }

  async function openResult(id: string) {
    setError('');
    try {
      setResult(await testingApi.getResult(id));
      setAttemptId(id);
      setActive(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Result is not available yet.');
    }
  }

  if (loading) return <div className="rounded-xl border bg-white p-8 text-slate-600">Loading assessment workspace…</div>;

  const currentQuestion = active?.questions[index];
  const currentAnswer = currentQuestion ? answers[currentQuestion.id] ?? { selected_options: [], text_response: '', is_marked_for_review: false } : null;
  const selectedIndustry = industries.find((item) => item.id === industryId);

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-violet-100 bg-gradient-to-br from-violet-50 via-white to-indigo-50 p-6 text-slate-900 shadow-sm shadow-violet-950/5 sm:p-8"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-800">Testing mode</p><h1 className="mt-2 text-3xl font-bold text-slate-950">Practice under real time limits</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Configure a timed, scored assessment with answer review after submission. Mock interviews are conversational role-play with follow-up questions and coaching.</p></header>
      {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}

      {result ? <article className="rounded-xl border bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase text-violet-700">Assessment report · {result.evaluation_status}</p><h2 className="mt-1 text-2xl font-bold">{result.percentage === null ? 'Partial evaluation' : `${result.percentage}%`}</h2><p className="mt-1 text-sm text-slate-600">{result.percentage === null ? `Known marks: ${result.total_score}/${result.max_score}. Unknown answers were not scored.` : `${result.total_score}/${result.max_score} marks · ${result.passed ? 'Passed' : 'Not passed'}`}</p></div><button onClick={() => setResult(null)} className="rounded-lg border px-4 py-2 text-sm font-medium">Back to testing</button></div>
        {result.recommendations && <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">{result.recommendations}</p>}
        <div className="mt-5 grid gap-3 sm:grid-cols-3"><div className="rounded-lg bg-emerald-50 p-4"><strong>{result.correct_count}</strong><p className="text-xs text-slate-600">Correct</p></div><div className="rounded-lg bg-rose-50 p-4"><strong>{result.incorrect_count}</strong><p className="text-xs text-slate-600">Incorrect</p></div><div className="rounded-lg bg-slate-100 p-4"><strong>{result.unanswered_count}</strong><p className="text-xs text-slate-600">Unanswered</p></div></div>
        <h3 className="mt-6 font-semibold">Question review</h3><ol className="mt-3 space-y-3">{result.question_feedback.map((item, questionIndex) => <li key={item.question_id} className="rounded-lg border p-4"><div className="flex justify-between gap-3"><strong>Question {questionIndex + 1} · {item.topic}</strong><span className="text-xs text-slate-500">{item.status} · {item.provenance ?? 'none'}</span></div><p className="mt-2 text-sm">{item.feedback}</p>{item.missing_concepts?.length ? <p className="mt-2 text-sm text-purple-800">Areas to address: {item.missing_concepts.join(', ')}</p> : null}{item.expected_answer && <details className="mt-3 text-sm"><summary className="cursor-pointer font-medium">View reference answer</summary><p className="mt-2 text-slate-700">{item.expected_answer}</p>{item.explanation && <p className="mt-2 text-slate-600">{item.explanation}</p>}</details>}</li>)}</ol>
      </article> : active && currentQuestion && currentAnswer ? <article className="mx-auto max-w-4xl rounded-xl border bg-white p-5 shadow-sm sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4"><div><p className="text-xs font-semibold uppercase text-violet-700">{active.title}</p><p className="mt-1 text-sm text-slate-500">Question {index + 1} of {active.questions.length} · {Object.keys(answers).filter((id) => answers[id].selected_options.length || answers[id].text_response.trim()).length} answered</p></div><div className={`flex items-center gap-2 rounded-lg px-3 py-2 font-mono text-lg font-bold ${remaining < 60 ? 'bg-red-50 text-red-700' : 'bg-indigo-50 text-indigo-800'}`}><Clock3 className="h-4 w-4" />{formatTime(remaining)}</div></div>
        <div className="mt-6 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-indigo-600 transition-all" style={{ width: `${((index + 1) / active.questions.length) * 100}%` }} /></div>
        <div className="mt-6 flex items-start justify-between gap-3"><h2 className="text-xl font-semibold leading-8 text-slate-900">{currentQuestion.question_text}</h2><button aria-label={currentAnswer.is_marked_for_review ? 'Remove review flag' : 'Mark for review'} onClick={() => updateAnswer(currentQuestion, { is_marked_for_review: !currentAnswer.is_marked_for_review })} className={`rounded-lg p-2 ${currentAnswer.is_marked_for_review ? 'bg-purple-100 text-purple-800' : 'text-slate-500 hover:bg-slate-100'}`}><Flag className="h-4 w-4" /></button></div>
        {active.questions.some((question) => question.source_provenance === 'ai_generated') && <p role="status" className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">This assessment includes AI-generated questions because the approved Question Bank did not have enough matches. These are practice questions that have not yet been editorially reviewed; their answer keys may need review.</p>}
        <div className="mt-2 flex gap-2 text-xs text-slate-500"><span>{currentQuestion.difficulty}</span><span>·</span><span>{currentQuestion.question_type.replaceAll('_', ' ')}</span><span>·</span><span>{saving ? 'Saving…' : statusMessage || 'Autosave enabled'}</span></div>
        {currentQuestion.options.length ? <fieldset className="mt-6 space-y-2"><legend className="mb-2 text-sm font-medium">Select {currentQuestion.question_type === 'mcq_multiple' ? 'all that apply' : 'one answer'}</legend>{currentQuestion.options.map((option) => { const checked = currentAnswer.selected_options.includes(option.id); return <label key={option.id} className={`flex cursor-pointer gap-3 rounded-lg border p-4 text-sm ${checked ? 'border-indigo-500 bg-indigo-50' : 'hover:bg-slate-50'}`}><input type={currentQuestion.question_type === 'mcq_multiple' ? 'checkbox' : 'radio'} checked={checked} onChange={() => updateAnswer(currentQuestion, { selected_options: currentQuestion.question_type === 'mcq_multiple' ? checked ? currentAnswer.selected_options.filter((id) => id !== option.id) : [...currentAnswer.selected_options, option.id] : [option.id], text_response: '' })} />{option.text}</label>; })}</fieldset> : <label className="mt-6 block text-sm font-medium">Your response<textarea aria-label="Assessment answer" rows={8} maxLength={20000} value={currentAnswer.text_response} onChange={(event) => updateAnswer(currentQuestion, { text_response: event.target.value, selected_options: [] })} className="mt-2 w-full rounded-lg border p-3 text-sm" placeholder={currentQuestion.question_type === 'coding' ? 'Paste your code. Secure execution may be unavailable.' : 'Write your answer…'} /></label>}
        <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t pt-4"><button onClick={() => setIndex((value) => Math.max(0, value - 1))} disabled={index === 0} className="inline-flex items-center gap-1 rounded-lg border px-4 py-2 text-sm disabled:opacity-40"><ChevronLeft className="h-4 w-4" />Previous</button><div className="flex flex-wrap gap-2"><button onClick={() => setIndex((value) => Math.min(active.questions.length - 1, value + 1))} disabled={index >= active.questions.length - 1} className="inline-flex items-center gap-1 rounded-lg border px-4 py-2 text-sm disabled:opacity-40">Next<ChevronRight className="h-4 w-4" /></button><button onClick={() => setConfirmSubmit(true)} className="inline-flex items-center gap-2 rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white"><Send className="h-4 w-4" />Submit</button></div></div>
        <div className="mt-4 flex flex-wrap gap-2">{active.questions.map((question, questionIndex) => <button key={question.id} onClick={() => setIndex(questionIndex)} aria-label={`Go to question ${questionIndex + 1}`} className={`h-9 w-9 rounded-lg border text-xs font-semibold ${questionIndex === index ? 'border-violet-700 bg-violet-700 text-white' : answers[question.id]?.is_marked_for_review ? 'border-purple-400 bg-purple-50 text-purple-800' : 'bg-white text-slate-700'}`}>{questionIndex + 1}</button>)}</div>
        {confirmSubmit && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-500/20 p-4 backdrop-blur-[1px]"><div role="dialog" aria-modal="true" aria-labelledby="submit-title" className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"><h2 id="submit-title" className="text-lg font-semibold">Submit assessment?</h2><p className="mt-2 text-sm text-slate-600">You have answered {Object.values(answers).filter((answer) => answer.selected_options.length || answer.text_response.trim()).length} of {active.questions.length} questions. Saved responses will be evaluated and the attempt will close.</p><div className="mt-5 flex justify-end gap-2"><button onClick={() => setConfirmSubmit(false)} className="rounded-lg border px-4 py-2 text-sm">Continue test</button><button onClick={() => void submit()} disabled={saving} className="rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800">Submit now</button></div></div></div>}
      </article> : assessmentId ? <article className="rounded-xl border bg-white p-6 shadow-sm"><p className="text-xs font-semibold uppercase text-violet-700">Instructions</p><h2 className="mt-2 text-xl font-bold">Your assessment is ready</h2>{aiGeneratedQuestionCount > 0 && <p role="status" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">This assessment includes {aiGeneratedQuestionCount} AI-generated question(s) that have not yet been editorially reviewed. They are practice material, not approved Question Bank content.</p>}<ul className="mt-4 list-inside list-disc space-y-2 text-sm text-slate-700"><li>The backend timer controls the deadline; refresh recovery uses the saved attempt.</li><li>Your answers autosave as you work. Objective questions are marked deterministically.</li><li>Subjective or coding evaluations may be unavailable without their provider; unavailable answers are saved without fabricated scores.</li><li>Answer keys and explanations appear only after final submission.</li></ul><button onClick={() => void begin()} className="mt-5 inline-flex items-center gap-2 rounded-lg bg-violet-700 px-5 py-2.5 font-semibold text-white"><Play className="h-4 w-4" />Start timed assessment</button></article> : <div className="space-y-5">
        <article className="rounded-xl border bg-white p-5 shadow-sm sm:p-6"><h2 className="text-lg font-semibold">Configure your assessment</h2><p className="mt-1 text-sm text-slate-600">Published Question Bank content is used first; if matching questions are insufficient, the configured provider can generate clearly labeled practice questions.</p><form onSubmit={(event) => { event.preventDefault(); void configure(); }} className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium"><RequiredLabel>Industry</RequiredLabel><select required value={industryId} onChange={(event) => { setIndustryId(event.target.value); setRoleId(''); }} className="mt-1 block w-full rounded-lg border px-3 py-2"><option value="">Choose industry</option>{industries.map((industry) => <option key={industry.id} value={industry.id}>{industry.name}</option>)}</select></label>
          <label className="text-sm font-medium"><RequiredLabel>Job role</RequiredLabel><select required value={roleId} onChange={(event) => setRoleId(event.target.value)} className="mt-1 block w-full rounded-lg border px-3 py-2"><option value="">Choose a role</option>{selectedIndustry?.job_roles.map((role) => <option key={role.id} value={role.id}>{role.title}</option>)}</select></label>
          <label className="text-sm font-medium"><RequiredLabel>Subject</RequiredLabel><input required value={subject} onChange={(event) => { setSubject(event.target.value); setTopic(''); }} className="mt-1 block w-full rounded-lg border px-3 py-2" placeholder="e.g. System Design" />{suggestionsLoading && <span role="status" className="mt-1 block text-xs font-normal text-slate-500">Finding relevant topics…</span>}</label>
          <label className="text-sm font-medium"><RequiredLabel>Topic</RequiredLabel><input required value={topic} onChange={(event) => setTopic(event.target.value)} className="mt-1 block w-full rounded-lg border px-3 py-2" placeholder="Choose a suggestion or enter a topic" />{topicSuggestions.length > 0 && <span className="mt-2 block space-y-1.5">{topicSuggestions.map((item) => <button type="button" key={`${item.subject}-${item.topic}`} onClick={() => setTopic(item.topic)} className="mr-1 inline-flex rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs text-violet-800">{item.topic}</button>)}<span className="block text-[11px] font-normal text-slate-500">{suggestionSource === 'available' ? 'AI suggestions, checked against your profile and practice history' : 'Suggestions from the active topic catalog'}</span></span>}</label>
          <label className="text-sm font-medium"><RequiredLabel>Difficulty</RequiredLabel><select required value={difficulty} onChange={(event) => setDifficulty(event.target.value)} className="mt-1 block w-full rounded-lg border px-3 py-2"><option value="">Choose difficulty</option>{['beginner', 'intermediate', 'advanced', 'expert', 'mixed'].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="text-sm font-medium"><RequiredLabel>Interview round</RequiredLabel><input required value={round} onChange={(event) => setRound(event.target.value)} className="mt-1 block w-full rounded-lg border px-3 py-2" placeholder="e.g. Technical" /></label>
          <label className="text-sm font-medium"><RequiredLabel>Questions</RequiredLabel><input type="text" inputMode="numeric" pattern="[0-9]*" maxLength={2} aria-label="Questions" placeholder="e.g. 10" value={number} onChange={(event) => { const value = normalizeWholeNumberInput(event.target.value); if (value !== null) setNumber(value); }} aria-invalid={!isWholeNumberInRange(number, 1, 50)} className="mt-1 block w-full rounded-lg border px-3 py-2" /><span className="mt-1 block text-xs font-normal text-slate-500">Choose the number you want (1–50). Backspace clears the field completely.</span></label>
          <label className="text-sm font-medium"><RequiredLabel>Duration (minutes)</RequiredLabel><input type="number" min={5} max={180} value={duration} onChange={(event) => setDuration(Number(event.target.value))} className="mt-1 block w-full rounded-lg border px-3 py-2" /></label>
          <label className="text-sm font-medium"><RequiredLabel>Marks per question</RequiredLabel><input type="text" inputMode="numeric" pattern="[0-9]*" maxLength={3} aria-label="Marks per question" value={marks} onChange={(event) => { const value = normalizeWholeNumberInput(event.target.value); if (value !== null) setMarks(value); }} aria-invalid={!isWholeNumberInRange(marks, 1, 100)} className="mt-1 block w-full rounded-lg border px-3 py-2" /><span className="mt-1 block text-xs font-normal text-slate-500">Whole marks only (1–100).</span></label>
          <label className="text-sm font-medium">Negative marks<input type="text" inputMode="numeric" pattern="[0-9]*" maxLength={3} aria-label="Negative marks" value={negativeMarks} onChange={(event) => { const value = normalizeWholeNumberInput(event.target.value); if (value !== null) setNegativeMarks(value); }} aria-invalid={!isWholeNumberInRange(negativeMarks, 0, 100)} className="mt-1 block w-full rounded-lg border px-3 py-2" /><span className="mt-1 block text-xs font-normal text-slate-500">Whole marks only (0–100).</span></label>
          <button disabled={configuring || !industryId || !roleId || !subject.trim() || !topic.trim() || !difficulty || !round.trim() || !isWholeNumberInRange(number, 1, 50) || !isWholeNumberInRange(marks, 1, 100) || !isWholeNumberInRange(negativeMarks, 0, 100)} className="sm:col-span-2 rounded-lg bg-violet-700 px-4 py-2.5 font-semibold text-white disabled:opacity-50">{configuring ? 'Preparing questions…' : 'Prepare assessment'}</button>
        </form></article>
        <article className="rounded-xl border bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><History className="h-5 w-5 text-violet-700" /><h2 className="font-semibold">Assessment history</h2></div>{history.length ? <ul className="mt-4 space-y-2">{history.map((item) => <li key={item.id} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 p-3"><div><p className="text-sm font-medium">{item.assessment_title}</p><p className="text-xs text-slate-500">{item.status} · {item.evaluation_status ?? 'result pending'}</p></div>{item.completed_at && <button onClick={() => void openResult(item.id)} className="text-sm font-semibold text-violet-700">View report</button>}</li>)}</ul> : <p className="mt-4 text-sm text-slate-500">Completed attempts will appear here.</p>}</article>
      </div>}
      {statusMessage && !active && !result && <p role="status" className="text-sm text-emerald-700">{statusMessage}</p>}
    </section>
  );
}
