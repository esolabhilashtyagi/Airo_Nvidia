import {
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, CartesianGrid, LineChart, Line, Legend,
} from 'recharts';

interface DashboardChartsProps {
  weeklyActivity: Array<{ day: string; questions: number }>;
  scoreHistory: Array<{ date: string; timestamp?: string | null; score: number; type: 'assessment' | 'mock_interview' }>;
  totalPracticeCount: number;
}

export function DashboardCharts({ weeklyActivity, scoreHistory, totalPracticeCount }: DashboardChartsProps) {
  const formatScoreDate = (item: { date: string; timestamp?: string | null }) => {
    const value = item.timestamp ? new Date(item.timestamp) : new Date(item.date);
    return Number.isNaN(value.getTime()) ? item.date : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(value);
  };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Weekly Preparation Velocity</h3>
            <p className="text-xs text-slate-500">Practice questions answered this week</p>
          </div>
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
            {totalPracticeCount} Total Attempts
          </span>
        </div>
        {weeklyActivity.length ? <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={weeklyActivity}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip cursor={{ fill: '#f5f3ff', opacity: 0.8 }} contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #ddd6fe', borderRadius: '10px', color: '#1e1b4b', fontSize: '12px', boxShadow: '0 8px 24px rgba(49, 46, 129, 0.12)' }} />
              <Bar dataKey="questions" fill="#7c3aed" radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div> : <p className="py-16 text-center text-sm text-slate-500">Practice activity will appear here as you complete questions.</p>}
      </div>

      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Completed performance history</h3>
            <p className="text-xs text-slate-500">Assessment and interview scores are shown separately</p>
          </div>
        </div>
        {scoreHistory.length ? <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={scoreHistory.map((item) => ({
              date: formatScoreDate(item),
              assessment_score: item.type === 'assessment' ? item.score : null,
              interview_score: item.type === 'mock_interview' ? item.score : null,
            }))}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip formatter={(value, name) => [`${value}%`, name === 'interview_score' ? 'Mock interview' : 'Assessment']} labelFormatter={(label) => `Completed ${label}`} contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #ddd6fe', borderRadius: '10px', color: '#1e1b4b', fontSize: '12px', boxShadow: '0 8px 24px rgba(49, 46, 129, 0.12)' }} />
              <Legend formatter={(name) => name === 'interview_score' ? 'Mock interview' : 'Assessment'} />
              <Line connectNulls type="monotone" dataKey="assessment_score" name="assessment_score" stroke="#6d28d9" strokeWidth={2.5} dot={{ r: 4 }} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
              <Line connectNulls type="monotone" dataKey="interview_score" name="interview_score" stroke="#0f766e" strokeWidth={2.5} dot={{ r: 4 }} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
            </LineChart>
          </ResponsiveContainer>
        </div> : <p className="py-16 text-center text-sm text-slate-500">Scores appear here after you complete an assessment or mock interview.</p>}
      </div>
    </div>
  );
}
