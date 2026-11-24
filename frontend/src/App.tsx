import { lazy, Suspense } from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AuthLayout } from './layouts/AuthLayout';
import { DashboardLayout } from './layouts/DashboardLayout';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { RouteErrorBoundary } from './components/common/RouteErrorBoundary';

const DashboardPage = lazy(() => import('./pages/dashboard/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const OnboardingWizard = lazy(() => import('./pages/onboarding/OnboardingWizard').then((module) => ({ default: module.OnboardingWizard })));
const ResumeLibraryPage = lazy(() => import('./pages/resume/ResumeLibraryPage').then((module) => ({ default: module.ResumeLibraryPage })));
const ResumeDetailPage = lazy(() => import('./pages/resume/ResumeDetailPage').then((module) => ({ default: module.ResumeDetailPage })));
const QuestionBankPage = lazy(() => import('./pages/questions/QuestionBankPage').then((module) => ({ default: module.QuestionBankPage })));
const ModulesPage = lazy(() => import('./pages/modules/ModulesPage').then((module) => ({ default: module.ModulesPage })));
const QuestionManagementPage = lazy(() => import('./pages/admin/QuestionManagementPage').then((module) => ({ default: module.QuestionManagementPage })));
const CoachPage = lazy(() => import('./pages/coach/CoachPage').then((module) => ({ default: module.CoachPage })));
const TestingPage = lazy(() => import('./pages/testing/TestingPage').then((module) => ({ default: module.TestingPage })));
const InterviewPage = lazy(() => import('./pages/interviews/InterviewPage').then((module) => ({ default: module.InterviewPage })));
const AdminConsolePage = lazy(() => import('./pages/admin/AdminConsolePage').then((module) => ({ default: module.AdminConsolePage })));
const ReportsPage = lazy(() => import('./pages/reports/ReportsPage').then((module) => ({ default: module.ReportsPage })));
const ModuleManagementPage = lazy(() => import('./pages/admin/ModuleManagementPage').then((module) => ({ default: module.ModuleManagementPage })));
const QuestionTaxonomyPage = lazy(() => import('./pages/admin/QuestionTaxonomyPage').then((module) => ({ default: module.QuestionTaxonomyPage })));
const SettingsPage = lazy(() => import('./pages/settings/SettingsPage').then((module) => ({ default: module.SettingsPage })));

function UnavailablePage() {
  const location = useLocation();
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-8">
      <h1 className="text-xl font-semibold text-slate-900">This section is not available yet</h1>
      <p className="mt-2 text-sm text-slate-600">{location.pathname} is planned for a later implementation phase.</p>
      <Link className="mt-5 inline-flex text-sm font-semibold text-violet-700 hover:underline" to="/dashboard">Return to dashboard</Link>
    </section>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <RouteErrorBoundary>
          <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><LoadingSpinner size="lg" message="Loading your workspace..." /></div>}>
            <Routes>
              <Route element={<AuthLayout />}>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
              </Route>
              <Route element={<DashboardLayout />}>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/onboarding" element={<OnboardingWizard />} />
                <Route path="/profile" element={<OnboardingWizard />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/resume" element={<ResumeLibraryPage />} />
                <Route path="/resume/:resumeId" element={<ResumeDetailPage />} />
                <Route path="/resume/:resumeId/analysis" element={<ResumeDetailPage />} />
                <Route path="/resume/:resumeId/enhancement" element={<ResumeDetailPage />} />
                <Route path="/resume/:resumeId/versions" element={<ResumeDetailPage />} />
                <Route path="/question-bank" element={<QuestionBankPage />} />
                <Route path="/modules" element={<ModulesPage />} />
                <Route path="/admin/questions" element={<QuestionManagementPage />} />
                <Route path="/coach" element={<CoachPage />} />
                <Route path="/roadmap" element={<CoachPage />} />
                <Route path="/testing" element={<TestingPage />} />
                <Route path="/interviews" element={<InterviewPage />} />
                <Route path="/admin" element={<AdminConsolePage />} />
                <Route path="/admin/modules" element={<ModuleManagementPage />} />
                <Route path="/admin/question-taxonomy" element={<QuestionTaxonomyPage />} />
                <Route path="/reports" element={<ReportsPage />} />
              </Route>
              <Route path="*" element={<UnavailablePage />} />
            </Routes>
          </Suspense>
        </RouteErrorBoundary>
      </AuthProvider>
    </BrowserRouter>
  );
}
