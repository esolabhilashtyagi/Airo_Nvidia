import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, CartesianGrid,
} from 'recharts';

interface DashboardChartsProps {
  weeklyActivity: Array<{ day: string; questions: number }>;
  scoreHistory: Array<{ date: string; score: number }>;
  totalPracticeCount: number;
  readinessScore: number | null;
}

export function DashboardCharts({ weeklyActivity, scoreHistory, totalPracticeCount, readinessScore }: DashboardChartsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Weekly Preparation Velocity</h3>
            <p className="text-xs text-slate-500">Practice questions answered this week</p>
          </div>
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
            {totalPracticeCount} Total Solved
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
            <h3 className="text-sm font-bold text-slate-900">Assessment Score Progression</h3>
            <p className="text-xs text-slate-500">Historical performance across practice tests</p>
          </div>
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-violet-50 text-violet-700 border border-violet-200">
            Readiness: {readinessScore ?? '—'}{readinessScore != null ? '%' : ''}
          </span>
        </div>
        {scoreHistory.length ? <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={scoreHistory}>
              <defs>
                <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #ddd6fe', borderRadius: '10px', color: '#1e1b4b', fontSize: '12px', boxShadow: '0 8px 24px rgba(49, 46, 129, 0.12)' }} />
              <Area type="monotone" dataKey="score" stroke="#6d28d9" strokeWidth={2.5} fillOpacity={1} fill="url(#colorScore)" activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
            </AreaChart>
          </ResponsiveContainer>
        </div> : <p className="py-16 text-center text-sm text-slate-500">Assessment history will appear here after your first completed test.</p>}
      </div>
    </div>
  );
}
