import React, { useState } from 'react';
import { RequiredLabel } from '../../components/common/RequiredMark';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { authApi } from '../../api/auth';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await authApi.forgotPassword(email);
      setIsSubmitted(true);
    } catch (err: any) {
      setError(err.message || 'Could not process request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="text-center space-y-4">
        <div className="w-12 h-12 bg-violet-50 text-violet-600 rounded-full flex items-center justify-center mx-auto">
          <CheckCircle2 className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-slate-900">Check your inbox</h3>
        <p className="text-xs leading-5 text-slate-500">
          If an active account matches <span className="font-semibold text-slate-700">{email}</span>, password reset instructions have been sent. Check your inbox and spam folder.
        </p>
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-600 hover:text-violet-700 pt-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Return to Sign In
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Forgot your password?</h3>
        <p className="text-xs text-slate-500 mt-0.5">Enter your registered email address to receive reset steps.</p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-700"><RequiredLabel>Email Address</RequiredLabel></label>
          <div className="mt-1 relative">
            <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="candidate@aairo.ai"
              className="w-full pl-9 pr-3 py-2 bg-white border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-600 text-slate-900"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-violet-500 transition-colors disabled:opacity-50"
        >
          {isSubmitting ? 'Sending...' : 'Send Reset Instructions'}
        </button>
      </form>

      <div className="pt-2 text-center text-xs text-slate-500">
        <Link to="/login" className="inline-flex items-center gap-1 font-semibold text-violet-600 hover:text-violet-700">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Sign In
        </Link>
      </div>
    </div>
  );
};
