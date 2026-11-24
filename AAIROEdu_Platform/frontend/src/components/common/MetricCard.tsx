import React from 'react';
import { Activity, Award, CheckCircle2, FileText, Video, type LucideIcon } from 'lucide-react';

const metricIcons: Record<string, LucideIcon> = {
  Activity,
  Award,
  CheckCircle2,
  FileText,
  Video,
};

export interface MetricCardProps {
  title: string;
  value: string | number;
  changeText?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  iconName?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  changeText,
  changeType = 'neutral',
  iconName = 'Activity',
}) => {
  const IconComponent = metricIcons[iconName] ?? Activity;

  const changeStyles = {
    positive: 'text-violet-800 bg-violet-50 border border-violet-100',
    negative: 'text-rose-600 bg-rose-50',
    neutral: 'text-slate-600 bg-slate-50',
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm hover:shadow transition-shadow">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </span>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${iconName === 'FileText' ? 'bg-slate-100 text-slate-600' : 'bg-violet-50 text-violet-600'}`}>
          <IconComponent className="w-5 h-5" />
        </div>
      </div>
      <div className="mt-3">
        <div className="text-2xl font-bold tracking-tight text-slate-900">{value}</div>
        {changeText && (
          <div className="mt-2 flex items-center">
            <span
              className={`text-xs font-medium px-2.5 py-1 rounded-md ${changeStyles[changeType]}`}
            >
              {changeText}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
