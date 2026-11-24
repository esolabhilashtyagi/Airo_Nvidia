import React, { useState } from 'react';
import { Outlet, Navigate, Link, useLocation } from 'react-router-dom';
import { Sidebar } from '../components/common/Sidebar';
import { Navbar } from '../components/common/Navbar';
import { useAuth } from '../context/AuthContext';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { AlertCircle, ArrowRight } from 'lucide-react';

export const DashboardLayout: React.FC = () => {
  const { user, profile, isLoading, isAuthenticated } = useAuth();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#faf9ff]">
        <LoadingSpinner size="lg" message="Loading your Aairo workspace..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const profileSetupAllowed = ['/profile', '/onboarding', '/settings'].includes(location.pathname);
  if (user?.role === 'candidate' && !profile?.onboarding_completed && !profileSetupAllowed) {
    return <Navigate to="/profile" replace state={{ profileIncomplete: true, from: location.pathname }} />;
  }

  return (
    <div className="flex min-h-screen bg-[#faf9ff]">
      <Sidebar mobileOpen={mobileSidebarOpen} onNavigate={() => setMobileSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar onMenuClick={() => setMobileSidebarOpen(true)} />

        {/* Onboarding Incomplete Alert Banner */}
        {user?.role === 'candidate' && profile && !profile.onboarding_completed && (
          <div className="bg-purple-50 border-b border-purple-200 px-6 py-2.5 flex items-center justify-between text-xs text-purple-900">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-purple-600 shrink-0" />
              <span>
                Your onboarding profile is incomplete (Step {profile.onboarding_step || 1} of 7). Complete it to unlock personalized AI recommendations.
              </span>
            </div>
            <Link
              to="/onboarding"
              className="inline-flex items-center gap-1 font-semibold text-purple-700 hover:text-purple-800 underline"
            >
              Resume Onboarding <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}

        <main className="mx-auto w-full max-w-screen-2xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-10 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
