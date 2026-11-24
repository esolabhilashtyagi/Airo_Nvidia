// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { CandidateProfile } from '../../types';

const { generateFromProfile } = vi.hoisted(() => ({ generateFromProfile: vi.fn() }));
vi.mock('../../api/resumes', () => ({ resumesApi: { generateFromProfile } }));
import { ProfileOverview } from './ProfileOverview';

afterEach(() => { cleanup(); vi.clearAllMocks(); });

const graduateProfile = {
  id: 'profile-1', user_id: 'user-1', candidate_type: 'student_fresher', sub_category: 'recent_graduate',
  industry_id: 'industry-1', industry: { id: 'industry-1', name: 'Information Technology', slug: 'information-technology', is_active: true, categories: [], job_roles: [] }, target_role: 'Associate AI Engineer',
  total_experience_months: 0, relevant_experience_months: 0, key_skills: ['Python', 'Prompt Engineering'],
  onboarding_completed: true, onboarding_step: 7, interview_rounds_preferred: ['Technical'],
  interaction_preference: 'text', interview_readiness_score: 0,
  education_history: [{ id: 'edu-1', degree: 'B.Tech', field_of_study: 'Computer Science', institution: 'Example University', end_year: 2026, is_current: false }],
  experience_history: [{ id: 'exp-1', company_name: 'Example Labs', job_title: 'AI Intern', start_date: 'May 2025', end_date: 'Aug 2025', is_current: false, description: 'Built a small internal search prototype.' }],
  target_companies: [],
} as CandidateProfile;

describe('ProfileOverview', () => {
  it('shows graduate education and internship details without implying a current employer', () => {
    render(<ProfileOverview profile={graduateProfile} onEdit={vi.fn()} />);

    expect(screen.getByText('Student / recent graduate')).toBeTruthy();
    expect(screen.getByText(/no professional tenure recorded/)).toBeTruthy();
    expect(screen.getByText('AI Intern')).toBeTruthy();
    expect(screen.getByText('Example Labs')).toBeTruthy();
    expect(screen.getByText(/B.Tech · Computer Science/)).toBeTruthy();
    expect(screen.queryByText('Current company')).toBeNull();
  });

  it('downloads a resume generated from the saved profile', async () => {
    generateFromProfile.mockResolvedValue({ blob: new Blob(['pdf']), filename: 'candidate-resume.pdf' });
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:profile-resume');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    const user = userEvent.setup();
    render(<ProfileOverview profile={graduateProfile} onEdit={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /Classic/ }));
    await user.click(screen.getByRole('button', { name: 'Download PDF' }));

    expect(generateFromProfile).toHaveBeenCalledWith('classic', 'pdf');
    expect(createObjectURL).toHaveBeenCalledOnce();
  });

  it('allows an editable DOCX export when selected', async () => {
    generateFromProfile.mockResolvedValue({ blob: new Blob(['docx']), filename: 'candidate-resume.docx' });
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:profile-resume');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    const user = userEvent.setup();
    render(<ProfileOverview profile={graduateProfile} onEdit={vi.fn()} />);

    await user.selectOptions(screen.getByRole('combobox', { name: 'Resume download format' }), 'docx');
    await user.click(screen.getByRole('button', { name: 'Download DOCX' }));

    expect(generateFromProfile).toHaveBeenCalledWith('modern', 'docx');
  });
});
