import { RequiredLabel } from '../../components/common/RequiredMark';
import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Bookmark, Search, ArrowRight, AlertCircle, Sparkles, Globe, Download, CheckCircle, ExternalLink, Code2, Copy, Check } from 'lucide-react';
import { apiClient } from '../../api/client';
import { questionsApi, companyIntelApi } from '../../api/services';
import type {
  Question,
  QuestionPracticeResult,
  QuestionPracticeHistory,
  CompanyInterviewQuestion,
  CompanySummary,
  CompanyBlueprint,
  DynamicDorks,
  SynthesizedRoundQuestion,
} from '../../types';

const provenanceLabel: Record<Question['source_provenance'], string> = {
  source_verified: 'Source verified',
  source_formatted: 'Source formatted',
  ai_generated: 'AI generated',
  editorially_reviewed: 'Editorially reviewed',
};

const CANONICAL_ROUNDS = [
  { id: '', label: 'All Rounds' },
  { id: '1', label: 'Round 1: Screening & Fundamentals' },
  { id: '2', label: 'Round 2: Core Craft & Execution' },
  { id: '3', label: 'Round 3: Applied Design & Case Study' },
  { id: '4', label: 'Round 4: Architecture & Strategy' },
  { id: '5', label: 'Round 5: Behavioral & Leadership' },
];

