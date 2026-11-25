// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const { getOverview, getAnalytics } = vi.hoisted(() => ({
  getOverview: vi.fn(),
  getAnalytics: vi.fn(),
}));

vi.mock('../../api/services', () => ({ dashboardApi: { getOverview, getAnalytics } }));
vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'candidate-1', full_name: 'Aishwarya Candidate', role: 'candidate' },
    profile: {
      onboarding_completed: true,
      target_role: 'Data Analyst',
      industry: { name: 'Finance' },
    },
  }),
}));

import { DashboardPage } from './DashboardPage';

afterEach(() => { cleanup(); vi.clearAllMocks(); });
beforeEach(() => {
  Object.defineProperty(window, 'IntersectionObserver', {
    configurable: true,
    value: class {
      observe() {}
      disconnect() {}
      unobserve() {}
    },
  });
  getOverview.mockResolvedValue({
    target_role: 'Data Analyst',
    industry_name: 'Finance',
    interview_readiness_score: 82.5,
    readiness_factors: {
      coverage_percent: 70,
      components: {
        profile_baseline: { label: 'Profile completeness', weight_percent: 15, score_percent: 90, included: true, description: 'Profile fields.' },
        resume_alignment: { label: 'Resume structure and analysis', weight_percent: 25, score_percent: 70, included: true, description: 'Resume review.' },
        assessment_proficiency: { label: 'Assessment performance', weight_percent: 30, score_percent: null, included: false, description: 'Completed assessments.' },
        interview_delivery: { label: 'Mock interview performance', weight_percent: 30, score_percent: 80, included: true, description: 'Completed interviews.' },
      },
    },
    metrics: [],
  });
  getAnalytics.mockResolvedValue({ weekly_activity: [], score_history: [], total_practice_count: 0 });
});

describe('DashboardPage overview', () => {
  it('uses neutral career wording and explains evidence coverage with real factor status', async () => {
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);

    expect(await screen.findByText('Career Preparation Overview')).toBeTruthy();
    expect(screen.queryByText(/AI Career Intelligence Dashboard/i)).toBeNull();
    expect(screen.getByText(/Current evidence coverage: 70%/)).toBeTruthy();
    expect(screen.getByText('30% weight · Not assessed')).toBeTruthy();
    expect(screen.getByText(/Your preparation metrics are summarized below/)).toBeTruthy();
  });
});
