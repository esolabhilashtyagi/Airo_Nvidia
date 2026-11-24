import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  actionLink?: string;
  onActionClick?: () => void;
  iconClassName?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  actionText,
  actionLink,
  onActionClick,
  iconClassName = '',
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 sm:p-12 text-center bg-white rounded-xl border border-dashed border-slate-300">
      <div className={`w-14 h-14 rounded-2xl bg-slate-100 text-slate-500 flex items-center justify-center mb-4 ${iconClassName}`}>
        <Icon className="w-7 h-7" />
      </div>
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-sm text-slate-500 max-w-sm">{description}</p>
      {(actionText && actionLink) && (
        <Link
          to={actionLink}
          className="mt-5 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-violet-600 hover:bg-violet-700 shadow-sm transition-colors"
        >
          {actionText}
        </Link>
      )}
      {(actionText && onActionClick && !actionLink) && (
        <button
          onClick={onActionClick}
          className="mt-5 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-violet-600 hover:bg-violet-700 shadow-sm transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
