import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Bot,
  HelpCircle,
  BookOpen,
  GraduationCap,
  Video,
  BarChart3,
  User,
  Settings,
  ShieldAlert,
  X,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { CandidateAvatar } from './CandidateAvatar';

export const Sidebar: React.FC<{ mobileOpen?: boolean; onNavigate?: () => void }> = ({ mobileOpen = false, onNavigate }) => {
  const { user, profile } = useAuth();

  const navigationItems = [
    { name: 'Overview', to: '/dashboard', icon: LayoutDashboard },
    { name: 'My Resume', to: '/resume', icon: FileText },
    { name: 'AI Coach & Roadmap', to: '/coach', icon: Bot },
    { name: 'Question Bank', to: '/question-bank', icon: HelpCircle },
    { name: 'Learning Modules', to: '/modules', icon: BookOpen },
    { name: 'Testing Mode', to: '/testing', icon: GraduationCap },
    { name: 'Mock Interviews', to: '/interviews', icon: Video },
    { name: 'Performance Reports', to: '/reports', icon: BarChart3 },
    { name: 'My Profile', to: '/profile', icon: User },
    { name: 'Settings', to: '/settings', icon: Settings },
  ];

  return (
    <>
      {mobileOpen && <div aria-hidden="true" onClick={onNavigate} className="fixed inset-0 z-40 bg-slate-500/20 backdrop-blur-[1px] md:hidden" />}
      <aside className={`${mobileOpen ? 'flex' : 'hidden'} fixed inset-y-0 left-0 z-50 h-screen w-72 shrink-0 flex-col border-r border-violet-100 bg-white text-slate-700 select-none md:sticky md:top-0 md:z-auto md:flex`}>
        {/* Brand Header */}
        <div className="h-[5.5rem] flex items-center px-6 border-b border-violet-100 gap-3">
          <CandidateAvatar gender={profile?.avatar_gender} size={44} label={`${user?.full_name || 'Candidate'} avatar`} />
          <div>
            <span className="font-bold text-xl text-violet-700 tracking-tight flex items-center gap-1.5">
              AAIRO
              {/* <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-violet-50 text-violet-700 border border-violet-100">
                Pro
              </span> */}
            </span>
            <p className="text-[11px] text-slate-500">Career Learning Platform</p>
          </div>
          <button type="button" aria-label="Close navigation menu" onClick={onNavigate} className="ml-auto rounded-lg p-2 text-slate-500 hover:bg-violet-50 hover:text-violet-700 md:hidden">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Navigation List */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-2">
          <div className="px-4 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Preparation Suite
          </div>

          {navigationItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex min-h-14 items-center justify-between px-3 py-2 rounded-full text-[15px] font-medium transition-all ${isActive
                  ? 'bg-gradient-to-r from-[#4d00ef] to-[#8952ff] text-white shadow-lg shadow-violet-500/20'
                  : 'text-[#17122f] hover:text-violet-700 hover:bg-violet-50'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <div className="flex min-w-0 items-center gap-3">
                    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border ${item.name === 'My Resume' ? (isActive ? 'border-white/40 bg-white/15 text-slate-200' : 'border-slate-200 bg-white text-slate-500') : (isActive ? 'border-white/40 bg-white/15' : 'border-violet-200 bg-white')}`}>
                      <item.icon className="h-[18px] w-[18px] shrink-0" />
                    </span>
                    <span>{item.name}</span>
                  </div>
                </>
              )}
            </NavLink>
          ))}

          {/* Administrator Section */}
          {(user?.role === 'administrator' || user?.role === 'content_manager') && (
            <div className="pt-5">
              <div className="px-4 pb-2 text-[11px] font-semibold uppercase tracking-wider text-violet-600 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5" />
                Management
              </div>
              <NavLink
                to="/admin"
                onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-full px-4 py-3 text-sm font-medium transition-all ${isActive
                    ? 'bg-gradient-to-r from-[#4d00ef] to-[#8952ff] text-white shadow-lg shadow-violet-500/20'
                    : 'text-[#17122f] hover:bg-violet-50 hover:text-violet-700'
                  }`
                }
              >
                <ShieldAlert className="w-4 h-4" />
                <span>Admin Console</span>
              </NavLink>
            </div>
          )}
        </div>

        {/* User Footer Profile */}
        <div className="border-t border-violet-100 bg-white p-4">
          <div className="flex items-center gap-3 px-2 py-1.5">
            <CandidateAvatar gender={profile?.avatar_gender} size={36} label={`${user?.full_name || 'Candidate'} avatar`} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-900 truncate">{user?.full_name || 'Candidate'}</p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email || ''}</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
