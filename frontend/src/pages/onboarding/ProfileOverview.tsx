import { useEffect, useState, type ReactNode } from 'react';
import {
  ArrowDownToLine, BriefcaseBusiness, Building2, CalendarDays, CheckCircle2, GraduationCap,
  PencilLine, Sparkles, Target, UserRound, LockKeyhole,
} from 'lucide-react';
import { resumesApi } from '../../api/resumes';
import { paymentsApi } from '../../api/services';
import type { CandidateProfile } from '../../types';
import { CandidateAvatar } from '../../components/common/CandidateAvatar';

type ResumeTemplate = 'modern' | 'classic' | 'compact';
declare global {
  interface Window {
    Razorpay?: new (options: { key: string; amount: number; currency: string; name: string; description: string; order_id: string; handler: (result: { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) => void; modal?: { ondismiss?: () => void }; theme?: { color: string } }) => { open: () => void; on: (event: string, callback: (result: unknown) => void) => void };
  }
}
const resumeTemplates: { id: ResumeTemplate; name: string; description: string; accent: string; }[] = [
  { id: 'modern', name: 'Professional', description: 'ATS-friendly single column with a crisp name and section hierarchy.', accent: 'bg-violet-600' },
  { id: 'classic', name: 'Academic', description: 'Formal typography and centered contact header for education-focused profiles.', accent: 'bg-slate-500' },
  { id: 'compact', name: 'Early career', description: 'Compact spacing to keep skills, education, and projects easy to scan.', accent: 'bg-violet-300' },
];

function experienceLabel(months: number, isGraduate: boolean) {
  if (months <= 0) return isGraduate ? 'Early career' : 'Not added';
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;
  return [years ? `${years} ${years === 1 ? 'year' : 'years'}` : '', remainingMonths ? `${remainingMonths} months` : '']
    .filter(Boolean).join(' ');
}

function formatSubcategory(value: string | null | undefined, isGraduate: boolean) {
  const label = (value || (isGraduate ? 'recent_graduate' : 'experienced_professional')).replaceAll('_', ' ');
  return label.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function DetailCard({ icon: Icon, title, children, className = '' }: {
  icon: typeof UserRound;
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return <article className={`rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_8px_26px_-20px_rgba(30,41,59,0.45)] sm:p-6 ${className}`}>
    <div className="mb-4 flex items-center gap-3">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-violet-50 text-violet-700"><Icon className="h-5 w-5" /></span>
      <h2 className="font-semibold tracking-tight text-slate-900">{title}</h2>
    </div>
    {children}
  </article>;
}

export function ProfileOverview({ profile, onEdit }: { profile: CandidateProfile; onEdit: () => void }) {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [resumeTemplate, setResumeTemplate] = useState<ResumeTemplate>('modern');
  const [templateAccess, setTemplateAccess] = useState<{ has_access: boolean; price_paise: number; checkout_configured: boolean } | null>(null);
  const [checkoutWorking, setCheckoutWorking] = useState(false);
  useEffect(() => { void paymentsApi.resumeTemplateAccess().then(setTemplateAccess).catch(() => setTemplateAccess(null)); }, []);
  const isGraduate = profile.candidate_type === 'student_fresher';

  async function downloadResume() {
    setGenerating(true);
    setError('');
    try {
      const { blob, filename } = await resumesApi.generateFromProfile(templateAccess?.has_access ? resumeTemplate : 'standard', 'pdf');
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Your profile resume could not be generated.');
    } finally {
      setGenerating(false);
    }
  }

  async function unlockTemplates() {
    setCheckoutWorking(true);
    setError('');
    try {
      const order = await paymentsApi.createResumeTemplateOrder();
      if (!window.Razorpay) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement('script');
          script.src = 'https://checkout.razorpay.com/v1/checkout.js';
          script.onload = () => resolve();
          script.onerror = () => reject(new Error('Checkout could not be loaded. Please retry.'));
          document.body.appendChild(script);
        });
      }
      if (!window.Razorpay) throw new Error('Checkout is unavailable in this browser.');
      const checkout = new window.Razorpay({
        key: order.key_id, amount: order.amount_paise, currency: order.currency, name: 'AAIRO',
        description: 'One-time premium resume layouts', order_id: order.order_id,
        handler: async (payment) => {
          try {
            await paymentsApi.verifyResumeTemplatePayment(payment);
            setTemplateAccess(await paymentsApi.resumeTemplateAccess());
          } catch (caught) { setError(caught instanceof Error ? caught.message : 'Payment verification failed.'); }
          finally { setCheckoutWorking(false); }
        },
        modal: { ondismiss: () => setCheckoutWorking(false) }, theme: { color: '#6d28d9' },
      });
      checkout.on('payment.failed', () => { setError('Payment was not completed. You can retry when ready.'); setCheckoutWorking(false); });
      checkout.open();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Checkout could not be opened.');
      setCheckoutWorking(false);
    }
  }

  return <section className="mx-auto max-w-5xl space-y-6 sm:space-y-8">
    <header className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
      <div>
        <p className="text-sm font-semibold tracking-wide text-violet-700">Your career profile</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Candidate information</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">Review your details or build a resume from your saved profile.</p>
      </div>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={onEdit} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-violet-300 hover:bg-violet-50/60">
          <PencilLine className="h-4 w-4" /> Edit profile
        </button>
        <button type="button" onClick={() => void downloadResume()} disabled={generating} className="inline-flex items-center gap-2 rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-violet-900/15 transition hover:bg-violet-800 disabled:cursor-wait disabled:opacity-60">
          <ArrowDownToLine className="h-4 w-4" /> {generating ? 'Preparing PDF…' : 'Download PDF'}
        </button>
      </div>
    </header>

    {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}

    <section aria-labelledby="resume-template-heading" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 id="resume-template-heading" className="font-semibold text-slate-900">Resume PDF</h2><p className="mt-1 text-sm text-slate-500">A clean, ATS-friendly document made from your saved profile.</p></div><span className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700">Standard format · PDF</span></div>
      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4"><p className="font-semibold text-slate-900">Standard</p><p className="mt-1 text-sm text-slate-600">Professional single-column layout with your summary, education, experience, skills, projects, and certifications.</p></div>
      {!templateAccess?.has_access && <div className="mt-4 rounded-xl border border-violet-200 bg-violet-50/50 p-4"><div className="flex flex-wrap items-start justify-between gap-4"><div><h3 className="flex items-center gap-2 font-semibold text-slate-900"><LockKeyhole className="h-4 w-4 text-violet-700" />Premium layouts</h3><p className="mt-1 text-sm text-slate-600">Unlock additional resume designs with a one-time purchase.</p>{templateAccess?.checkout_configured ? <p className="mt-2 text-sm font-semibold text-violet-900">{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(templateAccess.price_paise / 100)} · one-time</p> : <p className="mt-2 text-xs text-slate-600">Purchases are not available yet.</p>}</div><button type="button" onClick={() => void unlockTemplates()} disabled={checkoutWorking || !templateAccess?.checkout_configured} className="rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">{checkoutWorking ? 'Opening checkout…' : 'Unlock layouts'}</button></div></div>}
      {templateAccess?.has_access && <>
      <div className="mt-4 flex items-center justify-between"><div><h3 className="font-semibold text-slate-900">Choose a premium layout</h3><p className="mt-1 text-sm text-slate-500">Select a layout and download it as a PDF.</p></div><span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">Unlocked</span></div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">{resumeTemplates.map((template) => <button key={template.id} type="button" aria-pressed={resumeTemplate === template.id} onClick={() => setResumeTemplate(template.id)} className={`group rounded-xl border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-violet-300 ${resumeTemplate === template.id ? 'border-violet-500 bg-violet-50/50 shadow-sm' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'}`}>
        <div aria-hidden="true" className="flex h-24 gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow-inner"><span className={`w-1.5 shrink-0 rounded-full ${template.accent}`} /><div className={`flex-1 ${template.id === 'classic' ? 'text-center' : ''}`}><span className={`block h-2 w-2/3 rounded ${template.accent} ${template.id === 'classic' ? 'mx-auto' : ''}`} /><span className={`mt-2 block h-1 w-1/2 rounded bg-slate-300 ${template.id === 'classic' ? 'mx-auto' : ''}`} /><span className="mt-3 block h-1 w-full rounded bg-slate-200" /><span className="mt-1.5 block h-1 w-5/6 rounded bg-slate-200" /><span className="mt-2 block h-1 w-1/3 rounded bg-slate-300" /></div></div>
        <span className="mt-3 flex items-center justify-between gap-2"><span className="text-sm font-semibold text-slate-900">{template.name}</span><span className={`h-4 w-4 rounded-full border ${resumeTemplate === template.id ? 'border-violet-600 bg-violet-600 ring-2 ring-violet-100' : 'border-slate-300 bg-white'}`} /></span><span className="mt-1 block text-xs leading-5 text-slate-500">{template.description}</span>
      </button>)}</div></>}
    </section>

    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm shadow-slate-900/[0.03]">
      <div className="h-1 bg-violet-700" />
      <div className="p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-5">
          <div className="flex min-w-0 items-center gap-4">
            <CandidateAvatar gender={profile.avatar_gender} size={52} label="Profile avatar" />
            <div className="min-w-0">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-800"><Sparkles className="h-3.5 w-3.5" />{isGraduate ? 'Student / recent graduate' : 'Working professional'}</span>
              <p className="mt-1.5 truncate text-sm text-slate-600">{profile.industry?.name || 'Industry not selected'}</p>
            </div>
          </div>
          <div className="min-w-52 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Target role</p>
            <p className="mt-1 font-semibold text-slate-900">{profile.target_role || 'Add a target role'}</p>
          </div>
        </div>
        <dl className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 px-4 py-3"><dt className="text-xs font-medium text-slate-500">Career stage</dt><dd className="mt-1 text-sm font-semibold text-slate-800">{formatSubcategory(profile.sub_category, isGraduate)}</dd></div>
          <div className="rounded-xl border border-slate-200 px-4 py-3"><dt className="text-xs font-medium text-slate-500">Experience</dt><dd className="mt-1 text-sm font-semibold text-slate-800">{experienceLabel(profile.total_experience_months || 0, isGraduate)}</dd></div>
          <div className="rounded-xl border border-slate-200 px-4 py-3"><dt className="text-xs font-medium text-slate-500">Profile sections</dt><dd className="mt-1 text-sm font-semibold text-slate-800">{profile.education_history.length} education · {profile.experience_history.length} experience</dd></div>
        </dl>
        <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">Resumes use your saved profile details.</p>
      </div>
    </article>

    <div className="grid gap-4 lg:grid-cols-2">
      <DetailCard icon={UserRound} title="Contact & summary">
        <div className="space-y-2 text-sm text-slate-700">{[profile.phone, profile.location, profile.linkedin_url, profile.github_url].filter(Boolean).map((value) => <p key={value}>{value}</p>)}{profile.professional_summary && <p className="border-t border-slate-100 pt-3 leading-6">{profile.professional_summary}</p>}{![profile.phone, profile.location, profile.linkedin_url, profile.github_url, profile.professional_summary].some(Boolean) && <p className="text-slate-600">Add contact information and a short summary to your profile.</p>}</div>
      </DetailCard>
      <DetailCard icon={BriefcaseBusiness} title={isGraduate ? 'Internships & experience' : 'Work experience'}>
        {profile.experience_history.length ? <div className="space-y-4">
          {profile.experience_history.map((item, index) => <div key={item.id || `${item.company_name}-${index}`} className={index ? 'border-t border-slate-100 pt-4' : ''}>
            <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-medium text-slate-900">{item.job_title}</p><p className="mt-0.5 text-sm text-slate-600">{item.company_name}</p></div>
              <p className="text-xs text-slate-500">{[item.start_date, item.end_date || (item.is_current ? 'Present' : '')].filter(Boolean).join(' – ')}</p></div>
            {item.description && <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{item.description}</p>}
          </div>)}
        </div> : <p className="text-sm leading-6 text-slate-600">{isGraduate ? 'Add internships, volunteering, or relevant projects to your profile.' : 'No experience added yet.'}</p>}
        {!isGraduate && <p className="mt-4 border-t border-slate-100 pt-4 text-sm text-slate-600"><span className="font-medium text-slate-800">Current position:</span> {[profile.current_role, profile.current_company].filter(Boolean).join(' at ') || 'Not currently listed'}</p>}
      </DetailCard>

      <DetailCard icon={Building2} title="Projects">
        {profile.projects?.length ? <div className="space-y-4">{profile.projects.map((project, index) => <div key={`${project.name}-${index}`} className={index ? 'border-t border-slate-100 pt-4' : ''}><p className="font-medium text-slate-900">{project.name}{project.role ? ` · ${project.role}` : ''}</p>{project.technologies?.length > 0 && <p className="mt-1 text-xs text-slate-500">{project.technologies.join(' · ')}</p>}{project.description && <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{project.description}</p>}{project.url && <a href={project.url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm font-medium text-violet-800 underline">Project link</a>}</div>)}</div> : <p className="text-sm text-slate-600">Add coursework, personal, or professional projects to your profile.</p>}
      </DetailCard>

      <DetailCard icon={CheckCircle2} title="Certifications">
        {profile.certifications?.length ? <ul className="space-y-3">{profile.certifications.map((item, index) => <li key={`${item.name}-${index}`} className={index ? 'border-t border-slate-100 pt-3' : ''}><p className="font-medium text-slate-900">{item.name}</p><p className="mt-1 text-sm text-slate-600">{[item.issuer, item.issue_date].filter(Boolean).join(' · ')}</p></li>)}</ul> : <p className="text-sm text-slate-600">Add relevant credentials to your profile.</p>}
      </DetailCard>

      <DetailCard icon={GraduationCap} title="Education">
        {profile.education_history.length ? <div className="space-y-4">
          {profile.education_history.map((education, index) => <div key={education.id || `${education.degree}-${index}`} className={index ? 'border-t border-slate-100 pt-4' : ''}>
            <p className="font-medium text-slate-900">{education.degree}{education.field_of_study ? ` · ${education.field_of_study}` : ''}</p>
            <p className="mt-1 text-sm text-slate-600">{education.institution}</p>
            {(education.start_year || education.end_year) && <p className="mt-2 inline-flex items-center gap-1.5 text-xs text-slate-500"><CalendarDays className="h-3.5 w-3.5" />{[education.start_year, education.end_year || (education.is_current ? 'Present' : '')].filter(Boolean).join(' – ')}</p>}
            {education.grade && <p className="mt-1 text-xs text-slate-500">Grade: {education.grade}</p>}
          </div>)}
        </div> : <p className="text-sm text-slate-600">Add your degree or current program to strengthen your profile.</p>}
      </DetailCard>

      <DetailCard icon={Sparkles} title="Skills">
        {profile.key_skills.length ? <div className="flex flex-wrap gap-2">{profile.key_skills.map((skill) => <span key={skill} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700">{skill}</span>)}</div> : <p className="text-sm text-slate-600">No skills added yet.</p>}
        {profile.career_goals && <p className="mt-4 border-t border-slate-100 pt-4 text-sm leading-6 text-slate-600"><span className="font-medium text-slate-800">Career goal: </span>{profile.career_goals}</p>}
      </DetailCard>

      <DetailCard icon={Target} title="Job targets">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Target companies</p>
        {profile.target_companies.length ? <div className="mt-2 flex flex-wrap gap-2">{profile.target_companies.map((item) => <span key={item.id} className="inline-flex items-center gap-1.5 rounded-full bg-violet-50 px-3 py-1.5 text-sm text-violet-900"><Building2 className="h-3.5 w-3.5" />{item.company?.name || 'Company'}{item.target_role ? ` · ${item.target_role}` : ''}</span>)}</div> : <p className="mt-1 text-sm text-slate-600">No target companies selected.</p>}
        <p className="mt-4 border-t border-slate-100 pt-4 text-sm text-slate-600"><span className="font-medium text-slate-800">Interview rounds: </span>{profile.interview_rounds_preferred.length ? profile.interview_rounds_preferred.join(', ') : 'Not selected'}</p>
      </DetailCard>
    </div>
  </section>;
}
