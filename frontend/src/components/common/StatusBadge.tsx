import React from 'react';

export interface StatusBadgeProps {
  status: string;
  variant?: 'teal' | 'emerald' | 'amber' | 'blue' | 'rose' | 'slate';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status = 'unknown', variant }) => {
  const getVariant = () => {
    if (variant) return variant;
    const lower = status.toLowerCase();
    if (['completed', 'approved', 'passed', 'accepted', 'active'].includes(lower)) return 'emerald';
    if (['in_progress', 'pending', 'setup'].includes(lower)) return 'amber';
    if (['rejected', 'failed', 'abandoned', 'cancelled'].includes(lower)) return 'rose';
    if (['expert', 'advanced'].includes(lower)) return 'blue';
    return 'slate';
  };

  const currentVariant = getVariant();

  const styles = {
    teal: 'bg-violet-50 text-violet-700 border-violet-200',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-purple-50 text-purple-700 border-purple-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    rose: 'bg-rose-50 text-rose-700 border-rose-200',
    slate: 'bg-slate-100 text-slate-700 border-slate-200',
  };

  const formatText = (text: string) => {
    return text.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[currentVariant]}`}
    >
      {formatText(status)}
    </span>
  );
};