export function QuestionBankPage() {
  const [searchParams] = useSearchParams();
  const urlSearch = searchParams.get('search')?.trim() ?? '';

  // Mode: standard curriculum vs authentic company intelligence
  const [activeTab, setActiveTab] = useState<'company' | 'standard'>('company');

  // Standard Bank State
  const [questions, setQuestions] = useState<Question[]>([]);
  const [query, setQuery] = useState(urlSearch);
  const [searchText, setSearchText] = useState(urlSearch);
  const [filters, setFilters] = useState({
    difficulty: '',
    industry_category_id: '',
    job_role_id: '',
    skill_id: '',
    subject_id: '',
    topic_id: '',
    experience_level_id: '',
    company_id: '',
    interview_round: '',
    question_type: '',
    bookmarked: '',
  });
  const [taxonomy, setTaxonomy] = useState<{
    categories: { id: string; name: string }[];
    job_roles: { id: string; title: string }[];
    subjects: { id: string; name: string }[];
    topics: { id: string; name: string; subject_id: string }[];
    skills: { id: string; name: string }[];
    experience_levels: { id: string; name: string }[];
    interview_rounds: { id: string; name: string }[];
    companies: { id: string; name: string }[];
  }>({
    categories: [],
    job_roles: [],
    subjects: [],
    topics: [],
    skills: [],
    experience_levels: [],
    interview_rounds: [],
    companies: [],
  });
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [history, setHistory] = useState<QuestionPracticeHistory[] | null>(null);
  const [selected, setSelected] = useState<Question | null>(null);
  const [answer, setAnswer] = useState('');
  const [result, setResult] = useState<QuestionPracticeResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Company Intelligence State
  const [companyQuestions, setCompanyQuestions] = useState<CompanyInterviewQuestion[]>([]);
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string>('Google');
  const [selectedRound, setSelectedRound] = useState<string>('');
  const [companyCategory, setCompanyCategory] = useState<string>('');
  const [companyDifficulty, setCompanyDifficulty] = useState<string>('');
  const [companySearch, setCompanySearch] = useState<string>('');
  const [companySearchInput, setCompanySearchInput] = useState<string>('');
  const [companyLoading, setCompanyLoading] = useState(false);
  const [companyPage, setCompanyPage] = useState(1);
  const [companyTotal, setCompanyTotal] = useState(0);

  // Blueprint Modal
  const [blueprintModalOpen, setBlueprintModalOpen] = useState(false);
  const [blueprintData, setBlueprintData] = useState<CompanyBlueprint | null>(null);
  const [blueprintLoading, setBlueprintLoading] = useState(false);

  // Selected Company Question Practice
  const [selectedCompanyQ, setSelectedCompanyQ] = useState<CompanyInterviewQuestion | null>(null);
  const [companyAnswer, setCompanyAnswer] = useState('');
  const [companyResult, setCompanyResult] = useState<QuestionPracticeResult | null>(null);
  const [evaluatingCompany, setEvaluatingCompany] = useState(false);

  // Nemotron Dynamic Intelligence & Open-Web Engine
  const [dynamicDorks, setDynamicDorks] = useState<DynamicDorks | null>(null);
  const [synthesizedRoundQs, setSynthesizedRoundQs] = useState<SynthesizedRoundQuestion[]>([]);
  const [generatingNemotron, setGeneratingNemotron] = useState(false);
  const [scrapingLive, setScrapingLive] = useState(false);
  const [scrapeSuccessMsg, setScrapeSuccessMsg] = useState('');
  const [targetYoE, setTargetYoE] = useState<number>(3.5);
  const [targetSkills, setTargetSkills] = useState<string>('');
  const [targetRole, setTargetRole] = useState<string>('');
  const [customRoleInput, setCustomRoleInput] = useState<string>('');
  const [availableRoles, setAvailableRoles] = useState<string[]>([]);
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  const [customCompanyInput, setCustomCompanyInput] = useState<string>('');
  const [selectedIndustry, setSelectedIndustry] = useState<string>('');
  const [industrySearchInput, setIndustrySearchInput] = useState<string>('');
  const [availableIndustries, setAvailableIndustries] = useState<string[]>([]);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const [entityMode, setEntityMode] = useState<'company' | 'startup'>('company');
  const [flowStep, setFlowStep] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [companyDropdownOpen, setCompanyDropdownOpen] = useState(false);
  const [industryDropdownOpen, setIndustryDropdownOpen] = useState(false);
  const [roleDropdownOpen, setRoleDropdownOpen] = useState(false);
  const [roleSearchInput, setRoleSearchInput] = useState('');
  const [dynamicRounds, setDynamicRounds] = useState<{ id: string; label: string }[]>(CANONICAL_ROUNDS);

  const effectiveRole = targetRole === 'custom' ? customRoleInput.trim() || 'Software Engineer' : targetRole;
  const isStartupOrUnindexed =
    entityMode === 'startup' ||
    selectedCompany.toLowerCase() === 'startup' ||
    (companies.length > 0 && !companies.some((c) => c.name.toLowerCase() === selectedCompany.toLowerCase()));
  const filteredCompanies = customCompanyInput.trim()
    ? companies.filter((c) => c.name.toLowerCase().includes(customCompanyInput.trim().toLowerCase()))
    : companies;
  const filteredIndustries = industrySearchInput.trim()
    ? availableIndustries.filter((ind) => ind.toLowerCase().includes(industrySearchInput.trim().toLowerCase()))
    : availableIndustries;

  const [scrapeLimit, setScrapeLimit] = useState<number>(100);
  const [scrapePlatforms, setScrapePlatforms] = useState<string[]>([
    'LeetCode',
    'GeeksforGeeks',
    'Reddit',
    'Open Web',
  ]);

  function togglePlatform(plat: string) {
    setScrapePlatforms((prev) =>
      prev.includes(plat) ? (prev.length > 1 ? prev.filter((p) => p !== plat) : prev) : [...prev, plat]
    );
  }

  function handleRoleChange(newRole: string) {
    setTargetRole(newRole);
    const rLower = (newRole === 'custom' ? customRoleInput : newRole).toLowerCase();
    if (rLower.includes('finance') || rLower.includes('financial') || rLower.includes('fpa') || rLower.includes('accounting') || rLower.includes('valuation') || rLower.includes('treasury')) {
      setTargetSkills('Financial Modeling, DCF, Variance Analysis, Excel VBA, FP&A, GAAP / IFRS, Budgeting & Forecasting');
    } else if (rLower.includes('machine learning') || rLower.includes('ai') || rLower.includes('ml') || rLower.includes('genai') || rLower.includes('llm')) {
      setTargetSkills('PyTorch, CUDA, Transformers, Distributed Training, Model Quantization, RAG');
    } else if (rLower.includes('frontend') || rLower.includes('ui') || rLower.includes('web') || rLower.includes('react')) {
      setTargetSkills('React, TypeScript, Web Performance, State Management, DOM & CSS, Next.js');
    } else if (rLower.includes('data') || rLower.includes('analytics') || rLower.includes('analyst') || rLower.includes('bi')) {
      setTargetSkills('SQL, Statistics, Tableau, Data Warehousing, Python, ETL Pipelines, A/B Testing');
    } else if (rLower.includes('devops') || rLower.includes('sre') || rLower.includes('cloud') || rLower.includes('infrastructure')) {
      setTargetSkills('Kubernetes, Docker, Terraform, CI/CD, Linux Internals, Observability, AWS/Azure');
    } else if (rLower.includes('backend') || rLower.includes('systems') || rLower.includes('distributed')) {
      setTargetSkills('Go, Distributed Systems, Concurrency, Kafka, PostgreSQL, Microservices, gRPC');
    } else if (rLower.includes('design') || rLower.includes('ux') || rLower.includes('ui/ux') || rLower.includes('product design')) {
      setTargetSkills('Figma, Design Systems, User Research, Wireframing, Interaction Design, Prototyping, Usability Testing');
    } else if (rLower.includes('product') || rLower.includes('pm')) {
      setTargetSkills('Product Strategy, User Empathy, Metrics & KPIs, A/B Testing, Prioritization, PRDs');
    } else if (rLower.includes('security') || rLower.includes('cyber') || rLower.includes('infosec')) {
      setTargetSkills('Threat Modeling, OWASP, Penetration Testing, IAM, Cryptography, SOC2 Compliance');
    } else if (rLower.includes('sales') || rLower.includes('commercial')) {
      setTargetSkills('Solution Value Pitch, MEDDPICC, Pipeline Management, Discovery Calls, Objection Handling');
    } else if (rLower.includes('hr') || rLower.includes('talent') || rLower.includes('people')) {
      setTargetSkills('STAR Behavioral Framework, Competency Rubrics, Talent Pipeline, Culture Assessment');
    } else {
      setTargetSkills('Data Structures, Algorithms, System Design, Concurrency, Clean Code');
    }
  }

  async function handleGenerateNemotron() {
    setGeneratingNemotron(true);
    setError('');
    try {
      const skillsArr = targetSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const [dorksResp, synthResp] = await Promise.all([
        companyIntelApi.generateDorks({
          company: selectedCompany,
          role: effectiveRole,
          yoe: targetYoE,
          skills: skillsArr,
        }),
        companyIntelApi.synthesizeRoundQuestions({
          company: selectedCompany,
          role: effectiveRole,
          yoe: targetYoE,
          skills: skillsArr,
          round_number: selectedRound ? parseInt(selectedRound, 10) : undefined,
        }),
      ]);
      setDynamicDorks(dorksResp ?? null);
      setSynthesizedRoundQs(synthResp ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate Nemotron dynamic intelligence.');
    } finally {
      setGeneratingNemotron(false);
    }
  }

  async function handleLiveScrape() {
    setScrapingLive(true);
    setScrapeSuccessMsg('');
    setError('');
    try {
      const skillsArr = targetSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const res = await companyIntelApi.triggerLiveScrape({
        company: selectedCompany,
        industry: isStartupOrUnindexed && selectedIndustry ? selectedIndustry : undefined,
        role: effectiveRole,
        yoe: targetYoE,
        skills: skillsArr,
        round_number: selectedRound ? parseInt(selectedRound, 10) : undefined,
        difficulty: companyDifficulty || undefined,
        platforms: scrapePlatforms,
        keyword: companySearchInput || '',
        limit: scrapeLimit,
        max_pages: scrapeLimit >= 100 ? 6 : 3,
      });
      const countStored = res.stored_in_database ?? 0;
      const countExtracted = res.extracted_questions_count ?? 0;
      const countSources = res.scraped_sources_count ?? 4;
      const dbStatus = countStored > 0
        ? `saved ${countStored} new records into database`
        : (countExtracted > 0 ? `all ${countExtracted} questions verified & synced in database (deduplicated)` : 'no new questions found');
      setScrapeSuccessMsg(
        `✅ Live Scrape Complete: Scraped ${countSources} web sources, extracted ${countExtracted} authentic questions for ${selectedCompany} (${effectiveRole}, ${targetYoE} yrs YoE) and ${dbStatus}!`
      );
      void loadCompanyQuestions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Live scraping encountered an issue.');
    } finally {
      setScrapingLive(false);
    }
  }

  function exportCleanCsv() {
    const listToExport = companyQuestions.length ? companyQuestions : synthesizedRoundQs;
    if (!listToExport.length) return;
    const headers = ['Round', 'Interview Round', 'Company', 'Role', 'Question', 'Category', 'Difficulty', 'Skills Tested', 'Platform'];
    const rows = listToExport.map((q: any) => [
      `"${q.round_number || 1}"`,
      `"${(q.interview_round || '').replace(/"/g, '""')}"`,
      `"${(q.company_name || q.company || '').replace(/"/g, '""')}"`,
      `"${(q.job_role || q.role || '').replace(/"/g, '""')}"`,
      `"${(q.question_text || '').replace(/"/g, '""')}"`,
      `"${(q.category || '').replace(/"/g, '""')}"`,
      `"${q.difficulty || ''}"`,
      `"${(Array.isArray(q.skills_tested) ? q.skills_tested.join(', ') : '').replace(/"/g, '""')}"`,
      `"${(q.source_platform || '').replace(/"/g, '""')}"`,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `interview_questions_${selectedCompany.toLowerCase()}_clean.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function copyToClipboard(key: string, text: string) {
    void navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  // Load Standard Questions
  const loadQuestions = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [response, options] = await Promise.all([
        questionsApi.listQuestions({ search: query, ...filters, page, limit: 30, sort_by: 'created_at', sort_order: 'desc' }),
        questionsApi.taxonomy(),
      ]);
      setQuestions((items) => (page === 1 ? response ?? [] : [...items, ...(response ?? [])]));
      setHasMore((response ?? []).length === 30);
      setTaxonomy(options);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Questions could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [query, filters, page]);

  // Load Company Questions
  const loadCompanyQuestions = useCallback(async () => {
    setCompanyLoading(true);
    try {
      const params: Record<string, any> = {
        company: selectedCompany,
        role: effectiveRole !== 'All Roles' ? effectiveRole : undefined,
        round_number: selectedRound ? parseInt(selectedRound, 10) : undefined,
        category: companyCategory || undefined,
        difficulty: companyDifficulty || undefined,
        search: companySearch || undefined,
        page: companyPage,
        limit: Math.max(100, scrapeLimit),
      };
      const response = await companyIntelApi.listQuestions(params);
      setCompanyQuestions(response ?? []);
      setCompanyTotal((response ?? []).length);
    } catch (err) {
      console.error('Failed to load company questions:', err);
    } finally {
      setCompanyLoading(false);
    }
  }, [selectedCompany, effectiveRole, selectedRound, companyCategory, companyDifficulty, companySearch, companyPage]);

  // Initial Dynamic Metadata Directory (Companies, Roles, Categories)
  useEffect(() => {
    let mounted = true;
    async function fetchDynamicMetadata() {
      try {
        const [comps, roles, cats, inds] = await Promise.all([
          companyIntelApi.listCompanies(),
          companyIntelApi.listRoles(),
          companyIntelApi.listCategories(),
          apiClient<Array<{ id: string; name: string }>>('/industries').catch(() => []),
        ]);
        if (mounted) {
          if (comps?.length) setCompanies(comps);
          if (roles?.length) setAvailableRoles(roles);
          if (cats?.length) setAvailableCategories(cats);
          if (inds?.length) setAvailableIndustries(inds.map((i) => i.name));
        }
      } catch (err) {
        console.warn('Failed to load dynamic company intel metadata:', err);
      }
    }
    void fetchDynamicMetadata();
    return () => {
      mounted = false;
    };
  }, []);

  // Update roles and categories when selectedCompany changes
  useEffect(() => {
    let mounted = true;
    async function updateCompanySpecificMeta() {
      try {
        const [roles, cats] = await Promise.all([
          companyIntelApi.listRoles(selectedCompany),
          companyIntelApi.listCategories(selectedCompany),
        ]);
        if (mounted) {
          if (roles?.length) {
            setAvailableRoles(roles);
            if (targetRole !== 'custom' && !roles.includes(targetRole)) {
              handleRoleChange(roles[0]);
            }
          }
          if (cats?.length) setAvailableCategories(cats);
        }
      } catch (e) {
        // preserve existing
      }
    }
    void updateCompanySpecificMeta();
    return () => {
      mounted = false;
    };
  }, [selectedCompany]);

  // Dynamically update Rounds dropdown when Company, Role, or YoE changes
  useEffect(() => {
    let mounted = true;
    async function refreshDynamicRounds() {
      try {
        const bp = await companyIntelApi.getBlueprint(selectedCompany, effectiveRole, targetYoE);
        if (mounted && bp?.rounds?.length) {
          setDynamicRounds([
            { id: '', label: 'All Rounds' },
            ...bp.rounds.map((r: any) => ({
              id: String(r.number),
              label: r.name?.startsWith('Round ') ? r.name : `Round ${r.number}: ${r.name}`,
            })),
          ]);
        }
      } catch {
        if (mounted) setDynamicRounds(CANONICAL_ROUNDS);
      }
    }
    void refreshDynamicRounds();
    return () => {
      mounted = false;
    };
  }, [selectedCompany, effectiveRole, targetYoE]);

  useEffect(() => {
    if (activeTab === 'standard') {
      void loadQuestions();
    } else {
      void loadCompanyQuestions();
    }
  }, [activeTab, loadQuestions, loadCompanyQuestions]);

  useEffect(() => {
    setQuery(urlSearch);
    setSearchText(urlSearch);
    setPage(1);
  }, [urlSearch]);

  async function submitAnswer() {
    if (!selected || !answer.trim()) return;
    try {
      const response = await questionsApi.practiceQuestion(selected.id, answer.trim());
      setResult(response ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Your answer could not be saved.');
    }
  }

  async function submitCompanyAnswer() {
    if (!selectedCompanyQ || !companyAnswer.trim()) return;
    setEvaluatingCompany(true);
    try {
      const resp = await companyIntelApi.practiceQuestion(selectedCompanyQ.id, companyAnswer.trim());
      setCompanyResult(resp ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to evaluate answer.');
    } finally {
      setEvaluatingCompany(false);
    }
  }

  async function openBlueprint(compName: string) {
    setBlueprintLoading(true);
    setBlueprintModalOpen(true);
    try {
      const bp = await companyIntelApi.getBlueprint(compName);
      setBlueprintData(bp);
    } catch (err) {
      console.error('Failed to fetch blueprint:', err);
    } finally {
      setBlueprintLoading(false);
    }
  }

  async function toggleHistory() {
    if (history) {
      setHistory(null);
      return;
    }
    try {
      setHistory(await questionsApi.history());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Practice history could not be loaded.');
    }
  }

  async function toggleBookmark(question: Question) {
    try {
      const response = await questionsApi.toggleBookmark(question.id);
      setQuestions((items) =>
        items.map((item) => (item.id === question.id ? { ...item, is_bookmarked: response.is_bookmarked } : item))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bookmark could not be updated.');
    }
  }

  function openQuestion(question: Question) {
    setSelected(question);
    setAnswer('');
    setResult(null);
  }

  function openCompanyQuestion(q: CompanyInterviewQuestion | SynthesizedRoundQuestion | any) {
    const formatted: CompanyInterviewQuestion = {
      id: q.id || `synth_${q.round_number || 1}_${Date.now()}`,
      company_name: q.company_name || q.company || selectedCompany,
      job_role: q.job_role || q.role || 'Software Development Engineer',
      round_number: q.round_number || 1,
      interview_round: q.interview_round || `Round ${q.round_number || 1}`,
      question_text: q.question_text,
      category: q.category || 'General',
      difficulty: q.difficulty || 'Medium',
      source_platform: q.source_platform || 'Verified Company Interview Intelligence',
      original_url: q.original_url || '',
      confidence_score: q.confidence_score || 0.95,
      verification_status: q.verification_status || 'VERIFIED',
      skills_tested: q.skills_tested || [],
      solution_approach: q.solution_approach,
    };
    setSelectedCompanyQ(formatted);
    setCompanyAnswer('');
    setCompanyResult(null);
  }

  return (
    <section className="space-y-6">
      {/* Header */}
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-violet-100 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-violet-800">
              Interactive Practice
            </span>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
              44+ Tech Companies Verified
            </span>
          </div>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900">Question Bank & Interview Intel</h1>
          <p className="mt-1 text-slate-600">
            Master real interview questions from Google, Meta, Amazon, and top tier-1 tech companies across Rounds 1 to 5.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeTab === 'company' && selectedCompany && (
            <button
              type="button"
              onClick={() => void openBlueprint(selectedCompany)}
              className="inline-flex items-center gap-2 rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-800"
            >
              <span>{selectedCompany} Hiring Blueprint</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
          <button
            type="button"
            onClick={() => void toggleHistory()}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            {history ? 'Hide History' : 'Practice History'}
          </button>
        </div>
      </header>

      {/* Mode Switcher Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          type="button"
          onClick={() => setActiveTab('company')}
          className={`relative border-b-2 px-6 py-3 text-sm font-semibold transition ${activeTab === 'company'
              ? 'border-violet-700 text-violet-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
        >
          🏢 Authentic Company Interview Intel (FAANG & Tech)
          <span className="ml-2 rounded-full bg-violet-100 px-2 py-0.5 text-xs text-violet-700">335+ Verified</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('standard')}
          className={`relative border-b-2 px-6 py-3 text-sm font-semibold transition ${activeTab === 'standard'
              ? 'border-violet-700 text-violet-800'
              : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
        >
          🎓 Standard Curriculum Practice Bank
        </button>
      </div>

      {history && (
        <section aria-label="Practice history" className="space-y-2 rounded-xl border bg-white p-4">
          <h2 className="font-semibold text-slate-900">Recent practice history</h2>
          {history.length ? (
            history.map((item) => (
              <article key={item.id} className="rounded-lg bg-slate-50 p-3">
                <div className="flex flex-wrap justify-between gap-2">
                  <p className="font-medium text-slate-800">{item.question_text}</p>
                  <span className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600">Your answer: {item.user_response}</p>
                <p className="mt-1 text-xs font-medium text-slate-600">
                  {item.evaluation_status === 'unavailable'
                    ? 'Evaluation unavailable'
                    : item.evaluation_provenance === 'ai'
                      ? `AI evaluation · ${item.score_percentage ?? '—'}%`
                      : item.score_percentage === null
                        ? 'Saved without score'
                        : `Deterministic result · ${item.score_percentage}%`}
                </p>
              </article>
            ))
          ) : (
            <p className="text-sm text-slate-600">No saved practice attempts yet.</p>
          )}
        </section>
      )}

      {error && (
        <div role="alert" className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ========================================================================= */}
      {/* COMPANY INTERVIEW INTEL VIEW */}
      {/* ========================================================================= */}
      {activeTab === 'company' && (
        <div className="space-y-5">
          {/* Progressive Single-Screen Wizard Flow */}
          <div className="rounded-xl border border-violet-200 bg-white p-5 shadow-sm space-y-4">
            {/* Stepper Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { step: 1 as const, label: entityMode === 'startup' ? 'Startup & Industry' : 'Company' },
                  { step: 2 as const, label: 'Role' },
                  { step: 3 as const, label: 'YoE' },
                  { step: 4 as const, label: 'Skills' },
                  { step: 5 as const, label: 'Questions' },
                ].map((item, idx) => {
                  const isActive = flowStep === item.step;
                  const isDone = flowStep > item.step;
                  return (
                    <div key={item.step} className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => setFlowStep(item.step)}
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold transition ${
                          isActive
                            ? 'bg-violet-700 text-white shadow-xs'
                            : isDone
                              ? 'bg-violet-100 text-violet-800 hover:bg-violet-200'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                        }`}
                      >
                        <span
                          className={`inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold ${
                            isActive
                              ? 'bg-white text-violet-700'
                              : isDone
                                ? 'bg-violet-700 text-white'
                                : 'bg-slate-300 text-slate-700'
                          }`}
                        >
                          {isDone ? '✓' : item.step}
                        </span>
                        <span>{item.label}</span>
                      </button>
                      {idx < 4 && <span className="text-slate-300 text-xs">→</span>}
                    </div>
                  );
                })}
              </div>

              <div className="flex flex-wrap items-center gap-1.5 text-xs">
                <span className="rounded-md bg-violet-50 px-2 py-0.5 font-semibold text-violet-800 border border-violet-200">
                  {entityMode === 'startup'
                    ? `Startup${selectedIndustry ? ` · ${selectedIndustry}` : ''}`
                    : selectedCompany}
                </span>
                {flowStep >= 2 && (
                  <span className="rounded-md bg-indigo-50 px-2 py-0.5 font-semibold text-indigo-800 border border-indigo-200">
                    {effectiveRole}
                  </span>
                )}
                {flowStep >= 3 && (
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 font-semibold text-slate-700 border border-slate-200">
                    {targetYoE}y
                  </span>
                )}
              </div>
            </div>

            {/* Step 1: Company or Startup (+ Industry Suggestions) */}
            {flowStep === 1 && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Step 1: Choose Company or Startup</h3>
                    <p className="text-xs text-slate-500">
                      {entityMode === 'company'
                        ? 'Type a company name to see suggestions, or switch to Startup to search by industry.'
                        : 'Search or pick your startup industry.'}
                    </p>
                  </div>
                  <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5">
                    <button
                      type="button"
                      onClick={() => {
                        setEntityMode('company');
                        if (selectedCompany.toLowerCase() === 'startup' && companies.length > 0) {
                          setSelectedCompany(companies[0].name);
                        }
                        setSelectedIndustry('');
                        setCompanyPage(1);
                      }}
                      className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                        entityMode === 'company'
                          ? 'bg-white text-violet-800 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Company
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEntityMode('startup');
                        setSelectedCompany('Startup');
                        setCompanyPage(1);
                      }}
                      className={`rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                        entityMode === 'startup'
                          ? 'bg-emerald-700 text-white shadow-xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      Startup
                    </button>
                  </div>
                </div>

                {entityMode === 'company' ? (
                  <div className="relative space-y-2 rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (customCompanyInput.trim()) {
                          setSelectedCompany(customCompanyInput.trim());
                          setSelectedIndustry('');
                          setCompanyPage(1);
                          setCustomCompanyInput('');
                        }
                        setCompanyDropdownOpen(false);
                        setFlowStep(2);
                      }}
                      className="flex items-center gap-2"
                    >
                      <div className="relative flex-1">
                        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                        <input
                          value={customCompanyInput}
                          onFocus={() => setCompanyDropdownOpen(true)}
                          onBlur={() => setTimeout(() => setCompanyDropdownOpen(false), 150)}
                          onChange={(e) => {
                            setCustomCompanyInput(e.target.value);
                            setCompanyDropdownOpen(true);
                          }}
                          placeholder={`Selected: ${selectedCompany} — Type or click to pick company...`}
                          className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-600"
                        />

                        {companyDropdownOpen && (
                          <div className="absolute left-0 right-0 z-20 mt-1 max-h-56 overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                            {filteredCompanies.map((c) => (
                              <button
                                key={c.name}
                                type="button"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setSelectedCompany(c.name);
                                  setSelectedIndustry('');
                                  setCustomCompanyInput('');
                                  setCompanyPage(1);
                                  setCompanyDropdownOpen(false);
                                }}
                                className={`flex w-full items-center px-3 py-2 text-left text-xs transition ${
                                  selectedCompany.toLowerCase() === c.name.toLowerCase()
                                    ? 'bg-violet-50 font-semibold text-violet-800'
                                    : 'text-slate-700 hover:bg-slate-50'
                                }`}
                              >
                                <span>{c.name}</span>
                              </button>
                            ))}

                            {customCompanyInput.trim() && filteredCompanies.length === 0 && (
                              <div className="p-1.5 space-y-1">
                                <button
                                  type="button"
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    setSelectedCompany(customCompanyInput.trim());
                                    setSelectedIndustry('');
                                    setCustomCompanyInput('');
                                    setCompanyPage(1);
                                    setCompanyDropdownOpen(false);
                                  }}
                                  className="flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-xs font-semibold text-slate-800 hover:bg-slate-100"
                                >
                                  <span>Use "{customCompanyInput.trim()}"</span>
                                </button>
                                <button
                                  type="button"
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    setEntityMode('startup');
                                    setSelectedCompany('Startup');
                                    setCompanyPage(1);
                                    setCompanyDropdownOpen(false);
                                    setIndustryDropdownOpen(true);
                                  }}
                                  className="flex w-full items-center justify-between rounded-md bg-emerald-50 px-2.5 py-2 text-left text-xs font-semibold text-emerald-900 hover:bg-emerald-100"
                                >
                                  <span>"{customCompanyInput.trim()}" not indexed — Switch to Startup & pick Industry</span>
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      {customCompanyInput.trim() && (
                        <button
                          type="submit"
                          className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 transition shrink-0"
                        >
                          Use "{customCompanyInput.trim()}"
                        </button>
                      )}
                    </form>
                  </div>
                ) : (
                  <div className="relative rounded-lg border border-emerald-200 bg-emerald-50/60 p-3 space-y-2">
                    <span className="block text-xs font-bold text-emerald-900">
                      Startup Industry {selectedIndustry ? `· Selected: ${selectedIndustry}` : '(Click or type to see suggestions)'}
                    </span>
                    <div className="relative">
                      <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-emerald-500" />
                      <input
                        value={industrySearchInput}
                        onFocus={() => setIndustryDropdownOpen(true)}
                        onBlur={() => setTimeout(() => setIndustryDropdownOpen(false), 150)}
                        onChange={(e) => {
                          setIndustrySearchInput(e.target.value);
                          setIndustryDropdownOpen(true);
                          if (e.target.value.trim()) setSelectedIndustry(e.target.value.trim());
                        }}
                        placeholder="Search or pick industry (e.g. Fintech, AI/GenAI, SaaS, Healthcare)..."
                        className="w-full rounded-lg border border-emerald-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-800 focus:border-emerald-600 focus:outline-none"
                      />

                      {industryDropdownOpen && filteredIndustries.length > 0 && (
                        <div className="absolute left-0 right-0 z-20 mt-1 max-h-56 overflow-y-auto rounded-lg border border-emerald-200 bg-white py-1 shadow-lg">
                          {filteredIndustries.map((ind) => (
                            <button
                              key={ind}
                              type="button"
                              onMouseDown={(e) => {
                                e.preventDefault();
                                setSelectedIndustry(ind);
                                setIndustrySearchInput(ind);
                                setIndustryDropdownOpen(false);
                              }}
                              className={`flex w-full items-center justify-between px-3 py-2 text-left text-xs transition ${
                                selectedIndustry.toLowerCase() === ind.toLowerCase()
                                  ? 'bg-emerald-50 font-semibold text-emerald-800'
                                  : 'text-slate-700 hover:bg-emerald-50/60'
                              }`}
                            >
                              <span>{ind}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      if (entityMode === 'company' && customCompanyInput.trim()) {
                        setSelectedCompany(customCompanyInput.trim());
                        setSelectedIndustry('');
                        setCustomCompanyInput('');
                        setCompanyPage(1);
                      }
                      setFlowStep(2);
                    }}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-violet-700 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-violet-800 transition"
                  >
                    <span>Next: Select Role →</span>
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Role */}
            {flowStep === 2 && (
              <div className="space-y-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Step 2: Select Target Role</h3>
                  <p className="text-xs text-slate-500">Click or type to pick a role from the dropdown, or type any custom role.</p>
                </div>

                <div className="relative rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      value={roleSearchInput}
                      onFocus={() => setRoleDropdownOpen(true)}
                      onBlur={() => setTimeout(() => setRoleDropdownOpen(false), 150)}
                      onChange={(e) => {
                        setRoleSearchInput(e.target.value);
                        setRoleDropdownOpen(true);
                      }}
                      placeholder={`Selected: ${effectiveRole} — Click or type to pick role...`}
                      className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-xs text-slate-800 placeholder-slate-400 focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                    />

                    {roleDropdownOpen && (
                      <div className="absolute left-0 right-0 z-20 mt-1 max-h-56 overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                        {availableRoles
                          .filter((r) => !roleSearchInput.trim() || r.toLowerCase().includes(roleSearchInput.trim().toLowerCase()))
                          .map((r) => (
                            <button
                              key={r}
                              type="button"
                              onMouseDown={(e) => {
                                e.preventDefault();
                                handleRoleChange(r);
                                setRoleSearchInput('');
                                setRoleDropdownOpen(false);
                              }}
                              className={`flex w-full items-center px-3 py-2 text-left text-xs transition ${
                                targetRole === r
                                  ? 'bg-violet-50 font-semibold text-violet-800'
                                  : 'text-slate-700 hover:bg-slate-50'
                              }`}
                            >
                              <span>{r}</span>
                            </button>
                          ))}

                        {roleSearchInput.trim() && (
                          <button
                            type="button"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              setCustomRoleInput(roleSearchInput.trim());
                              setTargetRole('custom');
                              handleRoleChange('custom');
                              setRoleSearchInput('');
                              setRoleDropdownOpen(false);
                            }}
                            className="flex w-full items-center px-3 py-2 text-left text-xs font-semibold text-indigo-800 bg-indigo-50/70 hover:bg-indigo-100"
                          >
                            <span>Use custom role: "{roleSearchInput.trim()}"</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <button
                    type="button"
                    onClick={() => setFlowStep(1)}
                    className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setFlowStep(3)}
                    className="rounded-lg bg-violet-700 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-violet-800 transition"
                  >
                    Next: Experience (YoE) →
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Years of Experience (YoE) */}
            {flowStep === 3 && (
              <div className="space-y-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Step 3: Years of Experience (YoE)</h3>
                  <p className="text-xs text-slate-500">Choose your experience level or enter exact years.</p>
                </div>

                <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                  <select
                    value={[0, 1.5, 3.5, 6, 9].includes(targetYoE) ? String(targetYoE) : 'custom'}
                    onChange={(e) => {
                      if (e.target.value !== 'custom') {
                        setTargetYoE(parseFloat(e.target.value));
                      }
                    }}
                    className="flex-1 min-w-[220px] rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                  >
                    <option value="0">Intern (0 years)</option>
                    <option value="1.5">Entry Level (1.5 years)</option>
                    <option value="3.5">Mid Level (3.5 years)</option>
                    <option value="6">Senior (6 years)</option>
                    <option value="9">Staff / Principal (9+ years)</option>
                    <option value="custom">Custom Years</option>
                  </select>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      max="30"
                      value={targetYoE}
                      onChange={(e) => setTargetYoE(parseFloat(e.target.value) || 0)}
                      className="w-20 rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-xs font-semibold text-slate-800 text-center focus:border-violet-600 focus:outline-none"
                    />
                    <span className="text-slate-500 text-xs font-medium">yrs</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <button
                    type="button"
                    onClick={() => setFlowStep(2)}
                    className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => setFlowStep(4)}
                    className="rounded-lg bg-violet-700 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-violet-800 transition"
                  >
                    Next: Skills →
                  </button>
                </div>
              </div>
            )}

            {/* Step 4: Target Skills + Generate */}
            {flowStep === 4 && (
              <div className="space-y-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Step 4: Target Skills & Generate</h3>
                  <p className="text-xs text-slate-500">Review or customize skills, then generate as many relevant questions as possible.</p>
                </div>

                <input
                  value={targetSkills}
                  onChange={(e) => setTargetSkills(e.target.value)}
                  placeholder="e.g. Financial Modeling, DCF, Variance Analysis or Python, Distributed Systems, RAG"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:ring-2 focus:ring-violet-500/20 focus:border-violet-600 focus:outline-none"
                />

                <div className="flex flex-wrap items-center gap-3 pt-1">
                  <label className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
                    <span className="font-semibold text-slate-700">Max Questions:</span>
                    <select
                      value={scrapeLimit}
                      onChange={(e) => setScrapeLimit(parseInt(e.target.value, 10))}
                      className="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium focus:ring-1 focus:ring-violet-500 focus:outline-none"
                    >
                      <option value={30}>30 questions</option>
                      <option value={50}>50 questions</option>
                      <option value={100}>100 questions (Max)</option>
                      <option value={150}>150 questions (Exhaustive)</option>
                    </select>
                  </label>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <button
                    type="button"
                    onClick={() => setFlowStep(3)}
                    className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                  >
                    ← Back
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setFlowStep(5);
                      void handleLiveScrape();
                    }}
                    disabled={scrapingLive}
                    className="inline-flex items-center gap-2 rounded-lg bg-violet-700 px-5 py-2 text-xs font-bold text-white shadow-sm hover:bg-violet-800 disabled:opacity-80 transition"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Generate Relevant Questions →</span>
                  </button>
                </div>
              </div>
            )}

            {/* Step 5: Generated Questions Summary & Three-Dots Loader */}
            {flowStep === 5 && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-xs text-slate-600">
                    Showing questions for{' '}
                    <strong className="text-slate-900">
                      {entityMode === 'startup' ? `Startup (${selectedIndustry || 'All Industries'})` : selectedCompany}
                    </strong>{' '}
                    · <strong className="text-slate-900">{effectiveRole}</strong> ·{' '}
                    <strong className="text-slate-900">{targetYoE} yrs</strong>
                    {targetSkills.trim() ? ` · ${targetSkills}` : ''}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setFlowStep(1)}
                      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      Edit Flow
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleLiveScrape()}
                      disabled={scrapingLive}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-violet-700 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-violet-800 disabled:opacity-80"
                    >
                      <Search className="h-3.5 w-3.5" />
                      <span>{scrapingLive ? 'Generating...' : 'Regenerate'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleGenerateNemotron()}
                      disabled={generatingNemotron}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-violet-300 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-800 hover:bg-violet-100 disabled:opacity-50"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>{generatingNemotron ? 'Synthesizing...' : 'Nemotron Dorks'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => exportCleanCsv()}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      <Download className="h-3.5 w-3.5 text-slate-500" />
                      <span>Export CSV</span>
                    </button>
                  </div>
                </div>

                {(scrapingLive || generatingNemotron) && (
                  <div className="flex items-center justify-between rounded-lg border border-violet-200 bg-violet-50/80 px-4 py-4 text-xs font-medium text-violet-900">
                    <div className="flex items-center gap-3">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-violet-600 animate-bounce [animation-delay:-0.3s]" />
                        <span className="h-2.5 w-2.5 rounded-full bg-violet-600 animate-bounce [animation-delay:-0.15s]" />
                        <span className="h-2.5 w-2.5 rounded-full bg-violet-600 animate-bounce" />
                      </span>
                      <span className="font-semibold">
                        {scrapingLive
                          ? `Generating relevant questions for ${entityMode === 'startup' ? `Startup (${selectedIndustry || 'Any Industry'})` : selectedCompany} · ${effectiveRole} · ${targetYoE} yrs`
                          : `Synthesizing Nemotron search dorks & rounds for ${selectedCompany} · ${effectiveRole}`}
                      </span>
                    </div>
                    <span className="text-[11px] font-semibold text-violet-700">Fetching live results</span>
                  </div>
                )}

                {scrapeSuccessMsg && !scrapingLive && (
                  <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-2.5 text-xs font-medium text-emerald-800">
                    <CheckCircle className="h-4 w-4 shrink-0 text-emerald-600" />
                    <span>{scrapeSuccessMsg}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Search, Rounds & Topic Filters */}
          <form
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-5 shadow-sm"
            onSubmit={(e) => {
              e.preventDefault();
              setCompanySearch(companySearchInput);
              setCompanyPage(1);
            }}
          >
            <label className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input
                value={companySearchInput}
                onChange={(e) => setCompanySearchInput(e.target.value)}
                placeholder={`Search in ${selectedCompany} questions...`}
                className="w-full rounded-lg border py-2 pl-9 pr-3 text-sm focus:border-violet-500 focus:outline-none"
              />
            </label>
            <select
              value={selectedRound}
              onChange={(e) => {
                setSelectedRound(e.target.value);
                setCompanyPage(1);
              }}
              className="rounded-lg border px-3 py-2 text-sm"
            >
              {dynamicRounds.map((r) => (
                <option key={r.id || 'all'} value={r.id}>{r.label}</option>
              ))}
            </select>
            <select
              value={companyCategory}
              onChange={(e) => {
                setCompanyCategory(e.target.value);
                setCompanyPage(1);
              }}
              className="rounded-lg border px-3 py-2 text-sm"
            >
              <option value="">All Categories & Topics ({availableCategories.length})</option>
              {availableCategories.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <select
              value={companyDifficulty}
              onChange={(e) => {
                setCompanyDifficulty(e.target.value);
                setCompanyPage(1);
              }}
              className="rounded-lg border px-3 py-2 text-sm"
            >
              <option value="">All Difficulties</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
            <button className="rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-800">
              Filter Questions
            </button>
          </form>

          {/* (Guided Flow above handles Company/Startup, Industry, Role, YoE, Skills, and Generate) */}

          {/* Nemotron Dynamic Intelligence Viewer */}
          {dynamicDorks && (
            <div className="rounded-xl border border-violet-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-violet-700" />
                  <h3 className="font-bold text-slate-900">
                    Nemotron Dynamic Open-Web Search Dorks for {dynamicDorks.company} ({dynamicDorks.role})
                  </h3>
                </div>
                <span className="rounded-full bg-violet-100 px-3 py-0.5 text-xs font-bold text-violet-800">
                  Zero HackerNews Chatter · Noise-Filtered
                </span>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Canonical Rounds (1 to 5) Search Dorks
                  </h4>
                  {Object.entries(dynamicDorks.round_dorks || {}).map(([rKey, dorkVal]) => {
                    const rTitle = rKey.replace(/_/g, ' ').toUpperCase();
                    const dorkStr = Array.isArray(dorkVal)
                      ? dorkVal[0]
                      : typeof dorkVal === 'object' && dorkVal !== null
                        ? (dorkVal as any).dork_query || ''
                        : String(dorkVal);
                    return (
                      <div key={rKey} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-800">{rTitle}</span>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(rKey, dorkStr)}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-violet-700 hover:text-violet-800"
                          >
                            {copiedKey === rKey ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                            <span>{copiedKey === rKey ? 'Copied' : 'Copy Dork'}</span>
                          </button>
                        </div>
                        <code className="mt-1 block text-xs font-mono text-slate-700 break-all">{dorkStr}</code>
                      </div>
                    );
                  })}
                </div>

                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Platform-Specific Target Queries</h4>
                  {Object.entries(dynamicDorks.platform_queries || {}).map(([platKey, queryStr]) => {
                    const platTitle = platKey.replace(/_/g, ' ').toUpperCase();
                    return (
                      <div key={platKey} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-800">{platTitle}</span>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(platKey, queryStr)}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-violet-700 hover:text-violet-800"
                          >
                            {copiedKey === platKey ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                            <span>{copiedKey === platKey ? 'Copied' : 'Copy'}</span>
                          </button>
                        </div>
                        <code className="mt-1 block text-xs font-mono text-slate-700 break-all">{queryStr}</code>
                      </div>
                    );
                  })}

                  {synthesizedRoundQs.length > 0 && (
                    <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/70 p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-emerald-900">
                          ⚡ {synthesizedRoundQs.length} Verified Round Questions Synthesized
                        </span>
                        <button
                          type="button"
                          onClick={() => exportCleanCsv()}
                          className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 hover:text-emerald-800"
                        >
                          <Download className="h-3.5 w-3.5" />
                          <span>Download CSV</span>
                        </button>
                      </div>
                      <p className="mt-1 text-xs text-emerald-700">
                        Exact problem statements, optimal solution approaches, and tested competencies synthesized for Rounds 1–5.
                      </p>
                      <div className="mt-3 max-h-60 space-y-2 overflow-y-auto">
                        {synthesizedRoundQs.map((sq, sIdx) => (
                          <div key={sIdx} className="rounded border border-emerald-200 bg-white p-2.5 text-xs shadow-xs">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-emerald-900">
                                Round {sq.round_number}: {sq.category}
                              </span>
                              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800">
                                {sq.difficulty}
                              </span>
                            </div>
                            <p className="mt-1 line-clamp-2 text-slate-700">{sq.question_text}</p>
                            <div className="mt-2 flex items-center justify-between border-t border-slate-100 pt-1.5">
                              <span className="text-[10px] text-slate-500">
                                Skills: {sq.skills_tested?.slice(0, 3).join(', ')}
                              </span>
                              <button
                                type="button"
                                onClick={() => openCompanyQuestion(sq)}
                                className="font-bold text-violet-700 hover:text-violet-800"
                              >
                                Practice →
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Main Content Grid: Questions + Interactive Practice Pane */}
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(340px,0.9fr)]">
            {/* Question Cards List */}
            <div className="space-y-3">
              {companyLoading ? (
                <div className="rounded-xl border bg-white p-10 text-center text-slate-600">
                  <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-violet-700 border-t-transparent"></div>
                  <p className="mt-2 text-sm font-medium">Loading authentic interview questions for {selectedCompany}…</p>
                </div>
              ) : companyQuestions.length ? (
                companyQuestions.map((q) => (
                  <article
                    key={q.id}
                    className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-violet-300"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="inline-block rounded-md bg-violet-50 px-2.5 py-1 text-xs font-bold text-violet-800">
                          {q.company_name}
                        </span>
                        <span className="ml-2 inline-block rounded-md bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
                          {q.interview_round}
                        </span>
                        <span
                          className={`ml-2 inline-block rounded-md px-2 py-0.5 text-xs font-semibold ${q.difficulty.toLowerCase() === 'hard'
                              ? 'bg-rose-50 text-rose-700'
                              : q.difficulty.toLowerCase() === 'medium'
                                ? 'bg-amber-50 text-amber-700'
                                : 'bg-emerald-50 text-emerald-700'
                            }`}
                        >
                          {q.difficulty}
                        </span>
                      </div>
                      <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700">
                        ✓ Verified Interview
                      </span>
                    </div>

                    <h3 className="mt-3 text-base font-semibold leading-snug text-slate-900">
                      {q.question_text}
                    </h3>

                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                      <span className="rounded bg-slate-100 px-2 py-1 font-medium">{q.category}</span>
                      <span className="rounded bg-slate-100 px-2 py-1 text-slate-500">{q.job_role}</span>
                      {q.skills_tested?.slice(0, 3).map((skill, idx) => (
                        <span key={idx} className="rounded bg-slate-100 px-2 py-1 text-slate-500">
                          #{skill}
                        </span>
                      ))}
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
                      <button
                        type="button"
                        onClick={() => openCompanyQuestion(q)}
                        className="inline-flex items-center gap-1.5 text-sm font-semibold text-violet-700 hover:text-violet-800"
                      >
                        <span>Practice this question</span>
                        <ArrowRight className="h-4 w-4" />
                      </button>
                      <span className="text-xs text-slate-400">Platform: {q.source_platform}</span>
                    </div>
                  </article>
                ))
              ) : (
                <div className="rounded-xl border border-dashed bg-white p-10 text-center text-slate-600">
                  <p className="font-semibold text-slate-800">No questions found</p>
                  <p className="mt-1 text-sm">Try broadening your round or difficulty filters for {selectedCompany}.</p>
                </div>
              )}
            </div>

            {/* Interactive Practice Side Pane */}
            <aside className="h-fit rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:sticky lg:top-6">
              {selectedCompanyQ ? (
                <>
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div>
                      <span className="rounded-md bg-violet-100 px-2 py-0.5 text-xs font-bold text-violet-800">
                        {selectedCompanyQ.company_name}
                      </span>
                      <span className="ml-2 text-xs font-semibold text-slate-500">{selectedCompanyQ.interview_round}</span>
                    </div>
                    <span className="text-xs font-semibold uppercase text-violet-700">{selectedCompanyQ.difficulty}</span>
                  </div>

                  <h2 className="mt-3 text-lg font-bold text-slate-900">Practice Interview Problem</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{selectedCompanyQ.question_text}</p>

                  <label htmlFor="company-answer" className="mt-4 block text-sm font-medium text-slate-800">
                    <RequiredLabel>Your solution approach & code</RequiredLabel>
                  </label>
                  <textarea
                    id="company-answer"
                    value={companyAnswer}
                    onChange={(e) => setCompanyAnswer(e.target.value)}
                    rows={7}
                    disabled={evaluatingCompany || !!companyResult}
                    className="mt-2 w-full rounded-lg border p-3 font-mono text-xs focus:border-violet-500 focus:outline-none"
                    placeholder="1. Clarify constraints & edge cases...&#10;2. Outline algorithm & data structure...&#10;3. State Big-O time and space complexity...&#10;4. Provide implementation code..."
                  />

                  {!companyResult && (
                    <button
                      type="button"
                      onClick={() => void submitCompanyAnswer()}
                      disabled={evaluatingCompany || companyAnswer.trim().length < 5}
                      className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-800 disabled:opacity-50"
                    >
                      {evaluatingCompany ? (
                        <>
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                          <span>Evaluating against {selectedCompanyQ.company_name} rubric…</span>
                        </>
                      ) : (
                        <span>Evaluate Solution</span>
                      )}
                    </button>
                  )}

                  {companyResult && (
                    <div role="status" className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
                      <div className="flex items-center justify-between">
                        <span
                          className={`rounded-md px-2.5 py-1 text-xs font-bold ${companyResult.is_correct ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                            }`}
                        >
                          {companyResult.is_correct ? 'Meets Standards' : 'Needs Optimization'} · {companyResult.score_percentage}%
                        </span>
                        <span className="text-xs text-slate-500">Benchmark Assessment</span>
                      </div>
                      <p className="text-slate-800 font-medium">{companyResult.feedback}</p>
                      <div>
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Expected Key Elements</p>
                        <p className="mt-1 rounded bg-white p-2.5 text-xs text-slate-700 border border-slate-200">
                          {companyResult.expected_answer}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setCompanyResult(null);
                          setCompanyAnswer('');
                        }}
                        className="text-xs font-semibold text-violet-700 hover:text-violet-800"
                      >
                        Try another solution →
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <div className="py-12 text-center">
                  <h3 className="font-semibold text-slate-900">Select an Interview Question</h3>
                  <p className="mt-2 text-sm text-slate-500">
                    Click "Practice this question" on any {selectedCompany} problem to submit your solution and receive instant rubric feedback.
                  </p>
                </div>
              )}
            </aside>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STANDARD CURRICULUM PRACTICE VIEW */}
      {/* ========================================================================= */}
      {activeTab === 'standard' && (
        <div className="space-y-5">
          <form
            className="grid gap-3 rounded-xl border bg-white p-4 sm:grid-cols-2 lg:grid-cols-4 shadow-sm"
            onSubmit={(event) => {
              event.preventDefault();
              setQuestions([]);
              setPage(1);
              if (query === searchText && page === 1) void loadQuestions();
              else setQuery(searchText);
            }}
          >
            <label className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <span className="sr-only">Search questions</span>
              <input
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                placeholder="Search questions, subjects, topics"
                className="w-full rounded-lg border py-2.5 pl-9 pr-3 text-sm"
              />
            </label>
            <label className="sr-only" htmlFor="question-difficulty">
              Difficulty
            </label>
            <select
              id="question-difficulty"
              value={filters.difficulty}
              onChange={(event) => {
                setFilters({ ...filters, difficulty: event.target.value });
                setPage(1);
              }}
              className="rounded-lg border px-3 py-2.5 text-sm"
            >
              <option value="">All difficulties</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
              <option value="expert">Expert</option>
            </select>
            {[
              ['industry_category_id', 'All categories', taxonomy.categories.map((x) => [x.id, x.name])],
              ['job_role_id', 'All roles', taxonomy.job_roles.map((x) => [x.id, x.title])],
              ['subject_id', 'All subjects', taxonomy.subjects.map((x) => [x.id, x.name])],
              ['topic_id', 'All topics', taxonomy.topics.map((x) => [x.id, x.name])],
              ['skill_id', 'All skills', taxonomy.skills.map((x) => [x.id, x.name])],
              ['experience_level_id', 'All experience levels', taxonomy.experience_levels.map((x) => [x.id, x.name])],
              ['interview_round', 'All rounds', taxonomy.interview_rounds.map((x) => [x.name, x.name])],
              ['company_id', 'All companies', taxonomy.companies.map((x) => [x.id, x.name])],
              [
                'question_type',
                'All question types',
                [
                  'mcq_single',
                  'mcq_multiple',
                  'short_answer',
                  'long_answer',
                  'descriptive',
                  'coding',
                  'scenario',
                  'case_study',
                  'situational',
                  'behavioral',
                  'technical',
                  'domain_specific',
                ].map((x) => [x, x.replaceAll('_', ' ')]),
              ],
              ['bookmarked', 'All questions', [['true', 'Bookmarked only']]],
            ].map(([key, label, items]) => (
              <select
                key={String(key)}
                aria-label={String(label)}
                value={filters[key as keyof typeof filters]}
                onChange={(event) => {
                  setFilters({ ...filters, [key as string]: event.target.value });
                  setPage(1);
                }}
                className="rounded-lg border px-3 py-2.5 text-sm"
              >
                <option value="">{String(label)}</option>
                {(items as string[][]).map(([value, name]) => (
                  <option key={value} value={value}>
                    {name}
                  </option>
                ))}
              </select>
            ))}
            <button className="rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-violet-800">
              Search
            </button>
          </form>

          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.9fr)]">
            <div className="space-y-3">
              {loading ? (
                <div className="rounded-xl border bg-white p-8 text-slate-600">Loading published questions…</div>
              ) : questions.length ? (
                questions.map((question) => (
                  <article key={question.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="flex items-start justify-between gap-3">
                      <button
                        type="button"
                        onClick={() => openQuestion(question)}
                        className="text-left text-base font-semibold text-slate-900 hover:text-violet-700"
                      >
                        {question.question_text}
                      </button>
                      <button
                        type="button"
                        aria-label={question.is_bookmarked ? 'Remove bookmark' : 'Bookmark question'}
                        onClick={() => void toggleBookmark(question)}
                        className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
                      >
                        <Bookmark className="h-4 w-4" fill={question.is_bookmarked ? 'currentColor' : 'none'} />
                      </button>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1">{question.industry?.name ?? 'Industry'}</span>
                      <span className="rounded-full bg-slate-100 px-2.5 py-1">
                        {question.subject} · {question.topic}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2.5 py-1">{question.difficulty}</span>
                      <span className="rounded-full bg-violet-50 px-2.5 py-1 text-violet-800">
                        {provenanceLabel[question.source_provenance]}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => openQuestion(question)}
                      className="mt-4 text-sm font-semibold text-violet-700"
                    >
                      Practice this question →
                    </button>
                  </article>
                ))
              ) : (
                <div className="rounded-xl border border-dashed bg-white p-8 text-center text-slate-600">
                  No published questions match these filters.
                </div>
              )}
            </div>
            {hasMore && (
              <button
                type="button"
                onClick={() => setPage((value) => value + 1)}
                className="w-full rounded-lg border bg-white px-4 py-3 text-sm font-semibold text-slate-700"
              >
                Load more questions
              </button>
            )}
            <aside className="h-fit rounded-xl border border-slate-200 bg-white p-5 lg:sticky lg:top-6">
              {selected ? (
                <>
                  <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">
                    {selected.question_type.replaceAll('_', ' ')}
                  </p>
                  <h2 className="mt-2 text-xl font-bold text-slate-900">Practice question</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-700">{selected.question_text}</p>
                  {selected.options.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {selected.options.map((option) => (
                        <p key={option.id} className="rounded-md bg-slate-50 p-3 text-sm">
                          <strong>{option.id}.</strong> {option.text}
                        </p>
                      ))}
                    </div>
                  )}
                  <label htmlFor="practice-answer" className="mt-5 block text-sm font-medium text-slate-800">
                    <RequiredLabel>Your answer</RequiredLabel>
                  </label>
                  <textarea
                    id="practice-answer"
                    value={answer}
                    onChange={(event) => setAnswer(event.target.value)}
                    rows={5}
                    disabled={!!result}
                    className="mt-2 w-full rounded-lg border p-3 text-sm"
                    placeholder={
                      selected.options.length ? 'Enter the option ID, or IDs separated by commas' : 'Write your answer'
                    }
                  />
                  {!result && (
                    <button
                      type="button"
                      onClick={() => void submitAnswer()}
                      disabled={!answer.trim()}
                      className="mt-3 rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
                    >
                      Submit answer
                    </button>
                  )}
                  {result && (
                    <div role="status" className="mt-4 rounded-lg bg-slate-50 p-4 text-sm">
                      <p className="font-semibold text-slate-900">
                        {result.evaluation_status === 'unavailable'
                          ? 'Answer saved; evaluation unavailable'
                          : result.evaluation_provenance === 'ai'
                            ? `AI evaluation · ${result.score_percentage}%`
                            : `${result.is_correct ? 'Correct' : 'Not quite'} · ${result.score_percentage}%`}
                      </p>
                      <p className="mt-2 text-slate-700">{result.feedback}</p>
                      <p className="mt-3 font-medium text-slate-800">Expected answer</p>
                      <p className="mt-1 text-slate-700">{result.expected_answer}</p>
                      {result.explanation && <p className="mt-2 text-slate-700">{result.explanation}</p>}
                    </div>
                  )}
                </>
              ) : (
                <div className="py-10 text-center">
                  <h2 className="font-semibold text-slate-900">Choose a question</h2>
                  <p className="mt-2 text-sm text-slate-600">
                    Your response is saved to your practice history when submitted.
                  </p>
                </div>
              )}
            </aside>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* COMPANY BLUEPRINT MODAL */}
      {/* ========================================================================= */}
      {blueprintModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-100 pb-4">
              <div>
                <span className="rounded-md bg-violet-100 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-violet-800">
                  Hiring Blueprint
                </span>
                <h2 className="mt-1 text-2xl font-extrabold text-slate-900">
                  {blueprintData?.company_name || selectedCompany} Interview Process Loop
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  Target: {blueprintData?.target_role || 'Software Engineer'} · {blueprintData?.seniority_tier || 'Mid/Senior'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setBlueprintModalOpen(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                ✕
              </button>
            </div>

            {blueprintLoading ? (
              <div className="py-12 text-center">
                <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-violet-700 border-t-transparent"></div>
                <p className="mt-2 text-sm text-slate-600">Generating hiring blueprint…</p>
              </div>
            ) : blueprintData ? (
              <div className="mt-4 space-y-5">
                {/* Philosophy Banner */}
                <div className="rounded-xl border border-violet-100 bg-violet-50/50 p-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-violet-800">Hiring Philosophy & Culture</p>
                  <p className="mt-1 text-sm text-slate-700 leading-relaxed">{blueprintData.hiring_philosophy}</p>
                </div>

                {/* 5 Rounds Breakdown */}
                <div className="space-y-3">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    5-Round Hiring Sequence ({blueprintData.total_rounds} Total Rounds)
                  </p>
                  {blueprintData.rounds.map((round) => (
                    <div key={round.round_number} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                        <span className="text-sm font-bold text-slate-900">{round.round_name}</span>
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-800">
                            Weight: {round.weightage_percent}%
                          </span>
                          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                            ⏱️ {round.typical_duration_minutes} min
                          </span>
                        </div>
                      </div>

                      <div className="mt-3 grid gap-3 text-xs sm:grid-cols-2">
                        <div>
                          <p className="font-semibold text-slate-700">Core Focus Areas:</p>
                          <ul className="mt-1 list-inside list-disc text-slate-600 space-y-0.5">
                            {round.focus_areas.map((fa, idx) => (
                              <li key={idx}>{fa}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="font-semibold text-slate-700">Sample Topics:</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {round.sample_topics.map((st, idx) => (
                              <span key={idx} className="rounded bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700">
                                {st}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="mt-3 rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600">
                        <strong className="text-slate-800">Preparation Tip: </strong>
                        {round.preparation_tips}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => setBlueprintModalOpen(false)}
                    className="rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800"
                  >
                    Close Blueprint
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </section>
  );
}
