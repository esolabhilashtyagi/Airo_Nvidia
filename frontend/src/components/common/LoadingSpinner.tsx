import React from 'react';

export const LoadingSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg'; message?: string }> = ({
  size = 'md',
  message,
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <div className="flex flex-col items-center justify-center p-6 gap-3">
      <div
        className={`${sizeClasses[size]} border-violet-200 border-t-violet-600 rounded-full animate-spin`}
      />
      {message && <p className="text-sm text-slate-500 font-medium">{message}</p>}
    </div>
  );
};
