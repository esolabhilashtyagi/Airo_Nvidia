import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../../api/auth';
import { paymentsApi } from '../../api/services';
import { useAuth } from '../../context/AuthContext';
import { RequiredLabel } from '../../components/common/RequiredMark';

export function SettingsPage() {
  const { user, logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [atsAccess, setAtsAccess] = useState<{ has_access: boolean } | null>(null);
  const [resumeAccess, setResumeAccess] = useState<{ has_access: boolean } | null>(null);
  useEffect(() => {
    void Promise.all([paymentsApi.atsAccess(), paymentsApi.resumeTemplateAccess()]).then(([ats, resume]) => {
      setAtsAccess(ats);
      setResumeAccess(resume);
    }).catch(() => { setAtsAccess(null); setResumeAccess(null); });
  }, []);

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }

    setSaving(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      await logout();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Password could not be changed.');
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-sm font-semibold text-violet-700">Account</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-900">Settings</h1>
        <p className="mt-2 text-sm text-slate-600">Manage your account details and sign-in security.</p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Profile</h2>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          <div><dt className="text-xs font-medium text-slate-500">Name</dt><dd className="mt-1 text-sm text-slate-900">{user?.full_name}</dd></div>
          <div><dt className="text-xs font-medium text-slate-500">Email</dt><dd className="mt-1 text-sm text-slate-900">{user?.email}</dd></div>
        </dl>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-lg font-semibold text-slate-900">Profile & preferences</h2><p className="mt-1 text-sm text-slate-600">Keep your resume details and interview preferences current.</p></div><Link to="/profile" className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Edit profile</Link></div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Feature access</h2>
        <p className="mt-1 text-sm text-slate-600">Review paid features linked to your account.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4"><p className="text-sm font-semibold text-slate-900">Job-specific resume review</p><p className="mt-1 text-sm text-slate-600">{atsAccess?.has_access ? 'One-time access is active.' : atsAccess ? 'Not unlocked.' : 'Access status is unavailable.'}</p></div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4"><p className="text-sm font-semibold text-slate-900">Premium resume layouts</p><p className="mt-1 text-sm text-slate-600">{resumeAccess?.has_access ? 'One-time access is active.' : resumeAccess ? 'Not unlocked.' : 'Access status is unavailable.'}</p></div>
        </div>
        <p className="mt-3 text-xs text-slate-500">Purchases stay linked to this account. <Link to="/profile" className="font-semibold text-violet-800 underline">Open Resume Studio</Link> to download your PDF or view available layouts.</p>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Change password</h2>
        <p className="mt-1 text-sm text-slate-600">Use this while signed in and you know your current password. You’ll be signed out after the change.</p>
        {error && <p role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
        <form className="mt-4 space-y-4" onSubmit={(event) => void changePassword(event)}>
          <label className="block text-sm font-medium text-slate-700"><RequiredLabel>Current password</RequiredLabel>
            <input required autoComplete="current-password" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm font-medium text-slate-700"><RequiredLabel>New password</RequiredLabel>
            <input required minLength={8} autoComplete="new-password" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm font-medium text-slate-700"><RequiredLabel>Confirm new password</RequiredLabel>
            <input required minLength={8} autoComplete="new-password" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>
          <button type="submit" disabled={saving} className="rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {saving ? 'Updating…' : 'Update password'}
          </button>
        </form>
        <p className="mt-4 text-sm text-slate-600">Can’t sign in or don’t know your current password? <Link to="/forgot-password" className="font-semibold text-violet-700 hover:underline">Request reset instructions</Link>.</p>
      </section>
    </div>
  );
}
