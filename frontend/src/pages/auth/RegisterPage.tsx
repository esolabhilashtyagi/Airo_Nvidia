import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Lock, Mail, User, ArrowRight } from 'lucide-react';
import { RequiredLabel } from '../../components/common/RequiredMark';

const COMMON_PASSWORDS = new Set([
  'password', 'password1', 'password12', 'password123', 'password1234',
  'qwerty', 'qwerty123', 'welcome', 'welcome123', 'letmein', 'letmein123',
  'admin123', 'adminpassword123', 'candidatepass123', 'managerpass123',
  'securepassword123', 'iloveyou', 'iloveyou123', 'changeme', 'changeme123',
  '12345678', '123456789', '11111111', '00000000',
]);

const isWeakPassword = (value: string) => {
  const normalized = value.toLowerCase().replace(/[^a-z0-9]/g, '');
  return COMMON_PASSWORDS.has(normalized)
    || new Set(normalized).size <= 2
    || ['0123456789', '12345678', 'abcdefgh', 'qwerty', 'asdfgh', 'zxcvbn'].some((sequence) => normalized.includes(sequence));
};

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (isWeakPassword(password)) {
      setError('Choose a less common password; avoid common words, keyboard patterns, and simple sequences.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await register(email, password, fullName);
      // Carry only the email to the manual sign-in screen. Never carry or store
      // the password; password managers may otherwise restore an older value.
      navigate('/login', { state: { registered: true, email: email.trim() } });
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try a different email.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Create candidate account</h3>
        <p className="text-xs text-slate-500 mt-0.5">Start your personalized multi-industry career preparation.</p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-700"><RequiredLabel>Full Name</RequiredLabel></label>
          <div className="mt-1 relative">
            <User className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              autoComplete="name"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Maya Patel"
              className="w-full pl-9 pr-3 py-2 bg-white border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-600 text-slate-900"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700"><RequiredLabel>Email Address</RequiredLabel></label>
          <div className="mt-1 relative">
            <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="candidate@example.com"
              className="w-full pl-9 pr-3 py-2 bg-white border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-600 text-slate-900"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700"><RequiredLabel>Password</RequiredLabel></label>
          <div className="mt-1 relative">
            <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="8+ characters; avoid common passwords"
              className="w-full pl-9 pr-3 py-2 bg-white border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-600 text-slate-900"
            />
          </div>
          <p className="mt-1 text-xs text-slate-500">Avoid common words, keyboard patterns, and simple sequences.</p>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-violet-500 transition-colors disabled:opacity-50"
        >
          {isSubmitting ? 'Creating account...' : 'Create Account'}
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>

      <div className="pt-2 text-center text-xs text-slate-500">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-violet-600 hover:text-violet-700">
          Sign in
        </Link>
      </div>
    </div>
  );
};
