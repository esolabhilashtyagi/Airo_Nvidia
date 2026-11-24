import { useEffect, useState, type FormEvent } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, LockKeyhole } from 'lucide-react';
import { authApi } from '../../api/auth';

export function ResetPasswordPage() {
  const location = useLocation();
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token') || '');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [complete, setComplete] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (token && window.location.hash) {
      // The token fragment is never sent to the server; remove it from browser history after capture.
      window.history.replaceState(window.history.state, '', `${location.pathname}${location.search}`);
    }
  }, [location.pathname, location.search, token]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    if (!token) {
      setError('This reset link is missing its token. Request a new password reset email.');
      return;
    }
    if (password !== confirmPassword) {
      setError('The passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      await authApi.resetPassword(token, password);
      setComplete(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Password reset failed. Request a new link and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  if (complete) return <div className="space-y-4 text-center">
    <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-700"><CheckCircle2 className="h-6 w-6" /></span>
    <h1 className="text-lg font-semibold text-slate-900">Password updated</h1>
    <p className="text-sm text-slate-600">Your password has been changed. Sign in with your new password.</p>
    <Link to="/login" className="inline-flex items-center gap-2 pt-2 text-sm font-semibold text-violet-700 hover:underline"><ArrowLeft className="h-4 w-4" /> Back to sign in</Link>
  </div>;

  return <div className="space-y-6">
    <div><span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-700"><LockKeyhole className="h-5 w-5" /></span><h1 className="text-lg font-semibold text-slate-900">Choose a new password</h1><p className="mt-1 text-sm text-slate-500">Use a strong password you have not used on this account before.</p></div>
    {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
    {!token && !error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">This link is incomplete. Request a new password reset email.</p>}
    <form onSubmit={(event) => void submit(event)} className="space-y-4">
      <label className="block text-sm font-medium text-slate-700">New password<input type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-100" /></label>
      <label className="block text-sm font-medium text-slate-700">Confirm new password<input type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} className="mt-1.5 block w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-violet-600 focus:outline-none focus:ring-2 focus:ring-violet-100" /></label>
      <p className="text-xs leading-5 text-slate-500">Avoid common passwords, repeated characters, keyboard patterns, and simple number or letter sequences.</p>
      <button type="submit" disabled={submitting || !token} className="w-full rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:opacity-50">{submitting ? 'Updating password…' : 'Update password'}</button>
    </form>
    <Link to="/forgot-password" className="inline-flex items-center gap-2 text-sm font-semibold text-violet-700 hover:underline"><ArrowLeft className="h-4 w-4" /> Request a new reset link</Link>
  </div>;
}
