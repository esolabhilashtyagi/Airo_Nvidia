import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, Check, Clock3, FileText, LoaderCircle, LockKeyhole, Save, Trash2, X } from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { resumesApi } from '../../api/resumes';
import { paymentsApi } from '../../api/services';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { StatusBadge } from '../../components/common/StatusBadge';
import { calculateResumeReadiness } from '../../utils/resumeReadiness';
import type { ResumeAnalysis, ResumeDetail, ResumeParsedData, ResumeSuggestion } from '../../types';

type Tab = 'overview' | 'analysis' | 'enhancement' | 'versions';

declare global {
  interface Window {
    Razorpay?: new (options: {
      key: string; amount: number; currency: string; name: string; description: string; order_id: string;
      handler: (result: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) => void;
      modal?: { ondismiss?: () => void };
      theme?: { color: string };
    }) => { open: () => void; on: (event: string, callback: (result: unknown) => void) => void };
  }
}

export function ResumeDetailPage() {
  const { resumeId = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [resume, setResume] = useState<ResumeDetail | null>(null);
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null);
  const [parsedJson, setParsedJson] = useState('');
  const [editedSuggestions, setEditedSuggestions] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [atsAccess, setAtsAccess] = useState<Awaited<ReturnType<typeof paymentsApi.atsAccess>> | null>(null);
  const [checkoutWorking, setCheckoutWorking] = useState(false);

  const tab: Tab = location.pathname.endsWith('/analysis') ? 'analysis'
    : location.pathname.endsWith('/enhancement') ? 'enhancement'
      : location.pathname.endsWith('/versions') ? 'versions' : 'overview';

  const load = useCallback(async (preserveError = false) => {
    setLoading(true);
    if (!preserveError) setError(null);
    try {
      const [resumeData, analysisData] = await Promise.all([
        resumesApi.getResume(resumeId),
        resumesApi.getAnalysis(resumeId),
      ]);
      setResume(resumeData);
      setAnalysis(analysisData);
      setParsedJson(JSON.stringify(resumeData.parsed_data, null, 2));
    } catch (err) {
      if (!preserveError) setError(err instanceof Error ? err.message : 'Could not load this resume.');
    } finally {
      setLoading(false);
    }
  }, [resumeId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void paymentsApi.atsAccess().then(setAtsAccess).catch(() => setAtsAccess(null)); }, []);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setWorking(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      await load();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'The request could not be completed.';
      await load(true);
      setError(message);
    } finally {
      setWorking(false);
    }
  };

  const saveExtractedData = async () => {
    let parsed: ResumeParsedData;
    try {
      parsed = JSON.parse(parsedJson) as ResumeParsedData;
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('The root value must be an object.');
    } catch (err) {
      setError(`Check the extracted data JSON: ${err instanceof Error ? err.message : 'invalid JSON'}`);
      return;
    }
    await run(() => resumesApi.updateParsedData(resumeId, parsed), 'Your corrections were saved as a new resume version.');
  };

  const reviewSuggestion = async (suggestion: ResumeSuggestion, action: 'accept' | 'reject') => {
    await run(() => resumesApi.handleSuggestionAction(
      suggestion.id,
      action,
      action === 'accept' ? (editedSuggestions[suggestion.id] ?? suggestion.suggested_text) : undefined,
    ), action === 'accept' ? 'Suggestion accepted and saved as a new version.' : 'Suggestion rejected.');
  };

  const deleteResume = async () => {
    if (!window.confirm(`Delete “${resume?.file_name}” and its stored resume data? This cannot be undone.`)) return;
    setWorking(true);
    setError(null);
    try {
      await resumesApi.deleteResume(resumeId);
      navigate('/resume');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Resume deletion failed.');
      setWorking(false);
    }
  };

  const unlockPaidAts = async () => {
    setCheckoutWorking(true);
    setError(null);
    try {
      const order = await paymentsApi.createAtsOrder();
      if (!window.Razorpay) {
        await new Promise<void>((resolve, reject) => {
          // A previously failed script element does not fire onload on retry.
          document.querySelector<HTMLScriptElement>('script[data-razorpay-checkout]')?.remove();
          const script = document.createElement('script');
          script.src = 'https://checkout.razorpay.com/v1/checkout.js';
          script.async = true;
          script.dataset.razorpayCheckout = 'true';
          script.onload = () => resolve();
          script.onerror = () => {
            script.remove();
            reject(new Error('Razorpay Checkout could not be loaded. Check your network and retry.'));
          };
          document.body.appendChild(script);
        });
      }
      if (!window.Razorpay) throw new Error('Razorpay Checkout is unavailable in this browser.');
      const checkout = new window.Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: 'AAIRO Education Platform',
        description: 'Paid ATS resume review access',
        order_id: order.order_id,
        theme: { color: '#6D28D9' },
        handler: async (payment) => {
          try {
            await paymentsApi.verifyAtsPayment(payment);
            setAtsAccess(await paymentsApi.atsAccess());
            setNotice('Payment verified. Paid ATS review access is now active.');
          } catch (caught) {
            setError(caught instanceof Error ? caught.message : 'Payment verification is pending. Retry shortly.');
            setAtsAccess(await paymentsApi.atsAccess().catch(() => null));
          } finally {
            setCheckoutWorking(false);
          }
        },
        modal: { ondismiss: () => setCheckoutWorking(false) },
      });
      checkout.on('payment.failed', () => {
        setError('Payment did not complete. No ATS access was granted. You can retry.');
        setCheckoutWorking(false);
      });
      checkout.open();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Paid ATS checkout could not be started.');
      setCheckoutWorking(false);
    }
  };

  if (loading) return <LoadingSpinner size="lg" message="Loading resume details..." />;
  if (error && !resume) return <div role="alert" className="space-y-4 rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800"><p>{error}</p><Link to="/resume" className="font-semibold underline">Back to my resumes</Link></div>;
  if (!resume) return null;

  const analysisReady = Boolean(analysis && analysis.status === 'analysis_completed');
  const enhancedDraft = typeof resume.parsed_data.enhanced_text === 'string' ? resume.parsed_data.enhanced_text : '';
  const resumeReadiness = resume.parsing_status === 'extracted'
    ? calculateResumeReadiness(enhancedDraft || resume.raw_text || '', resume.parsed_data)
    : null;
  const sections: { key: Tab; label: string; path: string }[] = [
    { key: 'overview', label: 'Extracted details', path: `/resume/${resumeId}` },
    { key: 'analysis', label: 'Analysis', path: `/resume/${resumeId}/analysis` },
    { key: 'enhancement', label: 'Enhancements', path: `/resume/${resumeId}/enhancement` },
    { key: 'versions', label: 'Version history', path: `/resume/${resumeId}/versions` },
  ];
  const downloadEnhancedDraft = () => {
    if (!enhancedDraft) return;
    const blobUrl = URL.createObjectURL(new Blob([enhancedDraft], { type: 'text/plain;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = blobUrl;
    anchor.download = `${resume.file_name.replace(/\.[^.]+$/, '')}_enhanced-draft.txt`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 0);
  };

  return (
    <div className="space-y-6">
      <Link to="/resume" className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-violet-700"><ArrowLeft className="h-4 w-4" /> My resumes</Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600"><FileText className="h-5 w-5" /></span>
          <div className="min-w-0">
            <h1 className="break-all text-xl font-bold text-slate-900">{resume.file_name}</h1>
            <div className="mt-2 flex flex-wrap gap-2"><StatusBadge status={resume.parsing_status} /><StatusBadge status={resume.analysis_status} /></div>
          </div>
        </div>
        <button type="button" onClick={() => void deleteResume()} disabled={working} className="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-white px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-60"><Trash2 className="h-4 w-4" /> Delete resume</button>
      </div>

      {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
      {notice && <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}

      <nav aria-label="Resume sections" className="flex gap-1 overflow-x-auto border-b border-slate-200">
        {sections.map((item) => <Link key={item.key} to={item.path} className={`whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium ${tab === item.key ? 'border-violet-600 text-violet-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>{item.label}</Link>)}
      </nav>

      {tab === 'overview' && <div className="space-y-5">
        {resume.parsing_status !== 'extracted' && <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-purple-200 bg-purple-50 p-4 text-sm text-purple-900">
          <span>{resume.extraction_error || 'Text extraction is not complete.'}</span>
          <button type="button" disabled={working} onClick={() => void run(() => resumesApi.extractResume(resumeId), 'Resume text was extracted.')} className="rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-violet-800 disabled:opacity-60">{working ? 'Retrying…' : 'Retry extraction'}</button>
        </div>}

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="font-semibold text-slate-900">Extracted information</h2><p className="mt-1 text-xs text-slate-500">Edit fields if the parser made a mistake. Your upload stays unchanged.</p></div>
            <span className="text-xs text-slate-500">Extraction confidence indicator: {Math.round(resume.extraction_confidence * 100)}% · rule-based signal, not a probability</span>
          </div>
          {resume.parsing_status === 'extracted' ? <>
            <textarea aria-label="Editable extracted resume data in JSON" value={parsedJson} onChange={(event) => setParsedJson(event.target.value)} spellCheck={false} className="mt-4 min-h-80 w-full rounded-lg border border-slate-300 bg-slate-50 p-3 font-mono text-xs leading-5 text-slate-800 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100" />
            <button type="button" onClick={() => void saveExtractedData()} disabled={working || parsedJson === JSON.stringify(resume.parsed_data, null, 2)} className="mt-3 inline-flex items-center gap-2 rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800 disabled:opacity-50"><Save className="h-4 w-4" /> Save corrections</button>
          </> : <p className="mt-4 text-sm text-slate-500">Extracted fields will be available here after a successful retry.</p>}
        </div>

        {resume.raw_text && <details className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><summary className="cursor-pointer text-sm font-semibold text-slate-800">Preview extracted text</summary><pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-4 text-xs leading-5 text-slate-700">{resume.raw_text}</pre></details>}
      </div>}

      {tab === 'analysis' && <div className="space-y-5">
        <section className={`rounded-xl border p-5 ${atsAccess?.has_access ? 'border-emerald-200 bg-emerald-50' : 'border-violet-200 bg-violet-50/60'}`}>
          <div className="flex flex-wrap items-center justify-between gap-4"><div><div className="flex items-center gap-2"><LockKeyhole className="h-5 w-5 text-violet-700" /><h2 className="font-semibold text-slate-900">Paid job-specific ATS review</h2></div><p className="mt-1 text-sm text-slate-600">Compare this resume against a job description and get a transparent keyword and section match report. This is an estimate, not an employer ATS score or hiring guarantee.</p>{atsAccess?.has_access ? <p className="mt-2 text-sm font-semibold text-emerald-800">Access active for this account</p> : atsAccess?.checkout_configured ? <p className="mt-2 text-sm font-medium text-slate-700">One-time access: {new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(atsAccess.price_paise / 100)}</p> : <p className="mt-2 text-xs text-slate-600">Checkout is not configured yet. Admin must set a price and Razorpay keys before candidates can purchase.</p>}</div>{!atsAccess?.has_access && <button type="button" onClick={() => void unlockPaidAts()} disabled={checkoutWorking || !atsAccess?.checkout_configured} className="rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">{checkoutWorking ? 'Opening checkout…' : 'Unlock ATS review'}</button>}</div>
        </section>
        {resumeReadiness && <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Resume-only assessment · no job description needed</p><h2 className="mt-1 text-lg font-semibold text-slate-900">Resume structure check</h2><p className="mt-1 max-w-2xl text-sm text-slate-600">A repeatable check of contact details, section structure, listed skills, measurable evidence, and extracted-text readability.</p></div><div className="text-right"><p className="text-4xl font-bold text-violet-700">{resumeReadiness.score}<span className="text-base font-semibold text-slate-500">/100</span></p><p className="text-xs text-slate-500">Heuristic checklist</p></div></div>
          <div className="grid gap-3 md:grid-cols-2">{resumeReadiness.checks.map((check) => <div key={check.label} className="rounded-lg bg-slate-50 p-3"><div className="flex justify-between gap-3 text-sm"><span className="font-medium text-slate-800">{check.label}</span><span className="font-semibold text-slate-700">{check.score}/{check.maxScore}</span></div><div className="mt-2 h-1.5 rounded-full bg-slate-200"><div className="h-full rounded-full bg-violet-600" style={{ width: `${check.score / check.maxScore * 100}%` }} /></div><p className="mt-1.5 text-xs text-slate-600">{check.evidence}</p></div>)}</div>
          <div><h3 className="text-sm font-semibold text-slate-900">Ways to improve</h3>{resumeReadiness.improvements.length ? <ul className="mt-2 list-inside list-disc space-y-1.5 text-sm text-slate-700">{resumeReadiness.improvements.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-sm text-slate-700">These checks found no immediate structural gaps. Tailor your resume to each role for a job-specific keyword comparison.</p>}</div>
          <p className="border-t border-slate-200 pt-3 text-xs leading-5 text-slate-500">This 100-point checklist is calculated from extracted text. It is not an ATS vendor score, a job-match score, a hiring probability, or a guarantee. Employer systems vary. Recommendations never add unsupported claims.</p>
        </section>}
        {!resumeReadiness && resume.parsing_status === 'extracted' && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">A resume-only readiness estimate is unavailable because no readable extracted resume text is available. Verify the extraction before relying on resume checks.</p>}
        {!analysisReady && <div className="flex justify-end">
          <button type="button" onClick={() => void run(() => resumesApi.analyzeResume(resumeId), 'Role-aware analysis completed.')} disabled={working || resume.parsing_status !== 'extracted'} className="inline-flex items-center gap-2 rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-50">{working && <LoaderCircle className="h-4 w-4 animate-spin" />}{working ? 'Analyzing…' : 'Analyze resume'}</button>
        </div>}
        {analysisReady && analysis && <>
          {resume.analysis_error && <div role="status" className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">{resume.analysis_error}</div>}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-5"><h2 className="font-semibold text-emerald-950">Strengths</h2><ul className="mt-3 list-inside list-disc space-y-1.5 text-sm text-emerald-900">{analysis.strengths.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></div>
            <div className="rounded-xl border border-purple-200 bg-purple-50/60 p-5"><h2 className="font-semibold text-purple-950">Areas to improve</h2><ul className="mt-3 list-inside list-disc space-y-1.5 text-sm text-purple-900">{analysis.weaknesses.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="font-semibold text-slate-900">Scoring explanation</h2><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{analysis.summary_analysis}</p>{analysis.improvement_opportunities.length > 0 && <><h3 className="mt-5 text-sm font-semibold text-slate-900">Suggested next steps</h3><ul className="mt-2 list-inside list-disc space-y-1.5 text-sm text-slate-700">{analysis.improvement_opportunities.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ul></>}{analysis.missing_keywords.length > 0 && <><h3 className="mt-5 text-sm font-semibold text-slate-900">Role-related terms to review</h3><p className="mt-1 text-xs text-slate-500">These are ideas to check against the job you want. Add a term only when it truthfully reflects your experience.</p><div className="mt-2 flex flex-wrap gap-2">{analysis.missing_keywords.map((word) => <span key={word} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700">{word}</span>)}</div></>}</div>
        </>}
      </div>}

      {tab === 'enhancement' && <div className="space-y-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold text-slate-900">Resume enhancements</h2><p className="mt-1 max-w-3xl text-sm text-slate-500">Improve clarity and grammar with suggestions grounded in your resume. Review each change; unsupported claims are rejected.</p></div><button type="button" onClick={() => void run(() => resumesApi.enhanceResume(resumeId), 'Source-checked enhancement suggestions generated.')} disabled={working || resume.parsing_status !== 'extracted'} className="rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">{analysisReady ? 'Refresh suggestions' : 'Generate suggestions'}</button></div></div>
        {enhancedDraft && <section className="rounded-xl border border-violet-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold text-slate-900">Your revised text draft</h3><p className="mt-1 text-xs text-slate-600">Accepted edits are applied here. The original uploaded file and extracted source remain unchanged.</p></div><button type="button" onClick={downloadEnhancedDraft} className="rounded-lg border border-violet-300 px-3 py-2 text-sm font-semibold text-violet-800 hover:bg-violet-50">Download enhanced draft (.txt)</button></div><details className="mt-4"><summary className="cursor-pointer text-sm font-medium text-violet-800">Preview revised resume text</summary><pre className="mt-3 max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-700">{enhancedDraft}</pre></details><p className="mt-3 text-xs text-slate-500">Resume-only readiness checks use this revised draft after you accept edits. Open the Analysis tab to review the current estimate.</p></section>}
        {!analysisReady ? <p className="rounded-lg border border-purple-200 bg-purple-50 p-4 text-sm text-purple-900">Suggestions are unavailable. Try again later.</p> : analysis?.suggestions.length ? analysis.suggestions.map((suggestion) => <SuggestionCard key={suggestion.id} suggestion={suggestion} working={working} editedText={editedSuggestions[suggestion.id] ?? suggestion.suggested_text} onEdit={(text) => setEditedSuggestions((previous) => ({ ...previous, [suggestion.id]: text }))} onReview={reviewSuggestion} />) : <p className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-500">No suggestions for this resume.</p>}
      </div>}

      {tab === 'versions' && <div className="space-y-3">
        <h2 className="text-base font-semibold text-slate-900">Saved versions</h2>
        {[...resume.versions].sort((a, b) => b.version_number - a.version_number).map((version) => <article key={version.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2"><Clock3 className="h-4 w-4 text-violet-700" /><h3 className="font-semibold text-slate-900">Version {version.version_number}</h3></div><time className="text-xs text-slate-500">{new Date(version.created_at).toLocaleString()}</time></div><p className="mt-1 text-sm text-slate-600">{version.change_summary || 'Saved resume version'}</p><details className="mt-3"><summary className="cursor-pointer text-xs font-semibold text-violet-700">View saved content</summary><pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-700">{JSON.stringify(version.content, null, 2)}</pre></details></article>)}
      </div>}
    </div>
  );
}

function SuggestionCard({ suggestion, working, editedText, onEdit, onReview }: {
  suggestion: ResumeSuggestion;
  working: boolean;
  editedText: string;
  onEdit: (text: string) => void;
  onReview: (suggestion: ResumeSuggestion, action: 'accept' | 'reject') => Promise<void>;
}) {
  return <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold text-slate-900">{suggestion.category}</h3><StatusBadge status={suggestion.status} /></div>
    {suggestion.original_text && <div className="mt-4 grid gap-3 md:grid-cols-2"><div className="rounded-lg bg-slate-50 p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Original from resume</p><p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{suggestion.original_text}</p></div><div className="rounded-lg bg-violet-50 p-3"><label htmlFor={`suggestion-${suggestion.id}`} className="text-[11px] font-semibold uppercase tracking-wide text-violet-800">Proposed wording — edit before accepting</label><textarea id={`suggestion-${suggestion.id}`} disabled={suggestion.status !== 'pending'} value={editedText} onChange={(event) => onEdit(event.target.value)} className="mt-2 min-h-20 w-full resize-y bg-transparent text-sm leading-5 text-slate-800 focus:outline-none disabled:opacity-70" /></div></div>}
    {suggestion.supporting_context && <p className="mt-3 text-xs text-slate-500">Source context: “{suggestion.supporting_context}”</p>}
    {suggestion.reason && <p className="mt-3 text-sm leading-5 text-slate-600">{suggestion.reason}</p>}
    {suggestion.status === 'pending' && <div className="mt-4 flex gap-2"><button type="button" disabled={working} onClick={() => void onReview(suggestion, 'accept')} className="inline-flex items-center gap-1.5 rounded-lg bg-violet-700 px-3 py-2 text-xs font-semibold text-white hover:bg-violet-800 disabled:opacity-50"><Check className="h-3.5 w-3.5" /> Accept and save version</button><button type="button" disabled={working} onClick={() => void onReview(suggestion, 'reject')} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"><X className="h-3.5 w-3.5" /> Reject</button></div>}
  </article>;
}
