import React, { useEffect, useState } from 'react';
import { Search, Bell, Sparkles, LogOut, User as UserIcon, Menu } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import { systemApi } from '../../api/services';

export const Navbar: React.FC<{ onMenuClick?: () => void }> = ({ onMenuClick }) => {
  const { user, profile, logout } = useAuth();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [aiStatus, setAiStatus] = useState<'checking' | 'configured' | 'unconfigured' | 'unavailable'>('checking');
  const [notifications, setNotifications] = useState<Array<{ id: string; title: string; message: string; is_read: boolean; link_url?: string | null }>>([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [notificationsError, setNotificationsError] = useState('');

  useEffect(() => {
    systemApi.getAiStatus()
      .then((status) => setAiStatus(status.configured ? 'configured' : 'unconfigured'))
      .catch(() => setAiStatus('unavailable'));
  }, []);

  const openNotifications = async () => {
    const opening = !showNotifications;
    setShowNotifications(opening);
    if (!opening) return;

    setNotificationsLoading(true);
    setNotificationsError('');
    try {
      setNotifications(await systemApi.getNotifications());
    } catch (caught) {
      setNotificationsError(caught instanceof Error ? caught.message : 'Notifications could not be loaded.');
    } finally {
      setNotificationsLoading(false);
    }
  };

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-slate-200/80 bg-white">
      <div className="mx-auto flex h-full w-full max-w-screen-2xl items-center justify-between gap-2 px-4 sm:gap-4 sm:px-6 lg:px-10">
      {/* Search Input */}
      <button type="button" aria-label="Open navigation menu" onClick={onMenuClick} className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 md:hidden"><Menu className="h-5 w-5" /></button>
      <form className="flex min-w-0 flex-1 items-center gap-3 sm:max-w-96" onSubmit={(event) => { event.preventDefault(); const form = new FormData(event.currentTarget); const search = String(form.get('search') || '').trim(); if (search) navigate(`/question-bank?search=${encodeURIComponent(search)}`); }}>
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            name="search"
            placeholder="Search questions, topics, roadmaps..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 text-slate-800 placeholder-slate-400"
          />
        </div>
      </form>

      {/* Right Controls */}
        <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        {/* Active Industry / Target Role Badge */}
        {profile?.target_role && (
          <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-violet-50 text-violet-700 rounded-full border border-violet-200/80 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-violet-500 animate-pulse" />
            {profile.target_role}
            {profile.industry?.name && (
              <span className="text-violet-500 font-normal">({profile.industry.name})</span>
            )}
          </div>
        )}

        {/* AI Provider Status Pill */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200" title="Configured AI provider status">
          <Sparkles className="w-3.5 h-3.5 text-violet-500" />
          <span className="hidden sm:inline">AI Engine:</span>
          <span className="text-slate-900 font-semibold">{{ checking: 'Checking', configured: 'Configured', unconfigured: 'Setup required', unavailable: 'Status unavailable' }[aiStatus]}</span>
        </div>

        {/* Notifications Bell */}
        <div className="relative">
          <button
            onClick={() => void openNotifications()}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 relative transition-colors"
            aria-label="Notifications"
          >
            <Bell className="w-5 h-5" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-slate-200 p-4 z-50">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <span className="text-sm font-semibold text-slate-900">Notifications</span>
                <span className="text-xs text-violet-600 font-medium">{notifications.filter(item => !item.is_read).length} unread</span>
              </div>
              {notificationsLoading ? <p role="status" className="py-4 text-xs text-slate-500">Loading notifications…</p> : notificationsError ? <p role="alert" className="py-4 text-xs text-rose-700">{notificationsError}</p> : notifications.length ? <div className="max-h-80 divide-y overflow-y-auto">{notifications.map(item => <button key={item.id} className="block w-full py-3 text-left" onClick={() => { if (!item.is_read) void systemApi.markNotificationRead(item.id).then(() => setNotifications(rows => rows.map(row => row.id === item.id ? { ...row, is_read: true } : row))).catch((caught) => setNotificationsError(caught instanceof Error ? caught.message : 'Notification could not be marked as read.')); if (item.link_url) navigate(item.link_url); setShowNotifications(false); }}><span className="block text-xs font-semibold text-slate-900">{item.title}</span><span className="mt-1 block text-xs text-slate-600">{item.message}</span></button>)}</div> : <p className="py-4 text-xs text-slate-500">No notifications yet.</p>}
            </div>
          )}
        </div>

        {/* User Profile Avatar Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            aria-label={`Open user menu for ${user?.full_name || 'account'}`}
            aria-expanded={showUserMenu}
            className="flex items-center gap-2 p-1 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-violet-600 text-white font-semibold flex items-center justify-center text-xs shadow-sm">
              {user?.full_name ? user.full_name[0].toUpperCase() : 'U'}
            </div>
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-slate-200 py-1.5 z-50">
              <div className="px-4 py-2 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-900">{user?.full_name}</p>
                <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
              </div>
              <Link
                to="/profile"
                onClick={() => setShowUserMenu(false)}
                className="flex items-center gap-2 px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <UserIcon className="w-3.5 h-3.5 text-slate-400" />
                My Profile
              </Link>
              <button
                onClick={logout}
                className="w-full flex items-center gap-2 px-4 py-2 text-xs text-rose-600 hover:bg-rose-50 transition-colors text-left"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
      </div>
    </header>
  );
};
