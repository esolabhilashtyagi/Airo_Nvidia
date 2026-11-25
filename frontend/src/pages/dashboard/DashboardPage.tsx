import React, { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { dashboardApi } from '../../api/services';
import type { DashboardOverview } from '../../types';
import { MetricCard } from '../../components/common/MetricCard';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import {
  Sparkles, ArrowRight, Bot, FileText, Award, Video, HelpCircle, UserRound
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const DashboardCharts = lazy(() => import('./DashboardCharts').then((module) => ({ default: module.DashboardCharts })));

function DeferredDashboardCharts(props: React.ComponentProps<typeof DashboardCharts>) {
  const container = useRef<HTMLDivElement>(null);
  const [shouldLoad, setShouldLoad] = useState(false);

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setShouldLoad(true);
        observer.disconnect();
      }
    }, { rootMargin: '160px' });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={container} className="min-h-[20rem]">
      {shouldLoad ? <Suspense fallback={<div className="grid min-h-[20rem] place-items-center text-sm text-slate-500" role="status">Loading analytics charts…</div>}><DashboardCharts {...props} /></Suspense> : <div className="grid min-h-[20rem] place-items-center text-sm text-slate-500" aria-label="Analytics charts load when visible">Scroll to view your activity charts</div>}
    </div>
  );
}

export const DashboardPage: React.FC = () => {
  const { user, profile } = useAuth();
  const onboardingCompleted = profile?.onboarding_completed;
  const profileIncomplete = user?.role === 'candidate' && !onboardingCompleted;
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const targetRole = profile?.target_role || overview?.target_role;
  const targetIndustry = profile?.industry?.name || overview?.industry_name || 'your selected industry';

  useEffect(() => {
    if (profileIncomplete) return;
    let active = true;
    setIsLoading(true);
    setError(null);
    setOverview(null);
    setAnalytics(null);
    const loadDashboard = async () => {
      try {
        const [ovData, anData] = await Promise.all([
          dashboardApi.getOverview(),
          dashboardApi.getAnalytics(),
        ]);
        if (active) {
          setOverview(ovData);
          setAnalytics(anData);
        }
      } catch (err: any) {
        if (active) setError(err.message || 'Failed to load dashboard overview');
      } finally {
        if (active) setIsLoading(false);
      }
    };
    loadDashboard();
    return () => { active = false; };
  }, [user?.id, profileIncomplete]);

  if (isLoading) {
    return <LoadingSpinner size="lg" message="Loading candidate metrics and analytics..." />;
  }

  if (profileIncomplete) {
    return <section className="mx-auto max-w-2xl rounded-2xl border border-violet-200 bg-white p-8 text-center shadow-sm">
      <UserRound className="mx-auto h-10 w-10 text-violet-700" />
      <h1 className="mt-4 text-2xl font-bold text-slate-900">Complete your profile first</h1>
      <p className="mt-2 text-slate-600">Your learning plan, coach recommendations, and practice activities will be personalized after you finish the profile setup.</p>
      <Link to="/profile" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-violet-700 px-5 py-3 font-semibold text-white">Continue profile setup <ArrowRight className="h-4 w-4" /></Link>
    </section>;
  }

  if (error) {
    return <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">Dashboard data could not be loaded: {error}</div>;
  }

  return (
    <div className="space-y-8">
      {/* Welcome & Target Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-violet-100 bg-gradient-to-br from-violet-50 via-white to-indigo-50 p-6 text-slate-900 shadow-sm shadow-violet-950/5 sm:p-8">
        <div aria-hidden="true" className="pointer-events-none absolute -right-20 -top-28 h-72 w-72 rounded-full bg-violet-200/30 blur-3xl" />
        <div className="relative z-10 max-w-2xl">
          <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-white/80 px-3 py-1 text-xs font-semibold text-violet-800">
            <Sparkles className="w-3.5 h-3.5" />
            Career Preparation Overview
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
            Welcome back, {user?.full_name?.split(' ')[0] || 'Candidate'}!
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {targetRole
              ? <>Targeting <span className="font-semibold text-violet-800">{targetRole}</span> in <span className="font-semibold text-slate-900">{targetIndustry}</span>.</>
              : <>Choose a target role to personalize your preparation in <span className="font-semibold text-slate-900">{targetIndustry}</span>.</>}
            {' '}Your preparation metrics are summarized below.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/coach"
              className="inline-flex items-center gap-1.5 rounded-lg bg-violet-700 px-4 py-2 text-xs font-bold text-white shadow-sm shadow-violet-900/10 transition-colors hover:bg-violet-800"
            >
              <Bot className="w-4 h-4" /> Consult Career Coach
            </Link>
            <Link
              to="/testing"
              className="inline-flex items-center gap-1.5 rounded-lg border border-violet-200 bg-white/80 px-4 py-2 text-xs font-semibold text-slate-700 transition-colors hover:border-violet-300 hover:bg-white"
            >
              Start Timed Test <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {overview?.metrics?.map((metric, i) => (
          <MetricCard
            key={i}
            title={metric.title}
            value={metric.value}
            changeText={metric.change_text}
            changeType={metric.change_type}
            iconName={metric.icon}
          />
        ))}
      </div>

      <DeferredDashboardCharts
        weeklyActivity={analytics?.weekly_activity ?? []}
        scoreHistory={analytics?.score_history ?? []}
        totalPracticeCount={analytics?.total_practice_count ?? 0}
      />

      {/* Explainable Readiness Methodology Section */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Award className="w-5 h-5 text-violet-600" />
          <h3 className="text-sm font-bold text-slate-900">How your readiness estimate is calculated</h3>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Weighted average of available evidence. Missing assessments are excluded, not counted as zero. Current evidence coverage: {overview?.readiness_factors?.coverage_percent ?? 0}%.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(overview?.readiness_factors?.components ?? {}).map(([key, component]) => (
            <div key={key} className="p-3 bg-slate-50 rounded-lg border border-slate-200/60">
              <span className="text-[11px] font-semibold text-slate-500 uppercase">{component.label}</span>
              <p className="text-xs font-bold text-slate-900 mt-1">{component.weight_percent}% weight · {component.included ? `${component.score_percent}%` : 'Not assessed'}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">{component.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended Next Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-9 h-9 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center mb-3">
              <FileText className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-slate-900 text-sm">Resume Intelligence</h4>
            <p className="text-xs text-slate-500 mt-1">Upload your resume for structured feedback and role-specific suggestions.</p>
          </div>
          <Link to="/resume" className="mt-4 text-xs font-bold text-violet-600 hover:text-violet-700 flex items-center gap-1">
            Open Resume Studio <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-9 h-9 rounded-lg bg-violet-50 text-violet-700 flex items-center justify-center mb-3">
              <HelpCircle className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-slate-900 text-sm">Centralized Question Bank</h4>
            <p className="text-xs text-slate-500 mt-1">Browse practice questions by industry, role, and difficulty.</p>
          </div>
          <Link to="/question-bank" className="mt-4 text-xs font-bold text-violet-700 hover:text-violet-800 flex items-center gap-1">
            Browse Questions <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="w-9 h-9 rounded-lg bg-violet-50 text-violet-700 flex items-center justify-center mb-3">
              <Video className="w-5 h-5" />
            </div>
            <h4 className="font-semibold text-slate-900 text-sm">Mock Interview</h4>
            <p className="text-xs text-slate-500 mt-1">Practice role-focused technical and behavioral interview questions.</p>
          </div>
          <Link to="/interviews" className="mt-4 text-xs font-bold text-violet-700 hover:text-violet-800 flex items-center gap-1">
            Launch Simulation <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </div>
  );
};
