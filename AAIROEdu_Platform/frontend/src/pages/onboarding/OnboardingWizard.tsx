import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { candidatesApi, companiesApi, industriesApi } from '../../api/candidates';
import { useAuth } from '../../context/AuthContext';
import type { Industry } from '../../types';
import type { Education, Experience } from '../../types';
import { ProfileOverview } from './ProfileOverview';
import {
  Briefcase, GraduationCap, Building2, CheckCircle2,
  ArrowRight, ArrowLeft, Plus, Trash2, Volume2, MessageSquare
} from 'lucide-react';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { RequiredLabel, RequiredMark } from '../../components/common/RequiredMark';

export const OnboardingWizard: React.FC = () => {
  const { profile, refreshProfile } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isEditing, setIsEditing] = useState(location.pathname !== '/profile' || !profile?.onboarding_completed);

  const [currentStep, setCurrentStep] = useState(1);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [industryLoadAttempt, setIndustryLoadAttempt] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [candidateType, setCandidateType] = useState<'working_professional' | 'student_fresher'>('working_professional');
  const [subCategory, setSubCategory] = useState('experienced_professional');
  const [selectedIndustryId, setSelectedIndustryId] = useState<string>('');
  const [educationList, setEducationList] = useState<Education[]>([]);
  const [experienceList, setExperienceList] = useState<Experience[]>([]);
  const [currentCompany, setCurrentCompany] = useState('');
  const [currentRole, setCurrentRole] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [totalExperienceMonths, setTotalExperienceMonths] = useState(24);
  const [keySkillsInput, setKeySkillsInput] = useState('');
  const [selectedRounds, setSelectedRounds] = useState<string[]>(['Technical', 'HR']);
  const [targetCompanies, setTargetCompanies] = useState<{ company_name: string; target_role: string }[]>([]);
  const [companySearch, setCompanySearch] = useState('');
  const [companyMatches, setCompanyMatches] = useState<{ id: string; name: string }[]>([]);
  const [companyRoleInput, setCompanyRoleInput] = useState('');
  const [interactionPreference, setInteractionPreference] = useState<'text' | 'voice'>('text');
  const profileInitialized = useRef(false);

  useEffect(() => {
    let isCurrent = true;
    setIsLoading(true);
    industriesApi.listIndustries().then((indList) => {
      if (!isCurrent) return;
      setIndustries(indList);
      const profileIndustry = indList.find((industry) => industry.id === profile?.industry_id);
      setSelectedIndustryId((current) => (
        indList.some((industry) => industry.id === current)
          ? current
          : profileIndustry?.id || indList[0]?.id || ''
      ));
      setError(null);
    }).catch((err: Error) => {
      if (isCurrent) setError(err.message || 'Failed to load onboarding options');
    }).finally(() => {
      if (isCurrent) setIsLoading(false);
    });
    return () => { isCurrent = false; };
  }, [profile?.industry_id, industryLoadAttempt]);

  useEffect(() => {
        if (profile) {
          if (!profileInitialized.current && profile.onboarding_step > 1 && !profile.onboarding_completed) {
            setCurrentStep(profile.onboarding_step);
          }
          profileInitialized.current = true;
          if (profile.candidate_type) setCandidateType(profile.candidate_type);
          if (profile.sub_category) setSubCategory(profile.sub_category);
          if (profile.industry_id) setSelectedIndustryId(profile.industry_id);
          if (profile.current_company) setCurrentCompany(profile.current_company);
          if (profile.current_role) setCurrentRole(profile.current_role);
          if (profile.target_role) setTargetRole(profile.target_role);
          if (profile.total_experience_months) setTotalExperienceMonths(profile.total_experience_months);
          if (profile.key_skills?.length > 0) setKeySkillsInput(profile.key_skills.join(', '));
          if (profile.interview_rounds_preferred?.length > 0) setSelectedRounds(profile.interview_rounds_preferred);
          if (profile.interaction_preference) setInteractionPreference(profile.interaction_preference);
          setEducationList(profile.education_history?.map((education) => ({ ...education })) || []);
          setExperienceList(profile.experience_history?.map((experience) => ({ ...experience })) || []);
          setTargetCompanies(profile.target_companies?.map((item) => ({ company_name: item.company?.name || '', target_role: item.target_role || '' })) || []);
        }
  }, [profile]);

  useEffect(() => {
    if (!companySearch.trim()) { setCompanyMatches([]); return; }
    const timer = window.setTimeout(() => {
      companiesApi.search(companySearch).then(setCompanyMatches).catch(() => setCompanyMatches([]));
    }, 200);
    return () => window.clearTimeout(timer);
  }, [companySearch]);

  const handleNext = async () => {
    if (currentStep === 2 && !selectedIndustryId) {
      setError(industries.length === 0
        ? 'No active industries are available right now. Retry loading the options before continuing.'
        : 'Select an industry before continuing.');
      return;
    }
    const incompleteExperience = experienceList.some((entry) => {
      const hasDetails = Boolean(entry.company_name.trim() || entry.job_title.trim() || entry.description?.trim());
      return hasDetails && (!entry.company_name.trim() || !entry.job_title.trim());
    });
    if (incompleteExperience) {
      setError('For each experience entry, add both the company or organization and your position.');
      return;
    }
    setIsSaving(true);
    setError(null);

    const skills = keySkillsInput.split(',').map(s => s.trim()).filter(Boolean);
    const stepPayload: any = {
      step: currentStep,
      is_final_step: currentStep === 7,
      candidate_type: candidateType,
      sub_category: subCategory,
      industry_id: selectedIndustryId || null,
      current_company: candidateType === 'working_professional' ? currentCompany.trim() : '',
      current_role: candidateType === 'working_professional' ? currentRole.trim() : '',
      target_role: targetRole || (candidateType === 'working_professional' ? currentRole : 'Associate'),
      total_experience_months: candidateType === 'working_professional' ? totalExperienceMonths : 0,
      education: educationList.filter((education) => Boolean(education.degree.trim() || education.field_of_study.trim() || education.institution.trim())),
      experience: experienceList.filter((entry) => Boolean(entry.company_name.trim() || entry.job_title.trim() || entry.description?.trim())),
      key_skills: skills,
      interview_rounds_preferred: selectedRounds,
      target_companies: targetCompanies,
      interaction_preference: interactionPreference
    };

    try {
      await candidatesApi.saveOnboardingStep(stepPayload);
      await refreshProfile();

      if (currentStep < 7) {
        setCurrentStep(currentStep + 1);
      } else {
        navigate('/dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save progress');
    } finally {
      setIsSaving(false);
    }
  };

  const interviewRoundOptions = [
    'HR', 'Technical', 'Coding', 'System Design', 'Case Study',
    'Group Discussion', 'Managerial', 'Domain-Specific', 'Final Round'
  ];

  const addTargetCompany = (companyName: string) => {
    const name = companyName.trim();
    if (!name || targetCompanies.some((company) => company.company_name.toLowerCase() === name.toLowerCase())) return;
    setTargetCompanies((companies) => [...companies, { company_name: name, target_role: companyRoleInput.trim() || targetRole }]);
    setCompanySearch('');
    setCompanyMatches([]);
    setCompanyRoleInput('');
  };

  if (isLoading) {
    return <LoadingSpinner size="lg" message="Configuring onboarding..." />;
  }

  if (location.pathname === '/profile' && profile?.onboarding_completed && !isEditing) {
    return <ProfileOverview profile={profile} onEdit={() => setIsEditing(true)} />;
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Wizard Header Progress */}
      <div className="mb-8">
        {!profile?.onboarding_completed && <p className="mb-4 rounded-lg border border-violet-200 bg-violet-50 p-3 text-sm text-violet-900">Complete your profile first. Your coach, learning roadmap, and practice activities unlock when setup is finished.</p>}
        {location.pathname === '/profile' && isEditing && profile?.onboarding_completed && <button type="button" onClick={() => setIsEditing(false)} className="mb-4 text-sm font-semibold text-violet-800 underline">Cancel editing</button>}
        <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
          <span className="uppercase tracking-wider text-violet-600">Candidate Profiling</span>
          <span>Step {currentStep} of 7</span>
        </div>
        <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-violet-500 to-emerald-500 h-full transition-all duration-300 rounded-full"
            style={{ width: `${(currentStep / 7) * 100}%` }}
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
        {error && (
          <div className="mb-6 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
            {error}
          </div>
        )}

        {/* STEP 1: Candidate Type */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">What best describes your current journey?<RequiredMark /></h2>
              <p className="text-xs text-slate-500 mt-1">We personalize your preparation track and questions accordingly.</p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div
                onClick={() => { setCandidateType('working_professional'); setSubCategory('experienced_professional'); }}
                className={`p-5 rounded-xl border-2 cursor-pointer transition-all ${
                  candidateType === 'working_professional'
                    ? 'border-violet-500 bg-violet-50/40 shadow-sm'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="w-10 h-10 rounded-lg bg-violet-100 text-violet-700 flex items-center justify-center mb-3">
                  <Briefcase className="w-5 h-5" />
                </div>
                <h4 className="font-semibold text-slate-900 text-sm">Working Professional</h4>
                <p className="text-xs text-slate-500 mt-1">Currently employed, seeking promotion, or switching careers.</p>
              </div>

              <div
                onClick={() => { setCandidateType('student_fresher'); setSubCategory('recent_graduate'); }}
                className={`p-5 rounded-xl border-2 cursor-pointer transition-all ${
                  candidateType === 'student_fresher'
                    ? 'border-violet-500 bg-violet-50/40 shadow-sm'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center mb-3">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <h4 className="font-semibold text-slate-900 text-sm">Student / Fresher</h4>
                <p className="text-xs text-slate-500 mt-1">Undergraduate, final-year student, recent graduate, or diploma holder.</p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Subcategory</label>
              <select
                value={subCategory}
                onChange={(e) => setSubCategory(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-800"
              >
                {candidateType === 'working_professional' ? (
                  <>
                    <option value="experienced_professional">Experienced Professional</option>
                    <option value="job_seeker">Active Job Seeker</option>
                    <option value="career_switcher">Career Switcher</option>
                    <option value="promotion_seeker">Promotion / Appraisal Seeker</option>
                  </>
                ) : (
                  <>
                    <option value="final_year_student">Final-Year Student</option>
                    <option value="recent_graduate">Recent Graduate (0-1 yr)</option>
                    <option value="undergraduate">Undergraduate Student</option>
                    <option value="postgraduate">Postgraduate Student</option>
                    <option value="diploma_holder">Diploma Holder</option>
                  </>
                )}
              </select>
            </div>
          </div>
        )}

        {/* STEP 2: Industry Selection */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Select your target industry<RequiredMark /></h2>
              <p className="text-xs text-slate-500 mt-1">
                Aairo is industry-independent with 20+ specialized domain tracks.
              </p>
            </div>

            {industries.length === 0 ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                <p>No active industries are available. Your profile details are safe; try loading the options again.</p>
                <button type="button" onClick={() => setIndustryLoadAttempt((attempt) => attempt + 1)} className="mt-3 font-semibold underline underline-offset-2">
                  Retry loading industries
                </button>
              </div>
            ) : <div className="grid sm:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
              {industries.map((ind) => (
                <div
                  key={ind.id}
                  onClick={() => setSelectedIndustryId(ind.id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    selectedIndustryId === ind.id
                      ? 'border-violet-500 bg-violet-50/50 shadow-xs'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-slate-900">{ind.name}</span>
                    {selectedIndustryId === ind.id && (
                      <CheckCircle2 className="w-4 h-4 text-violet-600" />
                    )}
                  </div>
                  {ind.description && (
                    <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{ind.description}</p>
                  )}
                </div>
              ))}
            </div>}
          </div>
        )}

        {/* STEP 3: Education */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Educational Background</h2>
              <p className="text-xs text-slate-500 mt-1">Add your degrees and academic qualifications.</p>
            </div>

            {educationList.map((edu, idx) => (
              <div key={idx} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3 relative">
                <div className="grid sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700">Degree</label>
                    <input
                      type="text"
                      value={edu.degree}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].degree = e.target.value;
                        setEducationList(copy);
                      }}
                      placeholder="e.g. B.Tech, MBA, BBA, B.Com"
                      className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700">Field of Study</label>
                    <input
                      type="text"
                      value={edu.field_of_study}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].field_of_study = e.target.value;
                        setEducationList(copy);
                      }}
                      placeholder="e.g. Computer Science, Finance"
                      className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm"
                    />
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700">Institution / University</label>
                    <input
                      type="text"
                      value={edu.institution}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].institution = e.target.value;
                        setEducationList(copy);
                      }}
                      placeholder="e.g. Stanford University"
                      className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700">Graduation Year</label>
                    <input
                      type="number"
                      value={edu.end_year ?? ''}
                      onChange={(e) => {
                        const copy = [...educationList];
                        copy[idx].end_year = e.target.value ? parseInt(e.target.value, 10) : undefined;
                        setEducationList(copy);
                      }}
                      className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm"
                    />
                  </div>
                </div>
                <button type="button" onClick={() => setEducationList((items) => items.filter((_, itemIndex) => itemIndex !== idx))} className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 hover:text-rose-700">
                  <Trash2 className="w-3.5 h-3.5" /> Remove education
                </button>
              </div>
            ))}
            <button type="button" onClick={() => setEducationList((items) => [...items, { degree: '', field_of_study: '', institution: '', start_year: undefined, end_year: undefined, is_current: false }])} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
              <Plus className="w-3.5 h-3.5" /> Add education
            </button>
          </div>
        )}

        {/* STEP 4: Professional Details */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Experience & target role</h2>
              <p className="text-xs text-slate-500 mt-1">Recent graduates can leave employment details empty and add internships or practical experience below.</p>
            </div>

            {candidateType === 'working_professional' && (
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700">Current Company</label>
                  <input
                    type="text"
                    value={currentCompany}
                    onChange={(e) => setCurrentCompany(e.target.value)}
                    placeholder="e.g. TechCorp Solutions"
                    className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700">Current Designation</label>
                  <input
                    type="text"
                    value={currentRole}
                    onChange={(e) => setCurrentRole(e.target.value)}
                    placeholder="e.g. Full-Stack Developer"
                    className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>
            )}

            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700"><RequiredLabel>Target Job Role</RequiredLabel></label>
                <input
                  type="text"
                  required
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="e.g. Senior Software Architect"
                  className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm font-medium"
                />
              </div>
              {candidateType === 'working_professional' && (
                <div>
                  <label className="block text-xs font-medium text-slate-700">Professional experience (months)</label>
                  <input
                    type="number"
                    min={0}
                    max={720}
                    value={totalExperienceMonths}
                    onChange={(e) => setTotalExperienceMonths(parseInt(e.target.value) || 0)}
                    className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              )}
            </div>

            <div className="space-y-3 border-t border-slate-200 pt-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-slate-900">Internships & experience history <span className="font-normal text-slate-500">(optional)</span></h3>
                  <p className="mt-1 text-xs leading-5 text-slate-500">Add internships, part-time roles, volunteering, or other relevant experience. These details can appear in your generated resume.</p>
                </div>
                <button type="button" onClick={() => setExperienceList((items) => [...items, { company_name: '', job_title: '', start_date: '', end_date: '', is_current: false, description: '' }])} className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-violet-300 hover:bg-violet-50">
                  <Plus className="h-3.5 w-3.5" /> Add experience
                </button>
              </div>
              {candidateType === 'student_fresher' && experienceList.length === 0 && <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600">No work experience is required for a recent graduate. Continue with education, projects, and skills if you have no internships yet.</p>}
              {experienceList.map((entry, index) => <div key={entry.id || index} className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="text-xs font-medium text-slate-700">Company / organization<input value={entry.company_name} onChange={(event) => setExperienceList((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, company_name: event.target.value } : item))} placeholder="e.g. Summer internship organization" className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm" /></label>
                  <label className="text-xs font-medium text-slate-700">Position / role<input value={entry.job_title} onChange={(event) => setExperienceList((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, job_title: event.target.value } : item))} placeholder="e.g. Software Engineering Intern" className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm" /></label>
                  <label className="text-xs font-medium text-slate-700">Start date<input value={entry.start_date || ''} onChange={(event) => setExperienceList((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, start_date: event.target.value } : item))} placeholder="e.g. Jun 2025" className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm" /></label>
                  <label className="text-xs font-medium text-slate-700">End date<input value={entry.end_date || ''} disabled={entry.is_current} onChange={(event) => setExperienceList((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, end_date: event.target.value } : item))} placeholder="e.g. Aug 2025" className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm disabled:bg-slate-100" /></label>
                </div>
                <label className="flex items-center gap-2 text-xs text-slate-700"><input type="checkbox" checked={entry.is_current} onChange={(event) => setExperienceList((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, is_current: event.target.checked, end_date: event.target.checked ? '' : item.end_date } : item))} className="rounded border-slate-300 text-violet-700 focus:ring-violet-600" />This role is current</label>
                <label className="block text-xs font-medium text-slate-700">What did you work on?<textarea value={entry.description || ''} onChange={(event) => setExperienceList((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, description: event.target.value } : item))} rows={3} placeholder="Describe your responsibilities, projects, or outcomes. Keep claims factual." className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm" /></label>
                <button type="button" onClick={() => setExperienceList((items) => items.filter((_, itemIndex) => itemIndex !== index))} className="text-xs font-semibold text-rose-700 hover:text-rose-800">Remove this entry</button>
              </div>)}
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700">Key Skills (comma-separated)</label>
              <input
                type="text"
                value={keySkillsInput}
                onChange={(e) => setKeySkillsInput(e.target.value)}
                placeholder="e.g. Python, FastAPI, React, PostgreSQL, Docker, System Design"
                className="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg text-sm"
              />
            </div>
          </div>
        )}

        {/* STEP 5: Interview Rounds */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Which interview rounds are you preparing for?</h2>
              <p className="text-xs text-slate-500 mt-1">Select all rounds that apply to your upcoming interviews.</p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {interviewRoundOptions.map((round) => {
                const isSelected = selectedRounds.includes(round);
                return (
                  <button
                    type="button"
                    key={round}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedRounds(selectedRounds.filter(r => r !== round));
                      } else {
                        setSelectedRounds([...selectedRounds, round]);
                      }
                    }}
                    className={`p-3 rounded-xl border text-xs font-semibold text-left transition-all ${
                      isSelected
                        ? 'border-violet-500 bg-violet-50 text-violet-800 shadow-2xs'
                        : 'border-slate-200 text-slate-700 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span>{round}</span>
                      {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-violet-600" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* STEP 6: Target Companies */}
        {currentStep === 6 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Target Companies</h2>
              <p className="text-xs text-slate-500 mt-1">Specify your dream companies or organizations.</p>
            </div>

            <div className="space-y-3">
              <label className="block text-xs font-medium text-slate-700" htmlFor="company-search">Search or add a company</label>
              <input id="company-search" type="text" value={companySearch} onChange={(e) => setCompanySearch(e.target.value)} placeholder="Type an organization name" className="w-full p-2.5 bg-white border border-slate-300 rounded-lg text-sm" />
              {companyMatches.length > 0 && <div className="rounded-lg border border-slate-200 divide-y divide-slate-100">{companyMatches.map((company) => <button key={company.id} type="button" onClick={() => addTargetCompany(company.name)} className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50">{company.name}</button>)}</div>}
              {companySearch.trim() && !companyMatches.some((company) => company.name.toLowerCase() === companySearch.trim().toLowerCase()) && <button type="button" onClick={() => addTargetCompany(companySearch)} className="text-xs font-semibold text-violet-700 hover:underline">Add “{companySearch.trim()}” as a new company</button>}
              <label className="block text-xs font-medium text-slate-700" htmlFor="company-target-role">Target role for the next company</label>
              <input id="company-target-role" type="text" value={companyRoleInput} onChange={(e) => setCompanyRoleInput(e.target.value)} placeholder={targetRole || 'Role at this company'} className="w-full p-2.5 bg-white border border-slate-300 rounded-lg text-sm" />
              <div className="space-y-2">{targetCompanies.map((company, index) => <div key={`${company.company_name}-${index}`} className="flex items-center gap-2 rounded-lg bg-slate-50 p-3">
                <Building2 className="h-4 w-4 shrink-0 text-slate-500" />
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-800">{company.company_name}</span>
                <input aria-label={`Target role at ${company.company_name}`} value={company.target_role} onChange={(event) => setTargetCompanies((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, target_role: event.target.value } : item))} placeholder="Target role" className="w-40 rounded-md border border-slate-300 px-2 py-1.5 text-xs" />
                <button type="button" aria-label={`Remove ${company.company_name}`} onClick={() => setTargetCompanies((items) => items.filter((_, itemIndex) => itemIndex !== index))} className="text-rose-600"><Trash2 className="h-4 w-4" /></button>
              </div>)}</div>
            </div>
          </div>
        )}

        {/* STEP 7: Interaction Preferences */}
        {currentStep === 7 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Preparation & Interaction Mode</h2>
              <p className="text-xs text-slate-500 mt-1">Choose how you prefer practicing your mock interviews.</p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div
                onClick={() => setInteractionPreference('text')}
                className={`p-5 rounded-xl border-2 cursor-pointer transition-all ${
                  interactionPreference === 'text'
                    ? 'border-violet-500 bg-violet-50/50 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="w-10 h-10 rounded-lg bg-violet-100 text-violet-700 flex items-center justify-center mb-3">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <h4 className="font-semibold text-slate-900 text-sm">Text-Based Preparation</h4>
                <p className="text-xs text-slate-500 mt-1">Type in answers, review written model solutions, and refine STAR phrasing.</p>
              </div>

              <div
                onClick={() => setInteractionPreference('voice')}
                className={`p-5 rounded-xl border-2 cursor-pointer transition-all ${
                  interactionPreference === 'voice'
                    ? 'border-violet-500 bg-violet-50/50 shadow-xs'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="w-10 h-10 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center mb-3">
                  <Volume2 className="w-5 h-5" />
                </div>
                <h4 className="font-semibold text-slate-900 text-sm">Voice-Based Simulation</h4>
                <p className="text-xs text-slate-500 mt-1">Practice spoken articulation and audio interview delivery.</p>
                <p className="text-[11px] font-medium text-purple-700 mt-2">Requires a configured voice provider.</p>
              </div>
            </div>
          </div>
        )}

        {/* Wizard Controls */}
        <div className="mt-8 pt-6 border-t border-slate-200 flex items-center justify-between">
          <button
            type="button"
            disabled={currentStep === 1 || isSaving}
            onClick={() => setCurrentStep(currentStep - 1)}
            className="inline-flex items-center gap-1.5 px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-30 disabled:pointer-events-none"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back
          </button>

          <button
            type="button"
            disabled={isSaving}
            onClick={handleNext}
            className="inline-flex items-center gap-2 px-5 py-2.5 border border-transparent rounded-lg shadow-sm text-xs font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50 transition-colors"
          >
            {isSaving ? 'Saving...' : currentStep === 7 ? 'Complete Onboarding' : 'Save & Continue'}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
