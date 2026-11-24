import { useState, type ReactNode } from 'react';
import {
  ArrowDownToLine, BriefcaseBusiness, Building2, CalendarDays, GraduationCap,
  PencilLine, Sparkles, Target, UserRound,
} from 'lucide-react';
import { resumesApi } from '../../api/resumes';
import type { CandidateProfile } from '../../types';

type ResumeTemplate = 'modern' | 'classic' | 'compact';
const resumeTemplates: { id: ResumeTemplate; name: string; description: string; accent: string; }[] = [
  { id: 'modern', name: 'Modern', description: 'Clean, contemporary hierarchy with a violet accent.', accent: 'bg-violet-600' },
  { id: 'classic', name: 'Classic', description: 'Traditional centered heading and formal typography.', accent: 'bg-slate-500' },
  { id: 'compact', name: 'Compact', description: 'Space-efficient layout for concise, early-career resumes.', accent: 'bg-violet-300' },
];

function experienceLabel(months: number) {
  if (months <= 0) return 'Early career · no professional tenure recorded';
  const years = Math.floor(months / 12);
  const remainingMonths = months % 12;
  return [years ? `${years} ${years === 1 ? 'year' : 'years'}` : '', remainingMonths ? `${remainingMonths} months` : '']
    .filter(Boolean).join(' ');
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
  const isGraduate = profile.candidate_type === 'student_fresher';

  async function downloadResume() {
    setGenerating(true);
    setError('');
    try {
      const { blob, filename } = await resumesApi.generateFromProfile(resumeTemplate);
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

  return <section className="mx-auto max-w-5xl space-y-6 sm:space-y-8">
    <header className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
      <div>
        <p className="text-sm font-semibold tracking-wide text-violet-700">Your career profile</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Candidate information</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">Your saved details shape your preparation plan. Update them anytime, or create a resume from the information you have provided.</p>
      </div>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={onEdit} className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-violet-300 hover:bg-violet-50/60">
          <PencilLine className="h-4 w-4" /> Edit profile
        </button>
        <button type="button" onClick={() => void downloadResume()} disabled={generating} className="inline-flex items-center gap-2 rounded-xl bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-violet-900/15 transition hover:bg-violet-800 disabled:cursor-wait disabled:opacity-60">
          <ArrowDownToLine className="h-4 w-4" /> {generating ? 'Preparing resume…' : 'Generate resume'}
        </button>
      </div>
    </header>

    {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}

    <section aria-labelledby="resume-template-heading" className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between"><div><h2 id="resume-template-heading" className="font-semibold text-slate-900">Choose a resume style</h2><p className="mt-1 text-sm text-slate-500">Select a professional layout. Your DOCX uses only details saved in this profile.</p></div><span className="mt-1 text-xs text-slate-500">Download format: DOCX</span></div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">{resumeTemplates.map((template) => <button key={template.id} type="button" aria-pressed={resumeTemplate === template.id} onClick={() => setResumeTemplate(template.id)} className={`group rounded-xl border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-violet-300 ${resumeTemplate === template.id ? 'border-violet-500 bg-violet-50/50 shadow-sm' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'}`}>
        <div aria-hidden="true" className="flex h-24 gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow-inner"><span className={`w-1.5 shrink-0 rounded-full ${template.accent}`} /><div className={`flex-1 ${template.id === 'classic' ? 'text-center' : ''}`}><span className={`block h-2 w-2/3 rounded ${template.accent} ${template.id === 'classic' ? 'mx-auto' : ''}`} /><span className={`mt-2 block h-1 w-1/2 rounded bg-slate-300 ${template.id === 'classic' ? 'mx-auto' : ''}`} /><span className="mt-3 block h-1 w-full rounded bg-slate-200" /><span className="mt-1.5 block h-1 w-5/6 rounded bg-slate-200" /><span className="mt-2 block h-1 w-1/3 rounded bg-slate-300" /></div></div>
        <span className="mt-3 flex items-center justify-between gap-2"><span className="text-sm font-semibold text-slate-900">{template.name}</span><span className={`h-4 w-4 rounded-full border ${resumeTemplate === template.id ? 'border-violet-600 bg-violet-600 ring-2 ring-violet-100' : 'border-slate-300 bg-white'}`} /></span><span className="mt-1 block text-xs leading-5 text-slate-500">{template.description}</span>
      </button>)}</div>
    </section>

    <article className="relative overflow-hidden rounded-3xl border border-violet-200/70 bg-gradient-to-br from-white via-white to-violet-50/70 p-6 shadow-[0_18px_50px_-36px_rgba(91,33,182,0.42)] sm:p-8">
      <div className="pointer-events-none absolute -right-14 -top-20 h-60 w-60 rounded-full bg-violet-200/20 blur-3xl" />
      <div className="relative flex flex-wrap items-start justify-between gap-5">
        <div className="flex items-center gap-4">
          <span className="grid h-14 w-14 place-items-center rounded-2xl bg-violet-700 text-white shadow-lg shadow-violet-900/20"><UserRound className="h-7 w-7" /></span>
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-white/80 px-2.5 py-1 text-xs font-semibold text-violet-800"><Sparkles className="h-3.5 w-3.5" />{isGraduate ? 'Student / recent graduate' : 'Working professional'}</span>
            <p className="mt-2 text-sm text-slate-600">{profile.industry?.name || 'Industry not selected'}</p>
          </div>
        </div>
        <div className="min-w-48 rounded-2xl border border-white/80 bg-white/80 px-4 py-3 shadow-sm backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Target role</p>
          <p className="mt-1 font-semibold text-slate-900">{profile.target_role || 'Add a target role'}</p>
        </div>
      </div>
      <div className="relative mt-7 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200/70 bg-white/75 px-4 py-3"><p className="text-xs text-slate-500">Career stage</p><p className="mt-1 text-sm font-medium text-slate-800">{profile.sub_category?.replaceAll('_', ' ') || (isGraduate ? 'Recent graduate' : 'Professional')}</p></div>
        <div className="rounded-xl border border-slate-200/70 bg-white/75 px-4 py-3"><p className="text-xs text-slate-500">Experience</p><p className="mt-1 text-sm font-medium capitalize text-slate-800">{experienceLabel(profile.total_experience_months || 0)}</p></div>
        <div className="rounded-xl border border-slate-200/70 bg-white/75 px-4 py-3"><p className="text-xs text-slate-500">Profile sections</p><p className="mt-1 text-sm font-medium text-slate-800">{profile.education_history.length} education · {profile.experience_history.length} experience</p></div>
      </div>
      <p className="relative mt-4 text-xs leading-5 text-slate-500">Resume generation uses only the details saved here. Review your education, experience, and skills before downloading.</p>
    </article>

    <div className="grid gap-4 lg:grid-cols-2">
      <DetailCard icon={BriefcaseBusiness} title={isGraduate ? 'Internships & practical experience' : 'Professional experience'}>
        {profile.experience_history.length ? <div className="space-y-4">
          {profile.experience_history.map((item, index) => <div key={item.id || `${item.company_name}-${index}`} className={index ? 'border-t border-slate-100 pt-4' : ''}>
            <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-medium text-slate-900">{item.job_title}</p><p className="mt-0.5 text-sm text-slate-600">{item.company_name}</p></div>
              <p className="text-xs text-slate-500">{[item.start_date, item.end_date || (item.is_current ? 'Present' : '')].filter(Boolean).join(' – ')}</p></div>
            {item.description && <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{item.description}</p>}
          </div>)}
        </div> : <p className="text-sm leading-6 text-slate-600">{isGraduate ? 'No internships or practical experience added yet. You can add internships, volunteering, or relevant experience by editing your profile.' : 'No experience entries added yet.'}</p>}
        {!isGraduate && <p className="mt-4 border-t border-slate-100 pt-4 text-sm text-slate-600"><span className="font-medium text-slate-800">Current position:</span> {[profile.current_role, profile.current_company].filter(Boolean).join(' at ') || 'Not currently listed'}</p>}
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

      <DetailCard icon={Target} title="Job search preferences">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Target companies</p>
        {profile.target_companies.length ? <div className="mt-2 flex flex-wrap gap-2">{profile.target_companies.map((item) => <span key={item.id} className="inline-flex items-center gap-1.5 rounded-full bg-violet-50 px-3 py-1.5 text-sm text-violet-900"><Building2 className="h-3.5 w-3.5" />{item.company?.name || 'Company'}{item.target_role ? ` · ${item.target_role}` : ''}</span>)}</div> : <p className="mt-1 text-sm text-slate-600">No target companies selected.</p>}
        <p className="mt-4 border-t border-slate-100 pt-4 text-sm text-slate-600"><span className="font-medium text-slate-800">Interview rounds: </span>{profile.interview_rounds_preferred.length ? profile.interview_rounds_preferred.join(', ') : 'Not selected'}</p>
      </DetailCard>
    </div>
  </section>;
}
