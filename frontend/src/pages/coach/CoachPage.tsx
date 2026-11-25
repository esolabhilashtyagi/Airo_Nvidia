import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, Bot, BookOpen, ChevronDown, Send, Target } from 'lucide-react';
import { Link } from 'react-router-dom';
import { coachApi, modulesApi } from '../../api/services';
import type { Roadmap } from '../../types';
import { RequiredLabel } from '../../components/common/RequiredMark';

type SkillGap = Awaited<ReturnType<typeof coachApi.getSkillGap>>;
type Conversation = Awaited<ReturnType<typeof coachApi.getConversation>>;

function formatInline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => part.startsWith('**') && part.endsWith('**')
    ? <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong>
    : part);
}

function CoachMessageText({ text }: { text: string }) {
  const normalized = text
    .replace(/\r/g, '')
    .replace(/\s+\*\s+(?=\*\*)/g, ' ')
    .replace(/\s+(?=\d+\.\s+\*\*)/g, '\n');
  const lines = normalized.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const blocks: Array<{ type: 'paragraph' | 'ordered' | 'unordered'; lines: string[] }> = [];
  for (const line of lines) {
    const ordered = /^\d+\.\s+/.test(line);
    const unordered = /^[-*•]\s+/.test(line);
    const type = ordered ? 'ordered' : unordered ? 'unordered' : 'paragraph';
    const previous = blocks.at(-1);
    if (previous?.type === type && type !== 'paragraph') previous.lines.push(line.replace(/^(?:\d+\.|[-*•])\s+/, ''));
    else blocks.push({ type, lines: [line.replace(/^(?:\d+\.|[-*•])\s+/, '')] });
  }
  return <div className="space-y-2.5">{blocks.map((block, index) => {
    if (block.type === 'ordered') return <ol key={index} className="list-decimal space-y-2 pl-5">{block.lines.map((line, itemIndex) => <li key={itemIndex} className="pl-1">{formatInline(line)}</li>)}</ol>;
    if (block.type === 'unordered') return <ul key={index} className="list-disc space-y-2 pl-5">{block.lines.map((line, itemIndex) => <li key={itemIndex} className="pl-1">{formatInline(line)}</li>)}</ul>;
    const heading = block.lines[0].match(/^#{1,3}\s+(.+)$/);
    if (heading) return <h3 key={index} className="font-semibold text-slate-900">{formatInline(heading[1])}</h3>;
    return <p key={index}>{formatInline(block.lines[0])}</p>;
  })}</div>;
}

export function CoachPage() {
  const [skillGap, setSkillGap] = useState<SkillGap | null>(null);
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [conversations, setConversations] = useState<Awaited<ReturnType<typeof coachApi.listConversations>>>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [coachStatus, setCoachStatus] = useState('');
  const [expandedTaskId, setExpandedTaskId] = useState('');

  const refreshCoach = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [gaps, activeRoadmap, history] = await Promise.all([
        coachApi.getSkillGap(), modulesApi.getActiveRoadmap(), coachApi.listConversations(),
      ]);
      setSkillGap(gaps);
      setRoadmap(activeRoadmap);
      setConversations(history);
      if (history[0]) setConversation(await coachApi.getConversation(history[0].id));
      else setConversation(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Coach data could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refreshCoach(); }, [refreshCoach]);

  async function createRoadmap() {
    setError('');
    try {
      setRoadmap(await coachApi.generateRoadmap());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'A roadmap could not be created.');
    }
  }

  async function toggleTask(taskId: string) {
    try {
      await modulesApi.toggleRoadmapTask(taskId);
      setRoadmap(await modulesApi.getActiveRoadmap());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Roadmap progress could not be saved.');
    }
  }

  async function openConversation(id: string) {
    try {
      setConversation(await coachApi.getConversation(id));
      setCoachStatus('');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Conversation could not be loaded.');
    }
  }

  async function sendMessage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = message.trim();
    if (!text || sending) return;
    setSending(true);
    setError('');
    try {
      const result = await coachApi.chat(text, conversation?.id);
      setMessage('');
      setCoachStatus(result.ai_status === 'ai_generated'
        ? 'Response ready.'
        : 'Your message was saved. A response is temporarily unavailable; you can retry later.');
      setConversation(await coachApi.getConversation(result.conversation_id));
      const history = await coachApi.listConversations();
      setConversations(history);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Your message could not be sent.');
    } finally {
      setSending(false);
    }
  }

  if (loading) return <div className="rounded-xl border bg-white p-8 text-slate-600">Loading your coaching workspace…</div>;

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-violet-100 bg-gradient-to-br from-violet-50 via-white to-indigo-50 p-6 text-slate-900 shadow-sm shadow-violet-950/5 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-800">Career coach</p>
        <h1 className="mt-2 text-3xl font-bold text-slate-950">Build a grounded plan for your next move</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Recommendations use your profile and published learning content. Self-reported skills are kept separate from assessed evidence.</p>
      </header>
      {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}

      <div className="grid gap-5 xl:grid-cols-2">
        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3"><Target className="h-5 w-5 text-violet-700" /><div><h2 className="font-semibold text-slate-900">Skill analysis</h2><p className="text-xs text-slate-500">A profile-based view of your current strengths and next steps</p></div></div>
          <p className="mt-4 text-sm leading-6 text-slate-700">{skillGap?.coach_summary}</p>
          {!!skillGap?.self_reported_skills.length && <div className="mt-4"><h3 className="text-sm font-semibold">Your self-reported skills</h3><div className="mt-2 flex flex-wrap gap-2">{skillGap.self_reported_skills.map((skill) => <span key={skill} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">{skill}</span>)}</div></div>}
          {!!skillGap?.strong_skills.length && <div className="mt-4"><h3 className="text-sm font-semibold">Strengths to build on</h3><p className="mt-1 text-sm text-slate-700">{skillGap.strong_skills.join(', ')}</p></div>}
          {!!skillGap?.weak_skills.length && <div className="mt-4"><h3 className="text-sm font-semibold">Areas to strengthen</h3><p className="mt-1 text-sm text-slate-700">{skillGap.weak_skills.join(', ')}</p></div>}
          {!!skillGap?.missing_skills.length && <div className="mt-4"><h3 className="text-sm font-semibold">Potential role requirements</h3><p className="mt-1 text-sm text-slate-700">{skillGap.missing_skills.join(', ')}</p><p className="mt-1 text-xs text-slate-500">These are recommendations based on available role content, not proof that you lack a skill.</p></div>}
          {!!skillGap?.learning_priorities.length && <div className="mt-4 space-y-2">{skillGap.learning_priorities.map((item) => <div key={`${item.priority}-${item.skill_or_topic}`} className="rounded-lg bg-violet-50 p-3 text-sm"><strong>{item.priority}. {item.skill_or_topic}</strong><p className="mt-1">{item.actionable_recommendation}</p></div>)}</div>}
          {!!skillGap?.skill_evidence && <details className="mt-4 text-xs text-slate-500"><summary className="cursor-pointer">Evidence and provenance</summary><ul className="mt-2 space-y-1">{Object.entries(skillGap.skill_evidence).map(([skill, evidence]) => <li key={skill}>{skill}: {evidence}</li>)}</ul></details>}
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3"><BookOpen className="h-5 w-5 text-violet-700" /><div><h2 className="font-semibold text-slate-900">Learning roadmap</h2><p className="text-xs text-slate-500">Published modules matched to your industry, target role, and self-reported skills</p></div></div>
          {!roadmap ? <div className="mt-4 rounded-lg border border-dashed p-5 text-sm text-slate-600"><p>No active roadmap yet. It can be built from existing published modules.</p><button onClick={() => void createRoadmap()} className="mt-3 rounded-lg bg-violet-700 px-4 py-2 font-semibold text-white">Build roadmap</button></div> : <>
            <h3 className="mt-4 text-lg font-semibold">{roadmap.title}</h3><p className="mt-1 text-sm text-slate-600">{(roadmap.description ?? '').split('\n')[0]}</p>
            <ol className="mt-4 space-y-2">{roadmap.tasks.map((task) => { const expanded = expandedTaskId === task.id; return <li key={task.id} className="rounded-xl border border-slate-200 bg-slate-50/70 p-3"><div className="flex items-start gap-3"><input aria-label={`Complete ${task.title}`} type="checkbox" checked={task.is_completed} onChange={() => void toggleTask(task.id)} className="mt-1 h-4 w-4 accent-violet-700" /><div className="min-w-0 flex-1"><button type="button" aria-expanded={expanded} onClick={() => setExpandedTaskId(expanded ? '' : task.id)} className="flex w-full items-center justify-between gap-3 text-left font-medium text-slate-900"><span>{task.title}</span><ChevronDown className={`h-4 w-4 shrink-0 text-violet-700 transition-transform ${expanded ? 'rotate-180' : ''}`} /></button>{expanded && <div className="mt-2 border-t border-slate-200 pt-2">{task.description && <p className="text-sm leading-6 text-slate-600">{task.description}</p>}{task.module_id ? <Link to={`/modules?moduleId=${encodeURIComponent(task.module_id)}`} className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-violet-800 underline">Open learning module <ArrowRight className="h-4 w-4" /></Link> : <p className="mt-2 text-xs text-slate-500">Suggested learning step based on your profile.</p>}</div>}</div></div></li>; })}</ol>
          </>}
        </article>
      </div>

      <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm shadow-slate-200/60">
        <div className="flex flex-col gap-4 border-b border-slate-200 bg-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"><div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-700"><Bot className="h-5 w-5" /></span><div><h2 className="font-semibold text-slate-900">Career coach</h2><p className="mt-0.5 text-xs text-slate-500">Your private space for career and learning guidance</p></div></div>
          <div className="flex flex-wrap items-center gap-2">{conversation && <button type="button" onClick={() => { setConversation(null); setCoachStatus(''); }} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">New conversation</button>}{conversations.length > 0 && <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600"><span>History</span><select aria-label="Choose conversation" className="max-w-60 bg-transparent text-sm font-medium text-slate-900 outline-none" value={conversation?.id ?? ''} onChange={(event) => event.target.value ? void openConversation(event.target.value) : setConversation(null)}><option value="">New conversation</option>{conversations.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}</div>
        </div>
        <div className="max-h-[34rem] min-h-64 space-y-5 overflow-y-auto bg-gradient-to-b from-slate-50/80 to-white p-4 sm:p-6" aria-live="polite">
          {conversation?.messages.map((item) => <div key={item.id} className={`flex ${item.sender === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`w-fit max-w-[92%] rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm sm:max-w-[82%] ${item.sender === 'user' ? 'rounded-br-md bg-violet-700 text-white' : 'rounded-bl-md border border-slate-200 bg-white text-slate-700'}`}><p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.12em] opacity-65">{item.sender === 'user' ? 'You' : item.sender === 'assistant' ? 'Career coach' : 'System'}</p><CoachMessageText text={item.message_text} /></div></div>)}
          {!conversation?.messages.length && <div className="mx-auto max-w-lg py-10 text-center"><span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-100 text-violet-700"><Bot className="h-6 w-6" /></span><h3 className="mt-4 font-semibold text-slate-900">What would you like to work on?</h3><p className="mt-1 text-sm leading-6 text-slate-500">Ask about your target role, a skill you want to build, or how to prepare for an interview.</p></div>}
          {sending && <p role="status" className="text-xs text-slate-500">The coach is preparing a response…</p>}
          {coachStatus && <p role="status" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">{coachStatus}</p>}
        </div>
        <form onSubmit={(event) => void sendMessage(event)} className="flex flex-col gap-3 border-t border-slate-200 bg-white p-4 sm:flex-row sm:items-end sm:px-6 sm:py-5"><label htmlFor="coach-message" className="block min-w-0 flex-1 text-xs font-semibold text-slate-700"><RequiredLabel>Message</RequiredLabel><textarea id="coach-message" aria-label="Message the coach" rows={3} maxLength={10000} value={message} onChange={(event) => setMessage(event.target.value)} className="mt-2 block min-h-24 w-full resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-normal leading-6 text-slate-800 shadow-sm outline-none placeholder:text-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-100" placeholder="Ask a question or tell me what you’re working toward…" /><span className="mt-1 block text-right text-[11px] font-normal text-slate-400">{message.length}/10,000</span></label><button type="submit" disabled={!message.trim() || sending} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-violet-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-800 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 sm:mb-6 sm:w-auto">{sending ? 'Sending…' : 'Send message'} <Send className="h-4 w-4" /></button></form>
      </article>
    </section>
  );
}
